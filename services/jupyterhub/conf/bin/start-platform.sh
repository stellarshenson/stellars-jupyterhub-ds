#!/bin/bash

# run series of start scripts (services will need to run in background)
START_PLATFORM_DIR='/start-platform.d'
for file in $START_PLATFORM_DIR/*; do
    if [ -f "$file" ] && [ -x "$file" ]; then
        "$file" 
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

