#!/bin/bash

# run series of start scripts (synchronous provisioning: certs, config, timezone).
# each MUST succeed - a failure must abort the boot LOUDLY, not fall through to
# exec. 01_provision_config.sh wipes /srv/config before validating, so on a broken
# operator config it exits non-zero leaving /srv/config empty; without this check
# the old loop exec'd the hub at a missing -f path (traitlets silently skips it)
# and booted bone-stock JupyterHub behind the live proxy routes - broken logins,
# no spawns, no crash to alert on.
START_PLATFORM_DIR='/start-platform.d'
for file in "$START_PLATFORM_DIR"/*; do
    if [ -f "$file" ] && [ -x "$file" ]; then
        "$file"
        rc=$?
        if [ "$rc" -ne 0 ]; then
            echo "[start-platform] FATAL: $file exited $rc - aborting boot" >&2
            exit "$rc"
        fi
    fi
done

# run the hub via the DuoptimumHub subclass (duoptimum-hub console script, shipped
# by duoptimum-hub-services) instead of the stock `jupyterhub` command - same CLI,
# plus our registered_handlers trait. env params configured in Dockerfile + compose.
# config path is /srv/config/jupyterhub_config.py - populated every boot by
# 01_provision_config.sh from /mnt/user_config (operator) or /srv/jupyterhub (built-in)
# exec so the hub becomes PID 1 and receives docker's SIGTERM directly on
# `docker stop` / compose down/restart - without exec the signal hits this shell
# (which does not forward it), the hub is SIGKILLed after the grace period and
# its atexit cleanup (e.g. stop_gpuinfo_sidecar) never runs.
exec duoptimum-hub -f /srv/config/jupyterhub_config.py "$@"

# EOF

