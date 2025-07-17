#!/bin/sh 
CURRENT_FILE=`readlink -f $0`
CURRENT_DIR=`dirname $CURRENT_FILE`
cd $CURRENT_DIR

# Run the command for when GPU is not available
if [[ -f './compose-override.yml' ]]; then
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
