"""Built-in group management for JupyterHub startup."""

import os


def ensure_groups(builtin_groups):
    """Create groups defined in builtin_groups if they don't exist.

    Args:
        builtin_groups: list of group names to ensure exist

    Called from startup script (01_ensure_groups.py) before JupyterHub starts.
    """
    from jupyterhub import orm
    from jupyterhub.orm import Group

    if not builtin_groups:
        print("No groups to create (builtin_groups is empty)")
        return

    db_url = os.environ.get('JUPYTERHUB_DB_URL', 'sqlite:////data/jupyterhub.sqlite')
    db = orm.new_session_factory(db_url)()

    print(f"Ensuring {len(builtin_groups)} group(s) exist...")
    for group_name in builtin_groups:
        existing_group = db.query(Group).filter(Group.name == group_name).first()
        if not existing_group:
            print(f"  Creating group: {group_name}")
            new_group = Group(name=group_name)
            db.add(new_group)
            db.commit()
            print(f"  Group '{group_name}' created")
        else:
            print(f"  Group '{group_name}' exists")

    db.close()
    print("Group check complete\n")
