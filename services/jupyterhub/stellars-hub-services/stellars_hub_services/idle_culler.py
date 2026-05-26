"""Idle-culler calculations and the in-hub cull runtime.

Single source of truth for the session-extension feature. The home-page
countdown, the extend offer/apply logic, the admin activity dashboard, and the
actual cull decision all use the pure functions below, so what a user is shown
can never diverge from when the server is really stopped.

Model (all time in seconds unless noted; the extend UI works in whole hours):

    base_s      = idle timeout the server starts with
    max_ext_h   = maximum extension, whole hours
    ceiling_s   = base_s + max_ext_h*3600          # absolute cap on *remaining*
    ext_used_h  = granted extension hours (state['extension_hours_used'])
    effective_s = base_s + ext_used_h*3600         # idle budget the culler enforces
    elapsed_s   = now - last_activity
    remaining_s = clamp(effective_s - elapsed_s, 0, ceiling_s)
    offer_h     = floor((ceiling_s - remaining_s) / 3600)   # replenish + headroom
    extend(h):  ext_used_h += h                     # h already clamped to offer_h
    cull when:  elapsed_s >= effective_s   (or age >= max_age_s when max_age_s > 0)

Replenish: idle time already spent shows up in `offer_h` (the gap from the
current remaining up to the ceiling), so a user may opt to refill remaining all
the way back to the ceiling. `ext_used_h` is allowed to exceed `max_ext_h` -
that is what makes already-elapsed idle time recoverable - while `remaining_s`
is clamped to the ceiling so it can never *display* more than the ceiling, even
after activity resets `elapsed` to 0. The clamp is conservative: a server only
ever lives at least as long as the displayed remaining, never less.

Heavy imports (tornado, jupyterhub) are done inside the runtime functions so
this module imports with only the standard library - the pure calculations stay
trivially testable.
"""

from datetime import timezone


# ── Pure calculations (stdlib only) ─────────────────────────────────────────

def calc_effective_timeout(timeout_seconds, extensions_used_hours):
    """Idle budget enforced by the culler: base timeout + granted extension hours."""
    return timeout_seconds + extensions_used_hours * 3600


def calc_ceiling(timeout_seconds, max_extension_hours):
    """Absolute cap on *remaining* time (base + max extension)."""
    return timeout_seconds + max_extension_hours * 3600


def calc_time_remaining(effective_timeout, elapsed_seconds, ceiling=None):
    """Seconds until cull, floored at 0 and (when given) clamped to the ceiling.

    Clamping to the ceiling keeps a replenished session from ever displaying more
    than the ceiling once activity resets elapsed to 0 - the effective budget may
    legitimately exceed the ceiling after a replenish-while-idle extend.
    """
    remaining = effective_timeout - elapsed_seconds
    if remaining < 0:
        remaining = 0
    if ceiling is not None and remaining > ceiling:
        remaining = ceiling
    return remaining


def calc_available_hours(ceiling, time_remaining):
    """Whole hours a user may add now: the gap from remaining up to the ceiling.

    This is the replenish offer - it includes both unused extension headroom and
    the idle time already elapsed (whatever drew remaining below the ceiling).
    """
    gap = ceiling - time_remaining
    if gap < 0:
        gap = 0
    return int(gap / 3600)


def calc_new_extensions(current_extensions, hours):
    """Granted extension hours after adding `hours`.

    `hours` is expected to be already clamped to the available offer by the
    caller (which bounds remaining at the ceiling), so this is a plain sum and
    may exceed max_extension - that is how already-elapsed idle time is
    replenished.
    """
    return current_extensions + hours


def _as_utc(dt):
    """Normalise a possibly-naive datetime to tz-aware UTC (JupyterHub stores naive UTC)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def should_cull(now, last_activity, started, effective_seconds, max_age_seconds=0):
    """Decide whether a server should be stopped.

    Cull when inactivity (`now - last_activity`, falling back to age when there
    is no recorded activity) has reached the effective idle budget, or -
    independently - when the server's age has reached `max_age_seconds` (only
    checked when it is > 0). Mirrors the stock jupyterhub-idle-culler semantics
    but uses the per-server effective budget so granted extensions are honoured.
    """
    now = _as_utc(now)
    last_activity = _as_utc(last_activity)
    started = _as_utc(started)

    reference = last_activity if last_activity is not None else started
    inactive = (now - reference).total_seconds() if reference is not None else None

    should = inactive is not None and inactive >= effective_seconds

    if max_age_seconds and started is not None:
        age = (now - started).total_seconds()
        if age >= max_age_seconds:
            should = True

    return should


# ── In-hub cull runtime (heavy imports done lazily) ─────────────────────────

async def run_cull_pass(base_seconds, max_age_seconds):
    """One cull sweep over all active servers, run inside the hub process.

    Reads each server's granted extension directly from `orm_spawner.state`
    (the same store the UI handlers use) so per-user extensions actually delay
    the cull - the external jupyterhub-idle-culler cannot see this state, since
    the REST API exposes `spawner.get_state()` rather than the stored state.
    Returns the number of servers culled.
    """
    from datetime import datetime
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
            state = orm_spawner.state or {}
            ext_used_h = state.get("extension_hours_used", 0)
            effective_s = calc_effective_timeout(base_seconds, ext_used_h)

            if should_cull(
                now,
                orm_spawner.last_activity,
                orm_spawner.started,
                effective_s,
                max_age_seconds,
            ):
                app.log.info(
                    f"[Idle Culler] Culling {user.name} "
                    f"(effective={effective_s}s, ext_used={ext_used_h}h)"
                )
                await user.stop("")
                culled += 1
        except Exception as e:
            app.log.warning(f"[Idle Culler] Error handling {user.name}: {e}")

    if culled:
        app.log.info(f"[Idle Culler] Culled {culled} server(s)")
    return culled


def schedule_idle_culler(base_seconds, interval_seconds, max_age_seconds):
    """Start the in-hub idle-culler periodic callback (replaces the external service).

    Call once at startup when culling is enabled. Schedules onto the running
    IOLoop (mirrors `schedule_startup_favicon_callback`); the PeriodicCallback is
    stashed on the app so it is not garbage-collected.
    """
    from tornado.ioloop import IOLoop, PeriodicCallback

    async def _pass():
        try:
            await run_cull_pass(base_seconds, max_age_seconds)
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
            f"interval={interval_seconds}s, max_age={max_age_seconds}s"
        )

    IOLoop.current().add_callback(_start)
