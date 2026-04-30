"""Volume suffix extraction and user volume management."""


def get_user_volume_suffixes(volumes_dict, container_prefix="jupyterlab"):
    """Extract volume suffixes from volumes dict matching <prefix>-{username}_<suffix> pattern."""
    pattern = f"{container_prefix}-{{username}}_"
    suffixes = []
    for volume_name in volumes_dict.keys():
        if volume_name.startswith(pattern):
            suffix = volume_name[len(pattern):]
            suffixes.append(suffix)
    return suffixes
