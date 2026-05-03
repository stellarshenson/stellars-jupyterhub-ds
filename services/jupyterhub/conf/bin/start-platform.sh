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
jupyterhub -f /srv/config/jupyterhub_config.py $@

# EOF

