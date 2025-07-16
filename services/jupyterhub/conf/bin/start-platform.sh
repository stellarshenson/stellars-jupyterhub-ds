#!/bin/bash

# run series of start scripts (services will need to run in background)
START_PLATFORM_DIR='/start-platform.d'
for file in $START_PLATFORM_DIR/*; do
    if [ -f "$file" ] && [ -x "$file" ]; then
        "$file" 
    fi
done

# run jupyterhub, env params are configured in Dockerfile and docker-compose yml 
jupyterhub -f /srv/jupyterhub/jupyterhub_config.py

# EOF

