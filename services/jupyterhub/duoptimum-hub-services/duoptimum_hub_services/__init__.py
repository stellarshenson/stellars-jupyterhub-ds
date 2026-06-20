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
from .auth import DuoptimumHubAuthenticator, DuoptimumSignUpHandler, StellarsNativeAuthenticator
from .branding import setup_branding
from .docker_proxy import register_user, unregister_user
from .events import register_events
from .gpu import gpu_summary_lines, is_wsl2, resolve_gpu_mode
from .gpuinfo_sidecar import ensure_gpuinfo_sidecar, resolve_gpuinfo_url, stop_gpuinfo_sidecar
from .hooks import (
    make_post_stop_hook,
    make_pre_spawn_hook,
    schedule_policy_startup,
    schedule_startup_favicon_callback,
)
from .host import resolve_memory_quota_mb
from .hydrate import schedule_startup_hydration, start_activity_refreshers
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
from .config_validator import ValidationResult, validate_hub_config
from .gpu_cache import configure_gpu_cache
from .sent_notification_log import prepare_sent_notification_log, record_sent_notification
from .services import get_services_and_roles
from .volume_cache import configure_volume_cache
from .volumes import (
    get_user_volume_name_templates,
    get_user_volume_roles,
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
    "DuoptimumHubAuthenticator",
    "DuoptimumSignUpHandler",
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
    "configure_gpu_cache",
    "configure_volume_cache",
    "prepare_sent_notification_log",
    "record_sent_notification",
    "ensure_gpuinfo_sidecar",
    "stop_gpuinfo_sidecar",
    "resolve_gpuinfo_url",
    "register_user",
    "unregister_user",
    "get_services_and_roles",
    "run_cull_pass",
    "schedule_idle_culler",
    "should_cull",
    "get_user_volume_name_templates",
    "get_user_volume_roles",
    "validate_hub_config",
    "ValidationResult",
    "get_user_volume_suffixes",
    "gpu_summary_lines",
    "is_wsl2",
    "load_merged_user_volumes",
    "make_pre_spawn_hook",
    "make_post_stop_hook",
    "schedule_policy_startup",
    "register_events",
    "resolve_gpu_mode",
    "resolve_memory_quota_mb",
    "schedule_startup_favicon_callback",
    "schedule_startup_hydration",
    "setup_branding",
    "start_activity_refreshers",
]
