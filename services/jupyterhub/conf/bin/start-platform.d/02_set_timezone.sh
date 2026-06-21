#!/bin/bash
# ----------------------------------------------------------------------------------------
# Sets system timezone from JUPYTERHUB_TIMEZONE environment variable
# ----------------------------------------------------------------------------------------

TZ_NAME="${JUPYTERHUB_TIMEZONE:-Etc/UTC}"
LOG_COMPONENT="Timezone"
source /platform-log.sh   # log -> INFO-format line (see conf/bin/platform-log.sh)

if [ -n "$TZ_NAME" ] && [ -f "/usr/share/zoneinfo/$TZ_NAME" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ_NAME" /etc/localtime
    echo "$TZ_NAME" > /etc/timezone   # writes the tz FILE, not a log line
    export TZ="$TZ_NAME"
    log "Timezone set to $TZ_NAME"
else
    log "Timezone: UTC (default)"
fi

# EOF
