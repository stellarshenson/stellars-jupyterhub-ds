"""Volume suffix extraction and user volume management."""

import os


def _load_volumes_yaml(path):
    """Load a suffix-keyed user-volumes YAML; return {} if path is empty/missing."""
    if not path or not os.path.exists(path):
        return {}
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"User volumes YAML at {path!r} must be a mapping (got {type(data).__name__})")
    return data


def load_merged_user_volumes(defaults_path, overrides_path, compose_project="jupyterhub"):
    """Load + merge platform-defaults and operator-overrides user-volume YAMLs.

    Both files are suffix-keyed mappings (e.g. ``home: {mount: ..., description: ...}``).
    Per-suffix shallow merge: operator-supplied fields win, missing fields
    fall back to the platform default. Suffixes only present in the operator
    file are added verbatim.

    Returns ``USER_VOLUMES`` keyed by full volume-name pattern with the
    ``{username}`` placeholder still in place, e.g.::

        {f"{cp}_jupyterlab_{{username}}_home": {"mount": "/home", "description": "..."}}
    """
    defaults = _load_volumes_yaml(defaults_path)
    overrides = _load_volumes_yaml(overrides_path)
    merged = {}
    for suffix in set(defaults) | set(overrides):
        merged[suffix] = {**defaults.get(suffix, {}), **overrides.get(suffix, {})}
    return {
        f"{compose_project}_jupyterlab_{{username}}_{suffix}": data
        for suffix, data in merged.items()
    }


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
