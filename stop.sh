#!/bin/sh
CURRENT_FILE=`readlink -f $0`
CURRENT_DIR=`dirname $CURRENT_FILE`
cd $CURRENT_DIR

# Stop the platform and remove orphaned containers
if [ -f './compose_override.yml' ]; then
    echo "using compose override"
    docker compose --env-file .env \
	-f compose.yml \
	-f compose_override.yml \
	down --remove-orphans
else
    docker compose --env-file .env \
	-f compose.yml \
	down --remove-orphans
fi

# EOF
