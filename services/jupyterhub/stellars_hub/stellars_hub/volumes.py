"""Volume suffix extraction and user volume management."""


def get_user_volume_suffixes(volumes_dict):
    """Extract volume suffixes from volumes dict matching jupyterlab-{username}_<suffix> pattern."""
    suffixes = []
    for volume_name in volumes_dict.keys():
        if volume_name.startswith("jupyterlab-{username}_"):
            suffix = volume_name.replace("jupyterlab-{username}_", "")
            suffixes.append(suffix)
    return suffixes
