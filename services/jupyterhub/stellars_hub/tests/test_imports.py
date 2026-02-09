"""Import tests for stellars_hub package.

Verifies that all modules and public API can be imported without errors.
Runs during Docker build (builder stage) to catch packaging issues early.
"""

import importlib


def test_package_has_version():
    from stellars_hub import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_top_level_imports():
    from stellars_hub import StellarsNativeAuthenticator
    from stellars_hub import setup_branding
    from stellars_hub import register_events
    from stellars_hub import resolve_gpu_mode
    from stellars_hub import make_pre_spawn_hook
    from stellars_hub import schedule_startup_favicon_callback
    from stellars_hub import get_services_and_roles
    from stellars_hub import get_user_volume_suffixes
    assert callable(get_user_volume_suffixes)


def test_volumes():
    from stellars_hub.volumes import get_user_volume_suffixes
    volumes = {
        "jupyterlab-{username}_home": "/home",
        "jupyterlab-{username}_workspace": "/home/lab/workspace",
        "jupyterlab-{username}_cache": "/home/lab/.cache",
        "jupyterhub_shared": "/mnt/shared",
    }
    suffixes = get_user_volume_suffixes(volumes)
    assert isinstance(suffixes, list)
    assert 'home' in suffixes
    assert 'workspace' in suffixes
    assert 'cache' in suffixes


def test_password_cache():
    from stellars_hub.password_cache import cache_password, get_cached_password, clear_cached_password
    cache_password("testuser", "testpass")
    assert get_cached_password("testuser") == "testpass"
    clear_cached_password("testuser")
    assert get_cached_password("testuser") is None


def test_docker_utils():
    from stellars_hub.docker_utils import encode_username_for_docker
    assert encode_username_for_docker("test.user") == "test-2euser"
    assert encode_username_for_docker("simple") == "simple"


def test_activity_model():
    from stellars_hub.activity.model import ActivityBase, ActivitySample
    assert ActivitySample.__tablename__ == 'activity_samples'


def test_activity_monitor_class():
    from stellars_hub.activity.monitor import ActivityMonitor
    assert hasattr(ActivityMonitor, 'get_instance')
    assert hasattr(ActivityMonitor, 'record_sample')
    assert hasattr(ActivityMonitor, 'get_score')


def test_activity_helpers():
    from stellars_hub.activity.helpers import (
        record_activity_sample,
        calculate_activity_score,
        get_activity_sampling_status,
        get_inactive_after_seconds,
        rename_activity_user,
        delete_activity_user,
        initialize_activity_for_user,
        reset_all_activity_data,
        record_samples_for_all_users,
    )
    assert callable(record_activity_sample)


def test_activity_sampler():
    from stellars_hub.activity.sampler import ActivitySampler, start_activity_sampler
    assert hasattr(ActivitySampler, 'get_instance')


def test_activity_service():
    from stellars_hub.activity.service import ActivitySamplerService, main
    assert callable(main)


def test_volume_cache():
    from stellars_hub.volume_cache import (
        VolumeSizeRefresher,
        get_cached_volume_sizes,
        start_volume_size_refresher,
    )
    data, needs_refresh = get_cached_volume_sizes()
    assert isinstance(data, dict)
    assert needs_refresh is True  # No data cached yet


def test_handlers():
    from stellars_hub.handlers import (
        ManageVolumesHandler,
        RestartServerHandler,
        NotificationsPageHandler,
        ActiveServersHandler,
        BroadcastNotificationHandler,
        GetUserCredentialsHandler,
        SettingsPageHandler,
        SessionInfoHandler,
        ExtendSessionHandler,
        ActivityPageHandler,
        ActivityDataHandler,
        ActivityResetHandler,
        ActivitySampleHandler,
        FaviconRedirectHandler,
    )
    # Verify handler count matches expected
    from stellars_hub import handlers
    assert len(handlers.__all__) == 14


def test_auth():
    from stellars_hub.auth import StellarsNativeAuthenticator, CustomAuthorizationAreaHandler
    assert hasattr(StellarsNativeAuthenticator, 'get_handlers')


def test_events():
    from stellars_hub.events import register_events
    assert callable(register_events)


def test_gpu():
    from stellars_hub.gpu import detect_nvidia, resolve_gpu_mode
    assert callable(detect_nvidia)
    assert callable(resolve_gpu_mode)


def test_branding():
    from stellars_hub.branding import setup_branding
    result = setup_branding()
    assert isinstance(result, dict)
    assert 'logo_file' in result
    assert 'favicon_uri' in result


def test_hooks():
    from stellars_hub.hooks import make_pre_spawn_hook, schedule_startup_favicon_callback
    branding = {'lab_main_icon_static': '', 'lab_main_icon_url': '', 'lab_splash_icon_static': '', 'lab_splash_icon_url': ''}
    hook = make_pre_spawn_hook(branding, builtin_groups=['docker-sock', 'docker-privileged'])
    assert callable(hook)


def test_services():
    from stellars_hub.services import get_services_and_roles
    services, roles = get_services_and_roles(
        culler_enabled=0,
        culler_timeout=86400,
        culler_interval=600,
        culler_max_age=0,
        sample_interval=600,
    )
    assert isinstance(services, list)
    assert isinstance(roles, list)
    assert len(services) >= 1  # At least activity-sampler


def test_groups():
    from stellars_hub.groups import ensure_groups
    assert callable(ensure_groups)


def test_all_modules_importable():
    """Verify all package modules can be imported."""
    modules = [
        'stellars_hub',
        'stellars_hub.auth',
        'stellars_hub.branding',
        'stellars_hub.docker_utils',
        'stellars_hub.events',
        'stellars_hub.gpu',
        'stellars_hub.groups',
        'stellars_hub.hooks',
        'stellars_hub.password_cache',
        'stellars_hub.services',
        'stellars_hub.volume_cache',
        'stellars_hub.volumes',
        'stellars_hub.activity',
        'stellars_hub.activity.model',
        'stellars_hub.activity.monitor',
        'stellars_hub.activity.helpers',
        'stellars_hub.activity.sampler',
        'stellars_hub.activity.service',
        'stellars_hub.handlers',
        'stellars_hub.handlers.activity',
        'stellars_hub.handlers.credentials',
        'stellars_hub.handlers.favicon',
        'stellars_hub.handlers.notifications',
        'stellars_hub.handlers.server',
        'stellars_hub.handlers.session',
        'stellars_hub.handlers.settings',
        'stellars_hub.handlers.volumes',
    ]
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Failed to import {mod_name}"
