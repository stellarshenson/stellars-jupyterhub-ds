#!/bin/bash

# run series of start scripts (services will need to run in background)
START_PLATFORM_DIR='/start-platform.d'
for file in $START_PLATFORM_DIR/*; do
    if [ -f "$file" ] && [ -x "$file" ]; then
        "$file" 
    fi
done

# run jupyterhub, env params are configured in Dockerfile and docker-compose yml
# config path is /srv/config/jupyterhub_config.py - populated every boot by
# 01_provision_config.sh from /mnt/user_config (operator) or /srv/jupyterhub (built-in)
# exec so jupyterhub becomes PID 1 and receives docker's SIGTERM directly on
# `docker stop` / compose down/restart - without exec the signal hits this shell
# (which does not forward it), jupyterhub is SIGKILLed after the grace period and
# its atexit cleanup (e.g. stop_gpuinfo_sidecar) never runs.
exec jupyterhub -f /srv/config/jupyterhub_config.py "$@"

# EOF

