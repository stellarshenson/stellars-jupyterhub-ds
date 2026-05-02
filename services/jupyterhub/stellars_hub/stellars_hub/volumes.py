"""Volume suffix extraction and user volume management."""


def get_user_volume_suffixes(volumes_dict, compose_project="jupyterhub"):
    """Extract volume suffixes from volumes dict matching <project>_jupyterlab_{username}_<suffix> pattern."""
    pattern = f"{compose_project}_jupyterlab_{{username}}_"
    suffixes = []
    for volume_name in volumes_dict.keys():
        if volume_name.startswith(pattern):
            suffix = volume_name[len(pattern):]
            suffixes.append(suffix)
    return suffixes


def get_user_volume_name_templates(volumes_dict, compose_project="jupyterhub"):
    """Map suffix -> full volume-name template (with the `{username}` placeholder still in it).

    Single source of truth for what a per-user volume is actually called on
    disk: pulled directly from DOCKER_SPAWNER_VOLUMES keys so the UI label,
    the deletion handler, and DockerSpawner all agree on one name pattern.

        {f"{cp}_jupyterlab_{{username}}_home": "/home", ...}
            -> {"home": f"{cp}_jupyterlab_{{username}}_home", ...}
    """
    pattern = f"{compose_project}_jupyterlab_{{username}}_"
    return {
        volume_name[len(pattern):]: volume_name
        for volume_name in volumes_dict.keys()
        if volume_name.startswith(pattern)
    }
