"""Quota accounting helpers - pure functions over Docker API payloads.

Counts come from list responses already narrowed to the owner's label (so a
length is the count). Storage is summed from a ``/system/df`` payload. No I/O
here; the server fetches the payloads and calls these.
"""

from .config import OWNER_LABEL, owner_value, BYTES_PER_GB


def list_count(list_json):
    """Number of resources in a list response (already owner-filtered)."""
    return len(list_json) if isinstance(list_json, list) else 0


def over_count(current, maximum):
    """True if creating one more would exceed the hard count quota."""
    if not maximum or maximum <= 0:
        return False
    return current >= maximum


def _labels_of(obj):
    cfg = obj.get("Config")
    if isinstance(cfg, dict) and isinstance(cfg.get("Labels"), dict):
        return cfg["Labels"]
    labels = obj.get("Labels")
    return labels if isinstance(labels, dict) else {}


def storage_used_bytes(system_df, owner):
    """Sum bytes attributable to ``owner`` from a ``/system/df`` payload.

    Counts owned volume sizes (``Volumes[].UsageData.Size``) and owned
    containers' writable-layer sizes (``Containers[].SizeRw``). Sizes reported
    as -1 (not computed) are ignored.
    """
    total = 0
    df = system_df or {}
    for vol in (df.get("Volumes") or []):
        if _labels_of(vol).get(OWNER_LABEL) == owner_value(owner):
            size = ((vol.get("UsageData") or {}).get("Size")) or 0
            if size > 0:
                total += size
    for cont in (df.get("Containers") or []):
        if (cont.get("Labels") or {}).get(OWNER_LABEL) == owner_value(owner):
            size = cont.get("SizeRw") or 0
            if size > 0:
                total += size
    return total


def over_storage_budget(system_df, owner, max_gb):
    """True if the owner's measured usage already exceeds the GB budget.

    Soft cap: blocks new creates once over, but cannot stop an existing volume
    from growing further (no FS-level wall on Docker Desktop / WSL2).
    """
    if not max_gb or max_gb <= 0:
        return False
    return storage_used_bytes(system_df, owner) > int(max_gb * BYTES_PER_GB)
