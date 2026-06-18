"""Set-rule tests: each type's coerce normalises or rejects an admin write.

Coerce replaces the legacy per-field branches in ``GroupsConfigHandler.put``.
``coerce_config`` loops the registry; a reserved-name write raises a structured
``PolicyCoerceError`` (the stable reserved_env_var_names JSON), a malformed shape
raises a plain one (bare 400).
"""

import pytest

from duoptimum_hub_services.policy import (
    PolicyCoerceError,
    PolicyCtx,
    coerce_config,
)


def _ctx(reserved_names=frozenset(), reserved_prefixes=()):
    return PolicyCtx(reserved_names=reserved_names, reserved_prefixes=reserved_prefixes)


def _coerce(body, existing=None, **ctx):
    return coerce_config(body, existing or {}, _ctx(**ctx))


class TestEnvVarsCoerce:
    def test_accepts_list_and_active_flag(self):
        out = _coerce({'env_vars': [{'name': 'A', 'value': '1'}], 'env_vars_active': 1})
        assert out['env_vars'] == [{'name': 'A', 'value': '1'}]
        assert out['env_vars_active'] is True

    def test_non_list_raises_plain(self):
        with pytest.raises(PolicyCoerceError) as e:
            _coerce({'env_vars': 'nope'})
        assert e.value.structured is False

    def test_missing_name_raises_plain(self):
        with pytest.raises(PolicyCoerceError):
            _coerce({'env_vars': [{'value': 'x'}]})

    def test_reserved_name_raises_structured(self):
        with pytest.raises(PolicyCoerceError) as e:
            _coerce({'env_vars': [{'name': 'PATH', 'value': 'x'},
                                  {'name': 'JUPYTERHUB_X', 'value': 'y'}]},
                    reserved_names=frozenset({'PATH'}), reserved_prefixes=('JUPYTERHUB_',))
        assert e.value.structured is True
        assert e.value.code == 'reserved_env_var_names'
        assert e.value.extra['rejected'] == ['JUPYTERHUB_X', 'PATH']

    def test_absent_key_not_emitted(self):
        assert 'env_vars' not in _coerce({'env_vars_active': True})


class TestGpuCoerce:
    def test_bools_and_id_stringification(self):
        out = _coerce({'gpu_access': 1, 'gpu_all': 0, 'gpu_device_ids': [0, 2]})
        assert out['gpu_access'] is True and out['gpu_all'] is False
        assert out['gpu_device_ids'] == ['0', '2']

    def test_non_list_ids_raises(self):
        with pytest.raises(PolicyCoerceError):
            _coerce({'gpu_device_ids': '0,2'})


class TestDockerCoerce:
    def test_int_quota_clamped_nonnegative(self):
        out = _coerce({'docker_limited_max_containers': -5})
        assert out['docker_limited_max_containers'] == 0

    def test_garbage_int_becomes_zero(self):
        assert _coerce({'docker_limited_max_volumes': 'abc'})['docker_limited_max_volumes'] == 0

    def test_float_quota_rounded(self):
        assert _coerce({'docker_limited_mem_cap_gb': 7.26})['docker_limited_mem_cap_gb'] == 7.3

    def test_flags_bool(self):
        out = _coerce({'docker_active': 1, 'docker_access': 0,
                       'docker_limited_hub_network_access': 0})
        assert out['docker_active'] is True and out['docker_access'] is False
        assert out['docker_limited_hub_network_access'] is False


class TestMemCpuCoerce:
    def test_mem_clamp_and_round(self):
        out = _coerce({'mem_limit_enabled': 1, 'mem_limit_gb': -3.14})
        assert out['mem_limit_enabled'] is True and out['mem_limit_gb'] == 0.0

    def test_cpu_round(self):
        assert _coerce({'cpu_limit_cores': 2.55})['cpu_limit_cores'] == 2.5

    def test_cpu_garbage_zero(self):
        assert _coerce({'cpu_limit_cores': 'lots'})['cpu_limit_cores'] == 0.0


class TestSudoDownloadsCoerce:
    def test_sudo(self):
        out = _coerce({'sudo_active': 1, 'sudo_enable': 0})
        assert out['sudo_active'] is True and out['sudo_enable'] is False

    def test_downloads(self):
        out = _coerce({'downloads_active': 1, 'downloads_allow': 0})
        assert out['downloads_active'] is True and out['downloads_allow'] is False


class TestApiKeysCoerce:
    def test_non_dict_raises(self):
        with pytest.raises(PolicyCoerceError):
            _coerce({'api_keys_pool': []})

    def test_reserved_target_raises_structured_when_enabled(self):
        with pytest.raises(PolicyCoerceError) as e:
            _coerce({'api_keys_pool': {'enabled': True, 'mode': 'single', 'env_var_key': 'PATH'}},
                    reserved_names=frozenset({'PATH'}))
        assert e.value.structured and e.value.code == 'reserved_env_var_names'

    def test_reserved_target_ignored_when_disabled(self):
        out = _coerce({'api_keys_pool': {'enabled': False, 'mode': 'single', 'env_var_key': 'PATH'}},
                      reserved_names=frozenset({'PATH'}))
        assert out['api_keys_pool']['enabled'] is False

    def test_existing_slot_preserved(self):
        existing = {'api_keys_pool': {'mode': 'single', 'credentials': [
            {'slot': 'keep', 'key': 'k1'}]}}
        out = _coerce({'api_keys_pool': {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                                         'credentials': [{'slot': 'keep', 'key': 'k1'}]}},
                      existing=existing)
        assert out['api_keys_pool']['credentials'][0]['slot'] == 'keep'


class TestVolumeMountsCoerce:
    def test_non_list_raises(self):
        with pytest.raises(PolicyCoerceError):
            _coerce({'volume_mounts': 'x'})

    def test_strips_and_normalises(self):
        out = _coerce({'volume_mounts': [{'volume': ' v ', 'mountpoint': ' /mnt/x '}]})
        assert out['volume_mounts'] == [{'volume': 'v', 'mountpoint': '/mnt/x'}]


def test_coerce_config_only_emits_present_keys():
    out = coerce_config({'sudo_active': True}, {}, _ctx())
    assert out == {'sudo_active': True}
