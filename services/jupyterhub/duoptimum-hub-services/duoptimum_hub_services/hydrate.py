"""Startup hydration - warm every cache and fire the deferred checks ONCE at boot.

A freshly-(re)started hub used to show an empty portal until an admin first opened
the Activity page: the activity refreshers (volume sizes, container sizes, GPU
utilisation), the live-stats cache and the image-update snapshot were all started
LAZILY on the first ``/activity`` request. Servers that survived the restart were
therefore invisible (no sizes, no CPU/memory) until that first poll.

This module consolidates the one-time startup work behind a single entry point,
``schedule_startup_hydration``. Everything runs on the IOLoop AFTER the hub is
serving (mirroring ``schedule_policy_startup`` / ``schedule_startup_favicon_callback``)
and is best-effort, so none of it can stall hub boot - the synchronous boot work
(the bounded GPU probe, sidecar self-start, branding) stays where it is in the
config. Hydration covers:

  - survivor CHP favicon routes      (schedule_startup_favicon_callback)
  - survivor policy re-imposition    (schedule_policy_startup)
  - the activity refreshers + warm live stats for surviving servers
  - the image-update snapshot, so "update available" is known up front

``start_activity_refreshers`` is the SINGLE code path the ``/activity`` handler also
uses, so that handler is now a fallback rather than the only trigger.
"""

from .logging_setup import log


def start_activity_refreshers(gpu_list=None):
    """Start the background activity refreshers (idempotent). Each ``start()`` also
    submits an immediate first refresh, so the caches warm right away. GPU
    utilisation is started only when the host has GPUs (enumerated at boot), to
    avoid pointless sidecar polling on a GPU-less host."""
    from .volume_cache import VolumeSizeRefresher
    from .container_size_cache import ContainerSizeRefresher

    VolumeSizeRefresher.get_instance().start()
    ContainerSizeRefresher.get_instance().start()
    if gpu_list:
        from .gpu_cache import GpuUtilizationRefresher
        GpuUtilizationRefresher.get_instance().start()


def _warm_survivor_stats():
    """Trigger a live-stats sample for every lab server that survived the restart,
    so the activity map shows CPU/memory immediately instead of after the first
    ``/activity`` poll. No-op (no docker calls) when nothing survived."""
    from jupyterhub.app import JupyterHub
    from jupyterhub import orm
    from .docker_utils import encode_username_for_docker
    from .container_stats_cache import get_container_stats_with_refresh

    app = JupyterHub.instance()
    active = set()
    for orm_user in app.db.query(orm.User).all():
        user = app.users.get(orm_user.name)
        if user and user.spawner and user.spawner.active:
            active.add(encode_username_for_docker(user.name))
    if active:
        get_container_stats_with_refresh(active)  # seeds the activity-gated stats cache
        log.info(f"[Hydrate] warming live stats for {len(active)} surviving server(s)")


def _check_image_updates(lab_image):
    """Build the image snapshot up front (the slow ``docker image ls`` scan) so the
    per-container 'update available' check is immediate from the first ``/activity``
    request instead of lazily on first access. Logs the configured lab image's state."""
    from .docker_utils import _image_snapshot_get, _normalize_ref, _image_repo

    tag_to_id, newest_by_repo = _image_snapshot_get()
    log.info(f"[Hydrate] image-update snapshot warmed ({len(tag_to_id)} tags); update check is now immediate")
    if not lab_image:
        return
    ref = _normalize_ref(lab_image)
    current = tag_to_id.get(ref)
    newest = newest_by_repo.get(_image_repo(ref))
    if current is None:
        log.info(f"[Hydrate] lab image {ref} not present locally yet")
    elif newest and newest != current:
        log.info(f"[Hydrate] lab image {ref}: a newer local build is available (labs upgrade on restart)")
    else:
        log.info(f"[Hydrate] lab image {ref}: up to date")


def schedule_startup_hydration(stellars_config=None, favicon_uri='', favicon_busy_target='', policy_actx=None):
    """Single startup-hydration entry, deferred to the IOLoop after the hub is up.

    Consolidates everything that must be warmed / re-imposed once at boot so a
    (re)started hub never shows an empty portal until the first ``/activity``
    request. All steps are best-effort and run off the boot thread.

    Args:
        stellars_config: the ``c.JupyterHub.tornado_settings['stellars_config']``
            dict (read ``gpu_list`` + ``lab_image``)
        favicon_uri / favicon_busy_target: passed through to the favicon survivor
            callback
        policy_actx: the spawn hook's ApplyContext
            (``pre_spawn_hook._stellars_apply_context``); None skips policy re-imposition
    """
    from tornado.ioloop import IOLoop
    from .hooks import schedule_policy_startup, schedule_startup_favicon_callback

    # survivor CHP routes + policy re-imposition (each registers its own callback)
    schedule_startup_favicon_callback(favicon_uri=favicon_uri, favicon_busy_target=favicon_busy_target)
    if policy_actx is not None:
        schedule_policy_startup(policy_actx)

    cfg = stellars_config or {}
    gpu_list = cfg.get('gpu_list') or []
    lab_image = cfg.get('lab_image') or ''

    async def _hydrate():
        log.info("[Hydrate] warming caches + image-update check at startup")
        try:
            start_activity_refreshers(gpu_list)
        except Exception as e:
            log.warning(f"[Hydrate] activity refreshers failed: {e}")
        try:
            _warm_survivor_stats()
        except Exception as e:
            log.warning(f"[Hydrate] survivor stats warm failed: {e}")
        try:
            _check_image_updates(lab_image)
        except Exception as e:
            log.warning(f"[Hydrate] image-update check failed: {e}")

    IOLoop.current().add_callback(_hydrate)
