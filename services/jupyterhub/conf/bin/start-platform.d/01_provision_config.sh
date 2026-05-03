#!/bin/bash
# Two-stage config provisioning: operator overlay -> built-in fallback.
#
#   /mnt/user_config                        operator-supplied python files (optional bind-mount, ro)
#   /srv/jupyterhub/jupyterhub_config.py    built-in (baked into image, untouched)
#   /srv/config/                            runtime — populated every boot, what JupyterHub reads
#
# Trigger: presence of the root file (default jupyterhub_config.py, override
# via JUPYTERHUB_USER_CONFIG_FILE) under /mnt/user_config.
#   - missing  -> silent fallback to built-in (operator wants stock)
#   - present  -> strict validation; empty or syntax-broken -> exit 1
#
# Re-runs every boot: /srv/config is wiped and re-populated so operator edits
# under /mnt/user_config take effect on the next container restart, and a
# previous overlay does not linger after the operator removes the bind-mount.
# Server files in /srv/jupyterhub are never written to.

set -e

USER_CONFIG="${JUPYTERHUB_USER_CONFIG_DIR:-/mnt/user_config}"
ROOT="${JUPYTERHUB_USER_CONFIG_FILE:-jupyterhub_config.py}"
RUNTIME="/srv/config"
BUILTIN="/srv/jupyterhub/jupyterhub_config.py"
LOG_PREFIX="[Config]"

log()     { echo "$LOG_PREFIX $*"; }
log_err() { echo "$LOG_PREFIX ERROR: $*" >&2; }

mkdir -p "$RUNTIME"
rm -rf "$RUNTIME"/* 2>/dev/null || true

# Trigger only on root file presence; everything else (siblings, dictionaries,
# yaml) is irrelevant without a root.
if [ ! -f "$USER_CONFIG/$ROOT" ]; then
    cp -a "$BUILTIN" "$RUNTIME/jupyterhub_config.py"
    log "source: built-in (no $USER_CONFIG/$ROOT)"
    exit 0
fi

# Operator opted in -> strict.
if [ ! -s "$USER_CONFIG/$ROOT" ]; then
    log_err "$USER_CONFIG/$ROOT is empty"
    exit 1
fi
# In-memory syntax check via compile(); avoids py_compile's __pycache__/ write
# which would fail under the read-only /mnt/user_config bind-mount even for
# syntactically valid files.
if ! python3 -c 'import sys;f=sys.argv[1];compile(open(f).read(),f,"exec")' "$USER_CONFIG/$ROOT" 2>&1; then
    log_err "$USER_CONFIG/$ROOT failed syntax check (see above)"
    exit 1
fi

cp -a "$USER_CONFIG"/. "$RUNTIME"/
# JupyterHub always reads /srv/config/jupyterhub_config.py; if the operator's
# root has a different name, drop a same-name copy so start-platform.sh can
# load it without knowing the override.
if [ "$ROOT" != "jupyterhub_config.py" ]; then
    cp -a "$RUNTIME/$ROOT" "$RUNTIME/jupyterhub_config.py"
fi

log "source: operator-supplied ($USER_CONFIG/$ROOT)"
log "  copied $(find "$RUNTIME" -maxdepth 1 -type f | wc -l) file(s) to $RUNTIME"

# EOF
