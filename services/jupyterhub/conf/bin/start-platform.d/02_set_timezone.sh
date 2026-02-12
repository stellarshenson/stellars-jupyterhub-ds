#!/bin/bash
# ----------------------------------------------------------------------------------------
# Sets system timezone from JUPYTERHUB_TIMEZONE environment variable
# ----------------------------------------------------------------------------------------

TZ_NAME="${JUPYTERHUB_TIMEZONE:-Etc/UTC}"

if [ -n "$TZ_NAME" ] && [ -f "/usr/share/zoneinfo/$TZ_NAME" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ_NAME" /etc/localtime
    echo "$TZ_NAME" > /etc/timezone
    export TZ="$TZ_NAME"
    echo "Timezone set to $TZ_NAME"
else
    echo "Timezone: UTC (default)"
fi

# EOF
