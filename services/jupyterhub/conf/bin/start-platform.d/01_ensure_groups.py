#!/usr/bin/env python3
"""
Ensure required JupyterHub groups exist at startup.
Reads the list of groups from jupyterhub_config.py::BUILTIN_GROUPS.
This script runs before JupyterHub starts to create any missing groups.
"""

import os
import sys

def ensure_groups():
    """Create groups defined in BUILTIN_GROUPS if they don't exist"""
    # Import JupyterHub ORM and config
    sys.path.insert(0, '/srv/jupyterhub')

    from jupyterhub import orm
    from jupyterhub.orm import Group

    # Import BUILTIN_GROUPS from config (single source of truth)
    try:
        # Read the config file to extract BUILTIN_GROUPS
        config_globals = {}
        with open('/srv/jupyterhub/jupyterhub_config.py', 'r') as f:
            config_content = f.read()
            # Extract just the BUILTIN_GROUPS definition
            for line in config_content.split('\n'):
                if line.startswith('BUILTIN_GROUPS'):
                    exec(line, config_globals)
                    break

        groups_to_create = config_globals.get('BUILTIN_GROUPS', [])
    except Exception as e:
        print(f"Warning: Could not read BUILTIN_GROUPS from config: {e}")
        print("Skipping group creation")
        return

    if not groups_to_create:
        print("No groups to create (BUILTIN_GROUPS is empty)")
        return

    # Connect to the database
    db_url = os.environ.get('JUPYTERHUB_DB_URL', 'sqlite:////data/jupyterhub.sqlite')
    db = orm.new_session_factory(db_url)()

    print(f"Ensuring {len(groups_to_create)} group(s) exist...")
    for group_name in groups_to_create:
        # Check if group exists
        existing_group = db.query(Group).filter(Group.name == group_name).first()

        if not existing_group:
            # Create the group
            print(f"  Creating group: {group_name}")
            new_group = Group(name=group_name)
            db.add(new_group)
            db.commit()
            print(f"  ✓ Group '{group_name}' created")
        else:
            print(f"  ✓ Group '{group_name}' exists")

    db.close()
    print("Group check complete\n")

if __name__ == '__main__':
    try:
        ensure_groups()
    except Exception as e:
        print(f"Error ensuring groups: {e}", file=sys.stderr)
        sys.exit(1)
