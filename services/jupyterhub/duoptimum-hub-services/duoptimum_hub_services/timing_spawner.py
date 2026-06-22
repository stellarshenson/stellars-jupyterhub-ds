"""Timing-instrumented DockerSpawner subclass.

Emits ONE `[Timing]` log line per lifecycle method exit, carrying the
method name, username, and elapsed seconds. Designed to be low-volume:
no entry-side logging, no poll-loop logging - just exit summaries.

Also records a single `error` event in the platform event log when a spawn
RAISES (the only place a failed start is observable) - otherwise a crashed
spawn leaves the 'server starting' event with no matching outcome.

Methods instrumented:

  - ``start()``         total spawn time as the hub observes it
  - ``stop()``          total teardown as the hub observes it
  - ``remove_object()`` actual Docker DELETE call (subset of stop)

The delta ``stop() - remove_object()`` is the hub-side lag (poll cadence,
post-stop hooks, clear_state) on top of the Docker-side teardown. If that
delta is large, the bottleneck is the hub, not Docker.

Activation: ``c.JupyterHub.spawner_class =
'duoptimum_hub_services.timing_spawner.TimingDockerSpawner'`` in the hub
config. Drop back to ``dockerspawner.DockerSpawner`` to silence.

Pull the lines after the fact:
    docker logs <hub-container> 2>&1 | grep '\\[Timing\\]'
"""

from __future__ import annotations

import html
import time
from typing import Any

from dockerspawner import DockerSpawner

from .event_log import record_event


class TimingDockerSpawner(DockerSpawner):
    """DockerSpawner with one-line-per-method `[Timing]` probes."""

    async def start(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        t0 = time.perf_counter()
        try:
            return await super().start(*args, **kwargs)
        except Exception:
            # a raised spawn (nvidia prestart 500, image pull error, ...) otherwise leaves
            # no audit trace - the 'server starting' event gets no matching outcome. record
            # one best-effort 'error' event, then re-raise so the hub's error handling is unchanged
            record_event('error', f'<b>{html.escape(str(self.user.name if self.user else "?"))}</b> server failed to start')
            raise
        finally:
            self.log.info(
                "[Timing] start user=%s elapsed=%.3fs",
                self.user.name if self.user else "?",
                time.perf_counter() - t0,
            )

    async def stop(self, now: bool = False) -> None:  # type: ignore[override]
        t0 = time.perf_counter()
        try:
            return await super().stop(now=now)
        finally:
            self.log.info(
                "[Timing] stop user=%s elapsed=%.3fs",
                self.user.name if self.user else "?",
                time.perf_counter() - t0,
            )

    async def remove_object(self) -> None:  # type: ignore[override]
        # remove_object() is the actual Docker DELETE call inside stop().
        # The difference between this elapsed and stop()'s elapsed is the
        # hub-side overhead (poll cadence, hooks, clear_state).
        t0 = time.perf_counter()
        try:
            return await super().remove_object()
        finally:
            self.log.info(
                "[Timing] remove_object user=%s elapsed=%.3fs",
                self.user.name if self.user else "?",
                time.perf_counter() - t0,
            )
