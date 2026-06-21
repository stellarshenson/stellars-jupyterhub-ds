#!/bin/bash
# Shared INFO-format logger for the pre-hub start-platform.d scripts (SOURCED, not run).
#
# These scripts run before the hub starts, so there is no Python logger - they used to
# echo bare lines to stdout. This emits a line shaped like the JupyterHub tornado log,
# `[I <ts> <component>] message`, so the pre-hub output reads consistently with the hub's
# own INFO logs. Colour only when stdout is a TTY (plain in piped container logs) -
# "coloured if the terminal permits". Source it, then set LOG_COMPONENT before logging:
#
#   LOG_COMPONENT="Certificates"
#   source /platform-log.sh
#   log "applying operator certs"      # -> [I 2026-06-21 01:12:58.887 Certificates] applying operator certs
#   log_warn "..."                     # W, to stderr
#   log_err  "..."                     # E, to stderr
_plog() {
    local lvl="$1"; shift
    local color='' reset=''
    if [ -t 1 ]; then
        reset=$'\033[0m'
        case "$lvl" in I) color=$'\033[32m' ;; W) color=$'\033[33m' ;; E) color=$'\033[31m' ;; esac
    fi
    printf '%s[%s %s %s]%s %s\n' "$color" "$lvl" "$(date '+%Y-%m-%d %H:%M:%S.%3N')" "${LOG_COMPONENT:-Platform}" "$reset" "$*"
}
log()      { _plog I "$*"; }
log_warn() { _plog W "$*" >&2; }
log_err()  { _plog E "$*" >&2; }
