#!/bin/sh 
CURRENT_FILE=`readlink -f $0`
CURRENT_DIR=`dirname $CURRENT_FILE`
cd $CURRENT_DIR

# first pull the jupyterlab and jupyterhub image
docker pull stellars/stellars-jupyterlab-ds:latest
docker pull stellars/stellars-jupyterhub-ds:latest

# Run the command for when GPU is not available
if [ -f './compose_override.yml' ]; then
    echo "using compose override"
    docker compose --env-file .env \
	-f compose.yml \
	-f compose_override.yml \
	up  --no-recreate --no-build -d
else
    docker compose --env-file .env \
	-f compose.yml \
	up  --no-recreate --no-build -d
fi

# EOF
