"""Import tests for duoptimum_hub_services package.

Verifies that all modules and public API can be imported without errors.
Runs during Docker build (builder stage) to catch packaging issues early.
"""

import importlib


def test_package_has_version():
    from duoptimum_hub_services import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_top_level_imports():
    from duoptimum_hub_services import StellarsNativeAuthenticator
    from duoptimum_hub_services import setup_branding
    from duoptimum_hub_services import register_events
    from duoptimum_hub_services import resolve_gpu_mode
    from duoptimum_hub_services import ensure_gpuinfo_sidecar
    from duoptimum_hub_services import stop_gpuinfo_sidecar
    from duoptimum_hub_services import make_pre_spawn_hook
    from duoptimum_hub_services import schedule_policy_startup
    from duoptimum_hub_services import schedule_startup_favicon_callback
    from duoptimum_hub_services import get_services_and_roles
    from duoptimum_hub_services import get_user_volume_suffixes
    from duoptimum_hub_services import apply_abuse_protection
    from duoptimum_hub_services import build_app_protection
    from duoptimum_hub_services import ratelimit_disabled
    assert callable(get_user_volume_suffixes)
    assert callable(apply_abuse_protection)
    assert callable(resolve_gpu_mode)
    assert callable(ensure_gpuinfo_sidecar)
    assert callable(stop_gpuinfo_sidecar)


def test_volumes():
    from duoptimum_hub_services.volumes import get_user_volume_suffixes
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
    from duoptimum_hub_services.password_cache import cache_password, get_cached_password, clear_cached_password
    cache_password("testuser", "testpass")
    assert get_cached_password("testuser") == "testpass"
    clear_cached_password("testuser")
    assert get_cached_password("testuser") is None


def test_docker_utils():
    from duoptimum_hub_services.docker_utils import encode_username_for_docker, stats_from_container
    assert encode_username_for_docker("test.user") == "test-2euser"
    assert encode_username_for_docker("simple") == "simple"
    assert callable(stats_from_container)


def test_container_stats_cache():
    from duoptimum_hub_services.container_stats_cache import get_container_stats_with_refresh
    assert callable(get_container_stats_with_refresh)


def test_persisted_cache(tmp_path, monkeypatch):
    from duoptimum_hub_services import persisted_cache as pc
    monkeypatch.setenv("JUPYTERHUB_DATA_DIR", str(tmp_path))

    # fresh round-trip seeds
    sample = {"alice": {"total": 12.3}}
    pc.save_cached("widget", sample)
    loaded = pc.load_cached("widget")
    assert loaded is not None and loaded[0] == sample

    # >TTL is ignored (set TTL to 0 minutes -> any age is stale)
    monkeypatch.setenv("JUPYTERHUB_CACHED_DATA_TTL_MINUTES", "0")
    assert pc.load_cached("widget") is None

    # missing + corrupt return None, never raise
    assert pc.load_cached("never-written") is None
    (tmp_path / "broken.json").write_text("{not json")
    assert pc.load_cached("broken") is None


def test_activity_model():
    from duoptimum_hub_services.activity.model import ActivityBase, ActivitySample
    assert ActivitySample.__tablename__ == 'activity_samples'


def test_activity_monitor_class():
    from duoptimum_hub_services.activity.monitor import ActivityMonitor
    assert hasattr(ActivityMonitor, 'get_instance')
    assert hasattr(ActivityMonitor, 'record_sample')
    assert hasattr(ActivityMonitor, 'get_score')


def test_activity_helpers():
    from duoptimum_hub_services.activity.helpers import (
        calculate_activity_score,
        get_activity_sampling_status,
        get_inactive_after_seconds,
        rename_activity_user,
        delete_activity_user,
        initialize_activity_for_user,
        reset_all_activity_data,
        record_samples_for_all_users,
    )
    assert callable(calculate_activity_score)


def test_activity_service():
    from duoptimum_hub_services.activity.service import ActivitySamplerService, main
    assert callable(main)


def test_volume_cache():
    from duoptimum_hub_services.volume_cache import (
        VolumeSizeRefresher,
        get_cached_volume_sizes,
    )
    data, needs_refresh = get_cached_volume_sizes()
    assert isinstance(data, dict)
    assert needs_refresh is True  # No data cached yet


def test_gpu_cache():
    from duoptimum_hub_services.gpu_cache import (
        GpuUtilizationRefresher,
        configure_gpu_cache,
        get_gpu_utilization_with_refresh,
    )
    configure_gpu_cache('http://gpuinfo-nvidia:8000')
    # No sidecar reachable in the test env -> sample fails gracefully, cache stays {}.
    data = get_gpu_utilization_with_refresh()
    assert isinstance(data, dict)
    assert GpuUtilizationRefresher.get_instance() is not None


def test_handlers():
    from duoptimum_hub_services.handlers import (
        ManageVolumesHandler,
        RestartServerHandler,
        LabReadyHandler,
        ActiveServersHandler,
        BroadcastNotificationHandler,
        GetUserCredentialsHandler,
        SettingsDataHandler,
        SessionInfoHandler,
        ExtendSessionHandler,
        ActivityDataHandler,
        ActivityResetHandler,
        ActivitySampleHandler,
        FaviconRedirectHandler,
        HealthCheckHandler,
        GroupsDataHandler,
        GroupsCreateHandler,
        GroupsDeleteHandler,
        GroupsConfigHandler,
        GroupsReorderHandler,
        NativeUsersHandler,
        NativeUserAuthorizationHandler,
        UserProfileHandler,
        UserProfilesListHandler,
        UserForcePasswordChangeHandler,
        UserRenameHandler,
        UserDisplayPreferencesHandler,
        EffectiveGrantsHandler,
        ServerLogsHandler,
        EventsDataHandler,
        SentNotificationsDataHandler,
    )
    # Verify handler count matches expected (legacy server-rendered page handlers
    # removed - the React portal owns those routes)
    from duoptimum_hub_services import handlers
    assert len(handlers.__all__) == 30


def test_auth():
    from duoptimum_hub_services.auth import StellarsNativeAuthenticator, CustomAuthorizationAreaHandler
    assert hasattr(StellarsNativeAuthenticator, 'get_handlers')


def test_events():
    from duoptimum_hub_services.events import register_events
    assert callable(register_events)


def test_gpu():
    from duoptimum_hub_services.gpu import enumerate_gpus, resolve_gpu_mode
    assert callable(enumerate_gpus)
    assert callable(resolve_gpu_mode)


def test_branding():
    from duoptimum_hub_services.branding import setup_branding
    result = setup_branding()
    assert isinstance(result, dict)
    assert 'logo_file' in result
    assert 'favicon_uri' in result


def test_hooks():
    import asyncio
    import logging
    import types

    from duoptimum_hub_services.hooks import (
        make_pre_spawn_hook,
        schedule_policy_startup,
        schedule_startup_favicon_callback,
    )
    assert callable(schedule_policy_startup)
    assert callable(schedule_startup_favicon_callback)
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
    from duoptimum_hub_services.services import get_services_and_roles
    services, roles = get_services_and_roles(sample_interval=600)
    assert isinstance(services, list)
    assert isinstance(roles, list)
    assert len(services) >= 1  # At least activity-sampler


def test_groups_config():
    from duoptimum_hub_services.groups_config import GroupsConfigBase, GroupConfig, GroupsConfigManager, validate_group_name
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
    from duoptimum_hub_services.policy import resolve_policies as resolve_group_config
    from duoptimum_hub_services.policy import is_reserved_env_var

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
        'duoptimum_hub_services',
        'duoptimum_hub_services.auth',
        'duoptimum_hub_services.branding',
        'duoptimum_hub_services.docker_utils',
        'duoptimum_hub_services.events',
        'duoptimum_hub_services.gpu',
        'duoptimum_hub_services.hooks',
        'duoptimum_hub_services.password_cache',
        'duoptimum_hub_services.services',
        'duoptimum_hub_services.volume_cache',
        'duoptimum_hub_services.gpu_cache',
        'duoptimum_hub_services.volumes',
        'duoptimum_hub_services.activity',
        'duoptimum_hub_services.activity.model',
        'duoptimum_hub_services.activity.monitor',
        'duoptimum_hub_services.activity.helpers',
        'duoptimum_hub_services.activity.service',
        'duoptimum_hub_services.handlers',
        'duoptimum_hub_services.handlers.activity',
        'duoptimum_hub_services.handlers.credentials',
        'duoptimum_hub_services.handlers.favicon',
        'duoptimum_hub_services.handlers.notifications',
        'duoptimum_hub_services.handlers.server',
        'duoptimum_hub_services.handlers.session',
        'duoptimum_hub_services.handlers.settings',
        'duoptimum_hub_services.handlers.volumes',
        'duoptimum_hub_services.handlers.groups',
        'duoptimum_hub_services.handlers.native_users',
        'duoptimum_hub_services.handlers.user_profile',
        'duoptimum_hub_services.handlers.events_data',
        'duoptimum_hub_services.groups_config',
        'duoptimum_hub_services.user_profiles',
        'duoptimum_hub_services.event_log',
        'duoptimum_hub_services.policy',
        'duoptimum_hub_services.policy.registry',
        'duoptimum_hub_services.policy.engine',
    ]
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Failed to import {mod_name}"
