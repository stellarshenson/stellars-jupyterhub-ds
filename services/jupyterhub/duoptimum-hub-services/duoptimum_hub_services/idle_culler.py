"""Idle-culler calculations and the in-hub cull runtime.

Single source of truth for the session-extension feature. The home-page
countdown, the extend offer/apply logic, the admin activity dashboard, and the
actual cull decision all use the pure functions below, so what a user is shown
can never diverge from when the server is really stopped.

Model - a ceiling-bounded cull deadline (all times in seconds unless noted; the
extend UI works in whole hours):

    base_s      = idle timeout the server starts with
    max_ext_h   = maximum extension, whole hours
    ceiling_s   = base_s + max_ext_h*3600          # ABSOLUTE cap on remaining AND lifetime
    reference   = last_activity or started
    cull_at     = stored deadline timestamp (state['cull_at'])
    remaining_s = clamp(max(cull_at - now, base_s - (now - reference)), 0, ceiling_s)
    cull when   remaining_s <= 0   (or age >= max_age_s when max_age_s > 0)
    offer_h     = floor((ceiling_s - remaining_s) / 3600)
    extend(h):  remaining' = ceiling_s if h>=offer else min(remaining + h*3600, ceiling_s)
                cull_at = now + remaining'                # capped at now+ceiling

The deadline is what makes the ceiling a REAL cap: `remaining` is bounded by the
ceiling, and the deadline never sits more than `ceiling_s` ahead of `now`, so no
sequence of extends can bank lifetime past the ceiling (the previous "growing
budget" model could - extending repeatedly while idle inflated an uncapped
effective timeout). The `base_s - (now - reference)` term is an activity floor:
a freshly-active server always retains at least `base_s`, refreshed as real
activity advances `last_activity`. Extending pushes the deadline out (replenish)
up to - never past - the ceiling, so an idle server visibly counts down and
"take the full offer" lands remaining exactly on the ceiling ("max means max").

Legacy state used `state['extension_hours_used']`; `_cull_at` derives the
equivalent deadline on the fly (`reference + min(base + ext*3600, ceiling)`) so
existing servers display correctly with no migration pass - the first `extend`
persists `cull_at` and drops the legacy key.

Heavy imports (tornado, jupyterhub) are done inside the runtime functions so
this module imports with only the standard library - the pure calculations stay
trivially testable.
"""

from datetime import datetime, timedelta, timezone


# ── Pure calculations (stdlib only, seconds in / seconds out) ────────────────

def calc_ceiling(timeout_seconds, max_extension_hours):
    """Absolute cap on remaining time and lifetime (base + max extension)."""
    return timeout_seconds + max_extension_hours * 3600


def calc_remaining(seconds_to_deadline, seconds_since_activity, base_seconds, ceiling_seconds):
    """Seconds until cull: the later of the stored deadline and the activity
    floor (`base - idle`), floored at 0 and clamped to the ceiling.

    `seconds_to_deadline` is `cull_at - now` (may be negative once past the
    deadline). `seconds_since_activity` is `now - (last_activity or started)`,
    never negative. The activity floor guarantees a freshly-active server keeps
    at least `base`; the ceiling clamp guarantees remaining is never displayed -
    or enforced - above the cap.
    """
    activity_floor = base_seconds - seconds_since_activity
    remaining = max(seconds_to_deadline, activity_floor)
    if remaining < 0:
        remaining = 0
    if remaining > ceiling_seconds:
        remaining = ceiling_seconds
    return remaining


def calc_available_hours(remaining_seconds, ceiling_seconds):
    """Whole hours a user may add now: the gap from remaining up to the ceiling.

    This is the replenish offer - the headroom between the current remaining and
    the absolute ceiling. Floored to whole hours (the slider works in hours);
    taking the full offer is topped up to the exact ceiling by the caller.
    """
    gap = ceiling_seconds - remaining_seconds
    if gap < 0:
        gap = 0
    return int(gap / 3600)


def calc_progress_pct(remaining_seconds, base_seconds):
    """Progress-bar fill percent on the *normal TTL* scale (base, not ceiling).

    The bar measures remaining against the base timeout, not the ceiling, so a
    fresh or active server reads full (100%) and only begins to drain inside the
    final `base` window. Time banked above `base` by extension keeps the bar
    pinned at 100% until it falls back below base, at which point it counts down
    as the normal base-hour counter. Clamped to [0, 100]; `base_seconds <= 0`
    yields 0. Mirrored verbatim in `session-timer.js` (updateUI + startCountdown).
    """
    if base_seconds <= 0:
        return 0.0
    pct = remaining_seconds / base_seconds * 100
    if pct < 0:
        return 0.0
    return 100.0 if pct > 100 else pct


def calc_progress_pct_extended(remaining_seconds, base_seconds, display_ceiling_seconds):
    """Bar fill % (React portal). Below base: vs base (fresh = full). Banked above
    base: vs display_ceiling = remaining last extended TO, so just-extended = 100%
    and drains vs THAT mark, not the far 72h ceiling (old bug: 35h of 72h = ~50%).
    Mark ignored below base. Clamped [0,100]; base <= 0 -> 0. Mirrored in
    meters.tsx TtlGadget.pctFor.
    """
    if (
        remaining_seconds > base_seconds
        and display_ceiling_seconds
        and display_ceiling_seconds > base_seconds
    ):
        pct = remaining_seconds / display_ceiling_seconds * 100
    elif base_seconds > 0:
        pct = remaining_seconds / base_seconds * 100
    else:
        return 0.0
    if pct < 0:
        return 0.0
    return 100.0 if pct > 100 else pct


def calc_extended_remaining(remaining_seconds, hours, ceiling_seconds, maxed):
    """Remaining after applying an extension of `hours`, capped at the ceiling.

    `maxed` (the user took the full whole-hour offer) lands exactly on the
    ceiling rather than up to 59m short from the offer's whole-hour flooring -
    "max means max", now structural rather than a special-cased top-up.
    """
    if maxed:
        return ceiling_seconds
    extended = remaining_seconds + hours * 3600
    return ceiling_seconds if extended > ceiling_seconds else extended


def should_cull(remaining_seconds, age_seconds, max_age_seconds=0):
    """Cull when the ceiling-bounded remaining has run out, or - independently -
    when the server's age has reached `max_age_seconds` (only when it is > 0).
    """
    if remaining_seconds <= 0:
        return True
    if max_age_seconds and age_seconds is not None and age_seconds >= max_age_seconds:
        return True
    return False


def _as_utc(dt):
    """Normalise a possibly-naive datetime to tz-aware UTC (JupyterHub stores naive UTC)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# ── Runtime helpers (read orm state + datetime) ─────────────────────────────

def _cull_at(orm_spawner, reference, base_seconds, ceiling_seconds):
    """The server's cull deadline as a tz-aware UTC datetime.

    Prefers the persisted `state['cull_at']`; for legacy/fresh state derives the
    equivalent ceiling-capped deadline from `extension_hours_used` (default 0),
    so existing servers need no migration and a fresh server gets `base`.
    """
    state = orm_spawner.state or {}
    raw = state.get("cull_at")
    if raw:
        try:
            return _as_utc(datetime.fromisoformat(raw))
        except (TypeError, ValueError):
            pass
    ext_h = state.get("extension_hours_used", 0)
    budget = min(base_seconds + ext_h * 3600, ceiling_seconds)
    return reference + timedelta(seconds=budget)


def remaining_seconds_for(orm_spawner, base_seconds, ceiling_seconds, now):
    """Single source of truth for a server's remaining seconds (display + cull).

    Folds `last_activity` / `started` / `state` into the deadline model and
    returns an int in [0, ceiling]. Used by the session handler, the activity
    dashboard, and the cull pass so they can never diverge.
    """
    reference = _as_utc(orm_spawner.last_activity) or _as_utc(orm_spawner.started)
    if reference is None:
        # No activity and no start time recorded yet - treat as full base budget.
        return int(min(base_seconds, ceiling_seconds))
    seconds_since_activity = (now - reference).total_seconds()
    cull_at = _cull_at(orm_spawner, reference, base_seconds, ceiling_seconds)
    seconds_to_deadline = (cull_at - now).total_seconds()
    return int(calc_remaining(seconds_to_deadline, seconds_since_activity, base_seconds, ceiling_seconds))


# ── In-hub cull runtime (heavy imports done lazily) ─────────────────────────

async def run_cull_pass(base_seconds, ceiling_seconds, max_age_seconds):
    """One cull sweep over all active servers, run inside the hub process.

    Reads each server's deadline directly from `orm_spawner.state` (the same
    store the UI handlers use) via `remaining_seconds_for`, so per-user
    extensions actually delay the cull and the ceiling is a real lifetime cap -
    the external jupyterhub-idle-culler can see neither. Returns the number of
    servers culled.
    """
    from jupyterhub import orm
    from jupyterhub.app import JupyterHub

    app = JupyterHub.instance()
    now = datetime.now(timezone.utc)
    culled = 0

    for orm_user in app.db.query(orm.User).all():
        user = app.users.get(orm_user.name)
        if user is None:
            continue
        spawner = user.spawner
        if spawner is None or not spawner.active:
            continue
        # skip servers mid start/stop or not actually ready
        if getattr(spawner, "pending", None) or not getattr(spawner, "ready", False):
            continue

        try:
            orm_spawner = spawner.orm_spawner
            remaining_s = remaining_seconds_for(orm_spawner, base_seconds, ceiling_seconds, now)
            started = _as_utc(orm_spawner.started)
            age_s = (now - started).total_seconds() if started is not None else None

            if should_cull(remaining_s, age_s, max_age_seconds):
                app.log.info(
                    f"[Idle Culler] Culling {user.name} "
                    f"(remaining={remaining_s}s, ceiling={ceiling_seconds}s)"
                )
                await user.stop("")
                culled += 1
        except Exception as e:
            app.log.warning(f"[Idle Culler] Error handling {user.name}: {e}")

    if culled:
        app.log.info(f"[Idle Culler] Culled {culled} server(s)")
    return culled


def schedule_idle_culler(base_seconds, ceiling_seconds, interval_seconds, max_age_seconds):
    """Start the in-hub idle-culler periodic callback (replaces the external service).

    Call once at startup when culling is enabled. Schedules onto the running
    IOLoop (mirrors `schedule_startup_favicon_callback`); the PeriodicCallback is
    stashed on the app so it is not garbage-collected.
    """
    from tornado.ioloop import IOLoop, PeriodicCallback

    async def _pass():
        try:
            await run_cull_pass(base_seconds, ceiling_seconds, max_age_seconds)
        except Exception:
            from jupyterhub.app import JupyterHub
            JupyterHub.instance().log.exception("[Idle Culler] cull pass failed")

    def _start():
        from jupyterhub.app import JupyterHub
        app = JupyterHub.instance()
        pc = PeriodicCallback(_pass, interval_seconds * 1000)
        pc.start()
        app._stellars_idle_culler_pc = pc  # keep a reference alive
        app.log.info(
            f"[Idle Culler] In-hub culler started - timeout={base_seconds}s, "
            f"ceiling={ceiling_seconds}s, interval={interval_seconds}s, "
            f"max_age={max_age_seconds}s"
        )

    IOLoop.current().add_callback(_start)
