"""NVIDIA implementation of the Stellars GPU-info sidecar API.

A long-running peer the hub queries over a dedicated network instead of spawning
an ephemeral nvidia container per probe. The HTTP contract (``/health``,
``/gpus``) is vendor-neutral - future amd / intel / applesilicon sidecars
implement the same schema, so the hub stays vendor-agnostic.
"""

__version__ = "0.1.0"
