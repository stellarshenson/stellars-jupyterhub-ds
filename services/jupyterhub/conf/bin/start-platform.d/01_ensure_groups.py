#!/usr/bin/env python3
"""
Ensure required JupyterHub groups exist at startup.
Groups are defined inline - must match BUILTIN_GROUPS in jupyterhub_config.py.
"""

import sys

from stellars_hub.groups import ensure_groups

if __name__ == '__main__':
    try:
        ensure_groups(['docker-sock', 'docker-privileged'])
    except Exception as e:
        print(f"Error ensuring groups: {e}", file=sys.stderr)
        sys.exit(1)
