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
