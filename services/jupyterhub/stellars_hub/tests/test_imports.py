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
        "jupyterhub_jupyterlab_{username}_home": "/home",
        "jupyterhub_jupyterlab_{username}_workspace": "/home/lab/workspace",
        "jupyterhub_jupyterlab_{username}_cache": "/home/lab/.cache",
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
        HealthCheckHandler,
        GroupsPageHandler,
        GroupsDataHandler,
        GroupsCreateHandler,
        GroupsDeleteHandler,
        GroupsConfigHandler,
        GroupsReorderHandler,
    )
    # Verify handler count matches expected
    from stellars_hub import handlers
    assert len(handlers.__all__) == 21


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
    import asyncio
    import logging
    import types

    from stellars_hub.hooks import make_pre_spawn_hook, schedule_startup_favicon_callback
    branding = {'lab_main_icon_static': '', 'lab_main_icon_url': '', 'lab_splash_icon_static': '', 'lab_splash_icon_url': ''}
    hook = make_pre_spawn_hook(
        branding,
        gpu_available=False,
        reserved_env_var_names=frozenset({'JUPYTERLAB_TIMEZONE'}),
        reserved_env_var_prefixes=('JUPYTERHUB_',),
        compose_project='actone-ds',
    )
    assert callable(hook)

    # Drive the hook against a minimal dummy spawner to verify compose labels
    # are written into extra_create_kwargs. GroupsConfigManager.get_instance()
    # is wrapped in try/except inside the hook, so a missing DB falls through
    # to an empty config list - safe in this environment.
    spawner = types.SimpleNamespace(
        user=types.SimpleNamespace(name='alice', groups=[]),
        volumes={},
        extra_host_config={},
        environment={},
        extra_create_kwargs={},
        mem_limit=None,
        log=logging.getLogger('test_hooks'),
    )
    asyncio.run(hook(spawner))
    labels = spawner.extra_create_kwargs.get('labels') or {}
    assert labels.get('com.docker.compose.project') == 'actone-ds'
    assert labels.get('com.docker.compose.service') == 'jupyterlab_alice'
    assert labels.get('com.docker.compose.container-number') == '1'
    assert labels.get('com.docker.compose.oneoff') == 'False'

    # When compose_project is empty the hook must NOT inject compose labels.
    hook_no_project = make_pre_spawn_hook(
        branding,
        gpu_available=False,
        reserved_env_var_names=frozenset(),
        reserved_env_var_prefixes=(),
        compose_project='',
    )
    spawner2 = types.SimpleNamespace(
        user=types.SimpleNamespace(name='bob', groups=[]),
        volumes={},
        extra_host_config={},
        environment={},
        extra_create_kwargs={},
        mem_limit=None,
        log=logging.getLogger('test_hooks'),
    )
    asyncio.run(hook_no_project(spawner2))
    assert 'labels' not in spawner2.extra_create_kwargs


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


def test_groups_config():
    from stellars_hub.groups_config import GroupsConfigBase, GroupConfig, GroupsConfigManager, validate_group_name
    assert GroupConfig.__tablename__ == 'groups_config'
    valid, msg = validate_group_name("test-group_1")
    assert valid
    valid, msg = validate_group_name("bad name!")
    assert not valid
    valid, msg = validate_group_name("")
    assert not valid
    valid, msg = validate_group_name("1starts-with-digit")
    assert not valid


def test_group_resolver():
    from stellars_hub.group_resolver import resolve_group_config, is_reserved_env_var

    reserved_names = frozenset({'JUPYTERLAB_TIMEZONE', 'NVIDIA_DETECTED'})
    reserved_prefixes = ('JUPYTERHUB_', 'JPY_')

    # is_reserved_env_var: prefix, exact, and safe cases
    assert is_reserved_env_var('JUPYTERHUB_API_TOKEN', reserved_names, reserved_prefixes)
    assert is_reserved_env_var('JPY_API_TOKEN', reserved_names, reserved_prefixes)
    assert is_reserved_env_var('JUPYTERLAB_TIMEZONE', reserved_names, reserved_prefixes)
    assert not is_reserved_env_var('MY_VAR', reserved_names, reserved_prefixes)
    assert is_reserved_env_var('', reserved_names, reserved_prefixes)

    # All configs used below - sorted by priority desc as the manager returns them
    all_configs = [
        {
            'group_name': 'high',
            'priority': 10,
            'config': {
                'env_vars': [
                    {'name': 'SHARED', 'value': 'high_wins'},
                    {'name': 'JUPYTERHUB_SECRET', 'value': 'nope'},  # reserved
                ],
                'gpu_access': False,
                'docker_access': True,
                'docker_privileged': False,
            },
        },
        {
            'group_name': 'gpu-only',
            'priority': 5,
            'config': {
                'env_vars': [{'name': 'SHARED', 'value': 'low_loses'}, {'name': 'EXTRA', 'value': 'ok'}],
                'gpu_access': True,
                'docker_access': False,
                'docker_privileged': True,
            },
        },
        {'group_name': 'unrelated', 'priority': 0, 'config': {'env_vars': [], 'gpu_access': True}},
    ]

    # User in no groups
    r = resolve_group_config([], all_configs, True, reserved_names, reserved_prefixes)
    assert r['env_vars'] == {}
    assert r['gpu_access'] is False
    assert r['docker_access'] is False
    assert r['matched_groups'] == []

    # User in both groups: grants OR-accumulate, env var from higher priority wins
    r = resolve_group_config(['high', 'gpu-only'], all_configs, True, reserved_names, reserved_prefixes)
    assert r['env_vars'] == {'SHARED': 'high_wins', 'EXTRA': 'ok'}
    assert r['gpu_access'] is True
    assert r['docker_access'] is True
    assert r['docker_privileged'] is True
    assert r['matched_groups'] == ['high', 'gpu-only']
    assert r['skipped_env_vars'] == ['JUPYTERHUB_SECRET']

    # GPU hardware unavailable blocks GPU grant even if a group has gpu_access
    r = resolve_group_config(['gpu-only'], all_configs, False, reserved_names, reserved_prefixes)
    assert r['gpu_access'] is False
    assert r['docker_privileged'] is True

    # Memory limit resolution
    mem_configs = [
        {'group_name': 'small',   'priority': 10, 'config': {'mem_limit_enabled': True,  'mem_limit_gb': 4}},
        {'group_name': 'big',     'priority': 5,  'config': {'mem_limit_enabled': True,  'mem_limit_gb': 8}},
        {'group_name': 'off',     'priority': 3,  'config': {'mem_limit_enabled': False, 'mem_limit_gb': 16}},
        {'group_name': 'enabled-zero', 'priority': 2, 'config': {'mem_limit_enabled': True, 'mem_limit_gb': 0}},
    ]
    # No group with memory -> None
    assert resolve_group_config([], mem_configs, True, reserved_names, reserved_prefixes)['mem_limit_gb'] is None
    # Single enabled group -> that value
    assert resolve_group_config(['small'], mem_configs, True, reserved_names, reserved_prefixes)['mem_limit_gb'] == 4.0
    # Two enabled groups -> biggest wins
    assert resolve_group_config(['small', 'big'], mem_configs, True, reserved_names, reserved_prefixes)['mem_limit_gb'] == 8.0
    # Disabled group does NOT un-cap - small (4 GB) stands even though 'off' has 16 GB but disabled
    assert resolve_group_config(['small', 'off'], mem_configs, True, reserved_names, reserved_prefixes)['mem_limit_gb'] == 4.0
    # enabled with value 0 -> ignored (no cap)
    assert resolve_group_config(['enabled-zero'], mem_configs, True, reserved_names, reserved_prefixes)['mem_limit_gb'] is None


def test_all_modules_importable():
    """Verify all package modules can be imported."""
    modules = [
        'stellars_hub',
        'stellars_hub.auth',
        'stellars_hub.branding',
        'stellars_hub.docker_utils',
        'stellars_hub.events',
        'stellars_hub.gpu',
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
        'stellars_hub.handlers.groups',
        'stellars_hub.groups_config',
        'stellars_hub.group_resolver',
    ]
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Failed to import {mod_name}"
