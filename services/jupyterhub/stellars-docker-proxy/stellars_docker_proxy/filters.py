"""Pure request/response transforms that scope the Docker API to one owner.

No I/O, no aiohttp, no JupyterHub - just dict/JSON in, dict/JSON out, so the
ownership/labeling/quota contract is unit-testable in isolation. The server
layer calls these to mutate request bodies and query params before forwarding
to the real daemon.
"""

import json

from .config import OWNER_LABEL, MANAGED_LABEL, BYTES_PER_GB, NANO_PER_CORE

# Docker Compose / Docker Desktop group containers by this label.
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"


def has_compose_project(body):
    """True if a create body already declares a compose project (user's own
    `docker compose`) - such containers are left as-is (name + project)."""
    labels = (body or {}).get("Labels") or {}
    return bool(labels.get(COMPOSE_PROJECT_LABEL))


def inject_compose_project(body, project):
    """Group an ad-hoc container under ``project`` via the compose project label.

    No-op when ``project`` is empty or the body already declares a compose
    project (respect the user's own compose).
    """
    if not project or has_compose_project(body):
        return dict(body or {})
    out = dict(body or {})
    labels = dict(out.get("Labels") or {})
    labels[COMPOSE_PROJECT_LABEL] = project
    out["Labels"] = labels
    return out


def owner_labels(owner):
    """Labels stamped on every created resource."""
    return {OWNER_LABEL: owner, MANAGED_LABEL: "true"}


def inject_labels(body, owner):
    """Return a copy of a create body with owner+managed labels attached.

    Container, volume and network create bodies all carry a top-level ``Labels``
    map, so the same injection works for all three.
    """
    out = dict(body or {})
    labels = dict(out.get("Labels") or {})
    labels[OWNER_LABEL] = owner
    labels[MANAGED_LABEL] = "true"
    out["Labels"] = labels
    return out


def ensure_name_prefix(name, prefix):
    """Force the per-user name prefix onto a container name.

    Empty/None -> None: let Docker auto-name; ownership is still carried by the
    injected label, so filtering is unaffected.
    """
    if not name:
        return None
    if name.startswith(prefix):
        return name
    return prefix + name


def merge_label_filter(filters_param, owner):
    """Return a ``filters`` query JSON string narrowed to the owner's label.

    Docker's ``filters`` arg is a map of key -> list of values; multiple label
    constraints are AND-ed, so a user can only ever narrow *within* their own
    resources, never widen to someone else's.
    """
    try:
        current = json.loads(filters_param) if filters_param else {}
        if not isinstance(current, dict):
            current = {}
    except (json.JSONDecodeError, TypeError):
        current = {}
    labels = [v for v in (current.get("label") or []) if isinstance(v, str)]
    constraint = f"{OWNER_LABEL}={owner}"
    if constraint not in labels:
        labels.append(constraint)
    current["label"] = labels
    return json.dumps(current)


def _labels_of(inspect_json):
    """Extract the labels map from a container/volume/network inspect payload.

    Containers nest labels under ``Config.Labels``; volumes and networks carry a
    top-level ``Labels``.
    """
    if not inspect_json:
        return {}
    cfg = inspect_json.get("Config")
    if isinstance(cfg, dict) and isinstance(cfg.get("Labels"), dict):
        return cfg["Labels"]
    labels = inspect_json.get("Labels")
    return labels if isinstance(labels, dict) else {}


def is_owned(inspect_json, owner):
    """True if an inspect payload is owned by ``owner`` (by owner label)."""
    return _labels_of(inspect_json).get(OWNER_LABEL) == owner


def caps_violation(body, cpu_cap_cores, mem_cap_gb):
    """Return an error message if a container create body exceeds caps, else None.

    Reads ``HostConfig.NanoCpus`` (cores * 1e9) and ``HostConfig.Memory`` (bytes).
    A cap of 0 means "no cap".
    """
    hc = (body or {}).get("HostConfig") or {}
    if cpu_cap_cores and cpu_cap_cores > 0:
        nano = hc.get("NanoCpus") or 0
        if nano and nano > int(cpu_cap_cores * NANO_PER_CORE):
            return f"CPU request exceeds group cap of {cpu_cap_cores} cores"
    if mem_cap_gb and mem_cap_gb > 0:
        mem = hc.get("Memory") or 0
        if mem and mem > int(mem_cap_gb * BYTES_PER_GB):
            return f"Memory request exceeds group cap of {mem_cap_gb} GB"
    return None


def apply_caps(body, cpu_cap_cores, mem_cap_gb):
    """Return a copy of a container create body with caps injected as ceilings.

    Only fills in a cap when the user left it unset (0/absent). Assumes
    ``caps_violation`` already passed, so an explicit smaller request is kept.
    """
    out = dict(body or {})
    hc = dict(out.get("HostConfig") or {})
    if cpu_cap_cores and cpu_cap_cores > 0 and not hc.get("NanoCpus"):
        hc["NanoCpus"] = int(cpu_cap_cores * NANO_PER_CORE)
    if mem_cap_gb and mem_cap_gb > 0 and not hc.get("Memory"):
        hc["Memory"] = int(mem_cap_gb * BYTES_PER_GB)
    out["HostConfig"] = hc
    return out


def dangerous_reason(body):
    """Return a reason string if a container create body asks for something unsafe.

    Covers the escape/host-access vectors: privileged, host bind mounts (incl.
    the docker socket), host network/PID namespaces, added capabilities, and
    device passthrough. Named-volume mounts (``Type=volume``) are allowed.
    """
    hc = (body or {}).get("HostConfig") or {}
    if hc.get("Privileged"):
        return "privileged containers are not allowed"
    if hc.get("Binds"):
        return "host path bind mounts are not allowed"
    for m in (hc.get("Mounts") or []):
        if isinstance(m, dict) and m.get("Type") == "bind":
            return "host path bind mounts are not allowed"
    if (hc.get("NetworkMode") or "") == "host":
        return "host network mode is not allowed"
    if (hc.get("PidMode") or "") == "host":
        return "host PID namespace is not allowed"
    if hc.get("CapAdd"):
        return "added capabilities are not allowed"
    if hc.get("Devices"):
        return "device passthrough is not allowed"
    return None
