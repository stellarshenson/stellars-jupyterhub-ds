"""Stellars JupyterHub platform logic package."""

__version__ = "3.8.0"

from .abuse_protection import (
    apply_abuse_protection,
    build_app_protection,
    parse_int,
    ratelimit_disabled,
)
from .api_keys_pool import (
    PoolManager,
    env_for_slot,
    mask_last4,
    merge_pool_on_save,
    normalize_pool,
    parse_pool_labels,
    pick_free_slot,
    pool_label_key,
)
from .auth import StellarsNativeAuthenticator
from .branding import setup_branding
from .docker_proxy import register_user, unregister_user
from .events import register_events
from .gpu import is_wsl2, resolve_gpu_mode
from .hooks import (
    make_pre_spawn_hook,
    schedule_policy_startup,
    schedule_startup_favicon_callback,
)
from .idle_culler import (
    calc_available_hours,
    calc_ceiling,
    calc_extended_remaining,
    calc_remaining,
    remaining_seconds_for,
    run_cull_pass,
    schedule_idle_culler,
    should_cull,
)
from .services import get_services_and_roles
from .volume_cache import configure_volume_cache
from .volumes import (
    get_user_volume_name_templates,
    get_user_volume_suffixes,
    load_merged_user_volumes,
)

__all__ = [
    "PoolManager",
    "apply_abuse_protection",
    "build_app_protection",
    "parse_int",
    "ratelimit_disabled",
    "StellarsNativeAuthenticator",
    "env_for_slot",
    "mask_last4",
    "merge_pool_on_save",
    "normalize_pool",
    "parse_pool_labels",
    "pick_free_slot",
    "pool_label_key",
    "calc_available_hours",
    "calc_ceiling",
    "calc_extended_remaining",
    "calc_remaining",
    "remaining_seconds_for",
    "configure_volume_cache",
    "register_user",
    "unregister_user",
    "get_services_and_roles",
    "run_cull_pass",
    "schedule_idle_culler",
    "should_cull",
    "get_user_volume_name_templates",
    "get_user_volume_suffixes",
    "is_wsl2",
    "load_merged_user_volumes",
    "make_pre_spawn_hook",
    "schedule_policy_startup",
    "register_events",
    "resolve_gpu_mode",
    "schedule_startup_favicon_callback",
    "setup_branding",
]
