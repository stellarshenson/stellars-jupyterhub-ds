"""Apply-side regression guard for the policy models (the controller layer).

Each model's ``apply`` was moved verbatim out of the old monolithic
``pre_spawn_hook``. A ``FakeSpawner`` captures the exact spawner mutations each
model makes for representative resolved configs - the proof that the move is
behaviour-preserving on the critical spawn path. IO-heavy applies (docker-proxy
register, api-keys assign, downloads CHP routes) drive their existing seams via
small fakes / monkeypatch.
"""

import asyncio

import pytest

from duoptimum_hub_services.policy import POLICY_TYPES, ApplyContext, apply_policies

_BY_KEY = {p.key: p for p in POLICY_TYPES}
_UNSET = object()


class _Log:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass
    def error(self, *a, **k): pass
    def exception(self, *a, **k): pass


class FakeSpawner:
    def __init__(self):
        self.volumes = {}
        self.environment = {}
        self.extra_host_config = {}
        self.extra_create_kwargs = {}
        self.mem_limit = _UNSET
        self.cpu_limit = _UNSET
        self.log = _Log()


def _actx(**kw):
    return ApplyContext(app=kw.pop('app', None), username=kw.pop('username', 'alice'), **kw)


def _apply(key, resolved, actx=None, spawner=None):
    spawner = spawner or FakeSpawner()
    asyncio.run(_BY_KEY[key].apply(spawner, resolved, actx or _actx()))
    return spawner


# ── env_vars ─────────────────────────────────────────────────────────────────

class TestEnvVarsApply:
    def test_sets_env(self):
        s = _apply('env_vars', {'env_vars': {'FOO': 'bar', 'X': '1'}})
        assert s.environment == {'FOO': 'bar', 'X': '1'}

    def test_empty_noop(self):
        s = _apply('env_vars', {'env_vars': {}})
        assert s.environment == {}


# ── gpu ──────────────────────────────────────────────────────────────────────

class TestGpuApply:
    def test_all(self):
        s = _apply('gpu', {'gpu_access': True, 'gpu_all': True, 'gpu_device_ids': []})
        assert s.extra_host_config['device_requests'] == [
            {'Driver': 'nvidia', 'Count': -1, 'Capabilities': [['gpu']]}]
        assert s.environment['NVIDIA_VISIBLE_DEVICES'] == 'all'
        assert 'CUDA_VISIBLE_DEVICES' not in s.environment
        assert s.environment['ENABLE_GPU_SUPPORT'] == '1'
        assert s.environment['ENABLE_GPUSTAT'] == '1'

    def test_specific_with_uuid_map(self):
        s = _apply('gpu', {'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': ['0', '2']},
                   actx=_actx(gpu_uuid_by_index={'0': 'UUID0', '2': 'UUID2'}))
        assert s.extra_host_config['device_requests'] == [
            {'Driver': 'nvidia', 'DeviceIDs': ['0', '2'], 'Capabilities': [['gpu']]}]
        assert s.environment['NVIDIA_VISIBLE_DEVICES'] == '0,2'
        assert s.environment['CUDA_VISIBLE_DEVICES'] == 'UUID0,UUID2'

    def test_specific_no_uuid_map_falls_back_to_indices(self):
        s = _apply('gpu', {'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': ['1']})
        assert s.environment['CUDA_VISIBLE_DEVICES'] == '1'

    def test_none_disables(self):
        s = _apply('gpu', {'gpu_access': False, 'gpu_all': True, 'gpu_device_ids': []})
        assert 'device_requests' not in s.extra_host_config
        assert s.environment['NVIDIA_VISIBLE_DEVICES'] == 'void'
        assert s.environment['ENABLE_GPU_SUPPORT'] == '0'
        assert s.environment['ENABLE_GPUSTAT'] == '0'

    def test_delegates_to_vendor_provider(self):
        # the stage uses the provider's device request + visibility env, not a
        # hardcoded nvidia shape - proves the seam is live, not a fallback.
        class _FakeVendor:
            def runtime_name(self): return 'fakert'
            def device_request(self, all_gpus, ids):
                return {'Driver': 'fake', 'all': all_gpus, 'ids': list(ids)}
            def visibility_env(self, access, all_gpus, ids, uuid_map):
                return {'FAKE_VISIBLE': 'yes' if access else 'no'}
        s = _apply('gpu', {'gpu_access': True, 'gpu_all': True, 'gpu_device_ids': []},
                   actx=_actx(gpu_vendor=_FakeVendor()))
        assert s.extra_host_config['device_requests'] == [{'Driver': 'fake', 'all': True, 'ids': []}]
        assert s.environment['FAKE_VISIBLE'] == 'yes'
        assert 'NVIDIA_VISIBLE_DEVICES' not in s.environment  # provider chose its own naming
        assert s.environment['ENABLE_GPU_SUPPORT'] == '1'  # image-generic flags stay caller-side

    def test_provider_none_value_pops_preexisting_env(self):
        # the all-case provider returns CUDA_VISIBLE_DEVICES=None -> the stage must
        # UNSET a stale value, not leave it.
        s = FakeSpawner()
        s.environment['CUDA_VISIBLE_DEVICES'] = 'stale'
        _apply('gpu', {'gpu_access': True, 'gpu_all': True, 'gpu_device_ids': []}, spawner=s)
        assert 'CUDA_VISIBLE_DEVICES' not in s.environment


# ── docker ───────────────────────────────────────────────────────────────────

def _docker_resolved(**over):
    base = {'docker_access': False, 'docker_limited': False, 'docker_privileged': False}
    base.update(over)
    return base


class TestDockerApply:
    def test_raw_socket(self):
        s = _apply('docker', _docker_resolved(docker_access=True))
        assert s.volumes['/var/run/docker.sock'] == '/var/run/docker.sock'
        assert 'DOCKER_HOST' not in s.environment

    def test_none_pops_socket(self):
        s = FakeSpawner()
        s.volumes['/var/run/docker.sock'] = '/var/run/docker.sock'
        s.environment['DOCKER_HOST'] = 'unix://x'
        _apply('docker', _docker_resolved(), spawner=s)
        assert '/var/run/docker.sock' not in s.volumes
        assert 'DOCKER_HOST' not in s.environment

    def test_privileged(self):
        s = _apply('docker', _docker_resolved(docker_privileged=True))
        assert s.extra_host_config['privileged'] is True

    def test_not_privileged_pops(self):
        s = FakeSpawner()
        s.extra_host_config['privileged'] = True
        _apply('docker', _docker_resolved(), spawner=s)
        assert 'privileged' not in s.extra_host_config

    def test_limited_without_proxy_config_raises(self):
        with pytest.raises(RuntimeError):
            _apply('docker', _docker_resolved(docker_limited=True))

    def test_limited_registers_and_mounts(self, monkeypatch):
        async def fake_register_user(username, resolved, **kw):
            return ('/host/sock', '/run/dockersock', 'unix:///run/dockersock/docker.sock')
        monkeypatch.setattr('duoptimum_hub_services.docker_proxy.register_user', fake_register_user)
        actx = _actx(docker_proxy_socket_dir='/sock', docker_proxy_volume_name='vol')
        s = _apply('docker', _docker_resolved(docker_limited=True), actx=actx)
        assert s.environment['DOCKER_HOST'] == 'unix:///run/dockersock/docker.sock'
        mounts = s.extra_host_config['mounts']
        assert mounts[0]['Source'] == 'vol' and mounts[0]['VolumeOptions'] == {'Subpath': 'alice'}

    def test_limited_second_spawn_no_duplicate_mount(self, monkeypatch):
        # spawner objects persist for the hub's lifetime; a 2nd apply on the same
        # spawner must not append a 2nd identical proxy mount - dockerd rejects
        # "Duplicate mount point" and the user is locked out of every later spawn.
        async def fake_register_user(username, resolved, **kw):
            return ('/host/sock', '/run/dockersock', 'unix:///run/dockersock/docker.sock')
        monkeypatch.setattr('duoptimum_hub_services.docker_proxy.register_user', fake_register_user)
        actx = _actx(docker_proxy_socket_dir='/sock', docker_proxy_volume_name='vol')
        s = _apply('docker', _docker_resolved(docker_limited=True), actx=actx)
        _apply('docker', _docker_resolved(docker_limited=True), actx=actx, spawner=s)
        assert len(s.extra_host_config['mounts']) == 1

    def test_leaving_limited_docker_removes_stale_mount(self, monkeypatch):
        # a user dropped from the limited-docker group must not keep the proxy
        # mount on their next (non-docker) spawn - the cleanup at apply() top removes it.
        async def fake_register_user(username, resolved, **kw):
            return ('/host/sock', '/run/dockersock', 'unix:///run/dockersock/docker.sock')
        monkeypatch.setattr('duoptimum_hub_services.docker_proxy.register_user', fake_register_user)
        actx = _actx(docker_proxy_socket_dir='/sock', docker_proxy_volume_name='vol')
        s = _apply('docker', _docker_resolved(docker_limited=True), actx=actx)
        _apply('docker', _docker_resolved(), actx=actx, spawner=s)
        assert not s.extra_host_config.get('mounts')
        assert 'DOCKER_HOST' not in s.environment


# ── mem / cpu ─────────────────────────────────────────────────────────────────

class TestMemApply:
    def test_limit_with_swap_disabled(self):
        s = _apply('mem', {'mem_limit_gb': 8, 'mem_swap_disabled': True})
        assert s.mem_limit == 8 * 1024 ** 3
        assert s.extra_host_config['memswap_limit'] == 8 * 1024 ** 3

    def test_limit_swap_allowed(self):
        s = _apply('mem', {'mem_limit_gb': 4, 'mem_swap_disabled': False})
        assert s.mem_limit == 4 * 1024 ** 3
        assert 'memswap_limit' not in s.extra_host_config

    def test_none(self):
        s = _apply('mem', {'mem_limit_gb': None})
        assert s.mem_limit is None


class TestCpuApply:
    def test_ceil_to_whole(self):
        s = _apply('cpu', {'cpu_limit_cores': 2.5})
        assert s.cpu_limit == 3.0

    def test_min_one(self):
        s = _apply('cpu', {'cpu_limit_cores': 0.3})
        assert s.cpu_limit == 1.0

    def test_none(self):
        s = _apply('cpu', {'cpu_limit_cores': None})
        assert s.cpu_limit is None


# ── sudo ───────────────────────────────────────────────────────────────────────

class TestSudoApply:
    def test_group_on(self):
        s = _apply('sudo', {'sudo_enable': True})
        assert s.environment['JUPYTERLAB_SUDO_ENABLE'] == '1'

    def test_group_off(self):
        s = _apply('sudo', {'sudo_enable': False})
        assert s.environment['JUPYTERLAB_SUDO_ENABLE'] == '0'

    def test_unconfigured_uses_default_on(self):
        s = _apply('sudo', {'sudo_enable': None}, actx=_actx(lab_sudo_enable_default=1))
        assert s.environment['JUPYTERLAB_SUDO_ENABLE'] == '1'

    def test_unconfigured_uses_default_off(self):
        s = _apply('sudo', {'sudo_enable': None}, actx=_actx(lab_sudo_enable_default=0))
        assert s.environment['JUPYTERLAB_SUDO_ENABLE'] == '0'


# ── volume_mounts ──────────────────────────────────────────────────────────────

class TestVolumeMountsApply:
    def test_mounts_and_tracks(self):
        s = _apply('volume_mounts', {'volume_mounts': [{'volume': 'data', 'mountpoint': '/mnt/data', 'mode': 'rw'}],
                                     'skipped_volume_mounts': []})
        assert s.volumes == {'data': '/mnt/data'}  # rw keeps the bare-string form
        assert s._stellars_group_volume_keys == ['data']

    def test_read_only_uses_bind_mode_form(self):
        s = _apply('volume_mounts', {'volume_mounts': [{'volume': 'data', 'mountpoint': '/mnt/data', 'mode': 'ro'}],
                                     'skipped_volume_mounts': []})
        assert s.volumes == {'data': {'bind': '/mnt/data', 'mode': 'ro'}}

    def test_unmounts_on_leave(self):
        s = _apply('volume_mounts', {'volume_mounts': [{'volume': 'data', 'mountpoint': '/mnt/data', 'mode': 'rw'}],
                                     'skipped_volume_mounts': []})
        # next spawn: group removed -> previously-added volume is popped
        _apply('volume_mounts', {'volume_mounts': [], 'skipped_volume_mounts': []}, spawner=s)
        assert s.volumes == {}
        assert s._stellars_group_volume_keys == []

    def test_shared_mount_resolves_name_by_label(self):
        # the standard shared mount carries no saved name; apply mounts the
        # label-resolved volume (actx.shared_volume_name) at /mnt/shared
        s = _apply('volume_mounts',
                   {'shared_mount': {'allow': True, 'mode': 'rw'}, 'volume_mounts': [], 'skipped_volume_mounts': []},
                   actx=_actx(shared_volume_name='hub_shared_resolved'))
        assert s.volumes == {'hub_shared_resolved': '/mnt/shared'}
        assert s._stellars_group_volume_keys == ['hub_shared_resolved']

    def test_shared_mount_read_only(self):
        s = _apply('volume_mounts',
                   {'shared_mount': {'allow': True, 'mode': 'ro'}, 'volume_mounts': [], 'skipped_volume_mounts': []},
                   actx=_actx(shared_volume_name='hub_shared_resolved'))
        assert s.volumes == {'hub_shared_resolved': {'bind': '/mnt/shared', 'mode': 'ro'}}

    def test_shared_mount_skipped_when_no_volume_resolved(self):
        # shared allowed but no role=shared volume exists -> skipped, never invented
        s = _apply('volume_mounts',
                   {'shared_mount': {'allow': True, 'mode': 'rw'}, 'volume_mounts': [], 'skipped_volume_mounts': []},
                   actx=_actx(shared_volume_name=''))
        assert s.volumes == {}
        assert s._stellars_group_volume_keys == []

    def test_custom_reusing_shared_name_cannot_clobber_or_bypass_ro(self):
        # spawner.volumes is keyed by volume NAME: a custom row reusing the resolved
        # shared volume name must NOT overwrite the ro /mnt/shared mount with an rw one
        s = _apply('volume_mounts',
                   {'shared_mount': {'allow': True, 'mode': 'ro'},
                    'volume_mounts': [{'volume': 'hub_shared_resolved', 'mountpoint': '/mnt/data', 'mode': 'rw'}],
                    'skipped_volume_mounts': []},
                   actx=_actx(shared_volume_name='hub_shared_resolved'))
        # the shared ro mount survives; the colliding custom row is skipped
        assert s.volumes == {'hub_shared_resolved': {'bind': '/mnt/shared', 'mode': 'ro'}}
        assert s._stellars_group_volume_keys == ['hub_shared_resolved']


# ── downloads (fake app + proxy) ───────────────────────────────────────────────

class _FakeProxy:
    def __init__(self):
        self.extra_routes = {}
        self.added = []
        self.deleted = []

    def validate_routespec(self, spec):
        return spec if spec.endswith('/') else spec + '/'

    async def add_route(self, spec, target, data):
        self.added.append(spec)

    async def delete_route(self, spec):
        self.deleted.append(spec)


class _FakeHub:
    url = 'http://hub:8081/jupyterhub/hub/'


class _FakeApp:
    base_url = '/jupyterhub/'

    def __init__(self):
        self.hub = _FakeHub()
        self.proxy = _FakeProxy()
        self.log = _Log()
        self._downloads_handlers_injected = True  # skip Tornado handler injection


class TestDownloadsApply:
    def test_blocked_registers_four_routes(self):
        app = _FakeApp()
        actx = _actx(app=app, username='bob', block_file_downloads=1)
        _apply('downloads', {'downloads_allow': None}, actx=actx)  # default blocks
        assert len(app.proxy.added) == 4
        assert all('/user/bob/' in r for r in app.proxy.added)
        assert len(app.proxy.extra_routes) == 4

    def test_group_block_overrides_allow_default(self):
        app = _FakeApp()
        actx = _actx(app=app, username='bob', block_file_downloads=0)
        _apply('downloads', {'downloads_allow': False}, actx=actx)
        assert len(app.proxy.added) == 4

    def test_allowed_unregisters(self):
        app = _FakeApp()
        actx = _actx(app=app, username='bob', block_file_downloads=1)
        _apply('downloads', {'downloads_allow': True}, actx=actx)  # group allows -> clear
        assert app.proxy.added == []
        assert len(app.proxy.deleted) == 4

    def test_dormant_when_default_allow_and_unconfigured(self):
        app = _FakeApp()
        actx = _actx(app=app, username='bob', block_file_downloads=0)
        _apply('downloads', {'downloads_allow': None}, actx=actx)
        assert app.proxy.added == [] and app.proxy.deleted == []


# ── api_keys (stubbed observer, like test_api_keys_pool) ───────────────────────

class TestApiKeysApply:
    def test_assigns_env_and_label(self, monkeypatch):
        from duoptimum_hub_services import api_keys_pool as akp
        from duoptimum_hub_services.api_keys_pool import PoolManager, normalize_pool, pool_label_key
        PoolManager._instance = None
        monkeypatch.setattr(akp, 'observe_in_use', _empty_observe)
        monkeypatch.setattr(akp, '_container_name', lambda u: f'jupyterlab-{u}')

        pool = normalize_pool({'enabled': True, 'mode': 'single', 'env_var_key': 'API_KEY',
                               'credentials': [{'slot': 's0', 'key': 'k-secret'}]})
        pool['pool_id'] = 'p'
        resolved = {'api_key_pools': [pool], 'env_vars': {}, 'env_var_source': {}}
        s = _apply('api_keys', resolved)
        assert s.environment['API_KEY'] == 'k-secret'
        assert s.extra_create_kwargs['labels'][pool_label_key('p')] == 's0'
        PoolManager._instance = None

    def test_group_env_var_wins_over_pool(self, monkeypatch):
        from duoptimum_hub_services import api_keys_pool as akp
        from duoptimum_hub_services.api_keys_pool import PoolManager, normalize_pool
        PoolManager._instance = None
        monkeypatch.setattr(akp, 'observe_in_use', _empty_observe)
        monkeypatch.setattr(akp, '_container_name', lambda u: f'jupyterlab-{u}')

        pool = normalize_pool({'enabled': True, 'mode': 'single', 'env_var_key': 'SHARED',
                               'credentials': [{'slot': 's0', 'key': 'pool-val'}]})
        pool['pool_id'] = 'p'
        pool['group_index'] = 1
        # higher-priority group env var (index 0) already set this name
        resolved = {'api_key_pools': [pool], 'env_vars': {'SHARED': 'group-val'},
                    'env_var_source': {'SHARED': 0}}
        s = FakeSpawner()
        s.environment['SHARED'] = 'group-val'
        _apply('api_keys', resolved, spawner=s)
        assert s.environment['SHARED'] == 'group-val'  # plain env var wins on tie/precedence
        PoolManager._instance = None


async def _empty_observe():
    return {}, {}


# ── full loop ───────────────────────────────────────────────────────────────

def test_apply_policies_loop_runs_all_benign():
    """apply_policies wires every model; a benign resolved (no docker-limited /
    api-keys / downloads IO) mutates the spawner without errors."""
    resolved = {
        'env_vars': {'A': '1'}, 'env_var_source': {},
        'gpu_access': False, 'gpu_all': True, 'gpu_device_ids': [],
        'docker_access': False, 'docker_limited': False, 'docker_privileged': False,
        'mem_limit_gb': 16, 'mem_swap_disabled': True,
        'cpu_limit_cores': 4, 'sudo_enable': False,
        'downloads_allow': None, 'api_key_pools': [],
        'volume_mounts': [], 'skipped_volume_mounts': [],
    }
    s = FakeSpawner()
    asyncio.run(apply_policies(s, resolved, _actx(block_file_downloads=0)))
    assert s.environment['A'] == '1'
    assert s.environment['JUPYTERLAB_SUDO_ENABLE'] == '0'
    assert s.environment['NVIDIA_VISIBLE_DEVICES'] == 'void'
    assert s.mem_limit == 16 * 1024 ** 3
    assert s.cpu_limit == 4.0
