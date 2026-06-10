"""Tests for GroupConfigValidator - per-field coherence checks."""

from stellars_hub_services.groups_config import GroupConfigValidator


class TestValidateGpu:
    def test_no_grant_is_valid(self):
        assert GroupConfigValidator.validate_gpu({'gpu_access': False})[0] is True

    def test_all_gpus_is_valid(self):
        assert GroupConfigValidator.validate_gpu({'gpu_access': True, 'gpu_all': True})[0] is True

    def test_specific_ids_is_valid(self):
        c = {'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': ['0', '2']}
        assert GroupConfigValidator.validate_gpu(c)[0] is True

    def test_not_all_and_no_ids_is_invalid(self):
        c = {'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': []}
        valid, msg = GroupConfigValidator.validate_gpu(c)
        assert valid is False and 'GPU' in msg


class TestValidateDocker:
    def test_no_grant_is_valid(self):
        assert GroupConfigValidator.validate_docker({})[0] is True

    def test_normal_only_is_valid(self):
        assert GroupConfigValidator.validate_docker({'docker_access': True})[0] is True

    def test_limited_only_is_valid(self):
        assert GroupConfigValidator.validate_docker({'docker_limited': True})[0] is True

    def test_normal_plus_limited_is_invalid(self):
        valid, msg = GroupConfigValidator.validate_docker(
            {'docker_access': True, 'docker_limited': True}
        )
        assert valid is False and 'normal' in msg.lower() and 'limited' in msg.lower()

    def test_negative_quota_is_invalid(self):
        c = {'docker_limited': True, 'docker_limited_max_containers': -1}
        valid, msg = GroupConfigValidator.validate_docker(c)
        assert valid is False and 'max_containers' in msg

    def test_non_numeric_quota_is_invalid(self):
        c = {'docker_limited': True, 'docker_limited_max_volumes': 'abc'}
        valid, msg = GroupConfigValidator.validate_docker(c)
        assert valid is False and 'number' in msg.lower()

    def test_quota_zero_is_allowed(self):
        # Zero means "no quota" downstream (translates to default in resolver).
        c = {'docker_limited': True, 'docker_limited_max_storage_gb': 0}
        assert GroupConfigValidator.validate_docker(c)[0] is True


class TestValidateCpu:
    def test_disabled_is_valid_regardless(self):
        # When the toggle is off, even bogus values pass.
        c = {'cpu_limit_enabled': False, 'cpu_limit_cores': 0}
        assert GroupConfigValidator.validate_cpu(c)[0] is True

    def test_enabled_with_positive_value_is_valid(self):
        c = {'cpu_limit_enabled': True, 'cpu_limit_cores': 4}
        assert GroupConfigValidator.validate_cpu(c)[0] is True

    def test_enabled_with_zero_is_invalid(self):
        c = {'cpu_limit_enabled': True, 'cpu_limit_cores': 0}
        valid, msg = GroupConfigValidator.validate_cpu(c)
        assert valid is False and 'CPU' in msg

    def test_enabled_with_negative_is_invalid(self):
        c = {'cpu_limit_enabled': True, 'cpu_limit_cores': -1}
        assert GroupConfigValidator.validate_cpu(c)[0] is False

    def test_enabled_with_garbage_is_invalid(self):
        c = {'cpu_limit_enabled': True, 'cpu_limit_cores': 'lots'}
        valid, msg = GroupConfigValidator.validate_cpu(c)
        assert valid is False and 'number' in msg.lower()


class TestValidateMem:
    def test_disabled_is_valid_regardless(self):
        c = {'mem_limit_enabled': False, 'mem_limit_gb': 0}
        assert GroupConfigValidator.validate_mem(c)[0] is True

    def test_enabled_with_positive_value_is_valid(self):
        c = {'mem_limit_enabled': True, 'mem_limit_gb': 16}
        assert GroupConfigValidator.validate_mem(c)[0] is True

    def test_enabled_with_zero_is_invalid(self):
        c = {'mem_limit_enabled': True, 'mem_limit_gb': 0}
        valid, msg = GroupConfigValidator.validate_mem(c)
        assert valid is False and 'Memory' in msg

    def test_enabled_with_garbage_is_invalid(self):
        c = {'mem_limit_enabled': True, 'mem_limit_gb': 'two gigs'}
        valid, msg = GroupConfigValidator.validate_mem(c)
        assert valid is False


class TestValidateAll:
    def test_clean_config_passes(self):
        c = {
            'gpu_access': True, 'gpu_all': True,
            'docker_limited': True,
            'docker_limited_max_containers': 10,
            'cpu_limit_enabled': True, 'cpu_limit_cores': 4,
            'mem_limit_enabled': True, 'mem_limit_gb': 16,
        }
        valid, code, msg = GroupConfigValidator.validate_all(c)
        assert valid is True and code == '' and msg == ''

    def test_first_failure_wins_gpu(self):
        c = {'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': []}
        valid, code, _ = GroupConfigValidator.validate_all(c)
        assert valid is False and code == 'invalid_gpu_selection'

    def test_first_failure_wins_docker_when_gpu_clean(self):
        c = {'docker_access': True, 'docker_limited': True}
        valid, code, _ = GroupConfigValidator.validate_all(c)
        assert valid is False and code == 'invalid_docker_selection'

    def test_cpu_error_code(self):
        c = {'cpu_limit_enabled': True, 'cpu_limit_cores': 0}
        valid, code, _ = GroupConfigValidator.validate_all(c)
        assert valid is False and code == 'invalid_cpu_limit'

    def test_mem_error_code(self):
        c = {'mem_limit_enabled': True, 'mem_limit_gb': 0}
        valid, code, _ = GroupConfigValidator.validate_all(c)
        assert valid is False and code == 'invalid_mem_limit'


class TestValidateApiKeysPool:
    def test_disabled_is_valid(self):
        assert GroupConfigValidator.validate_api_keys_pool({'api_keys_pool': {'enabled': False}})[0] is True

    def test_no_mode_is_invalid(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': ''}}
        valid, msg = GroupConfigValidator.validate_api_keys_pool(c)
        assert valid is False and 'mode' in msg.lower()

    def test_single_missing_var_is_invalid(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': 'single', 'env_var_key': ''}}
        valid, msg = GroupConfigValidator.validate_api_keys_pool(c)
        assert valid is False and 'api-key' in msg.lower()

    def test_pair_missing_var_is_invalid(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': 'pair', 'env_var_id': 'ID', 'env_var_secret': ''}}
        valid, msg = GroupConfigValidator.validate_api_keys_pool(c)
        assert valid is False and 'pair' in msg.lower()

    def test_pair_half_credential_is_invalid(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': 'pair', 'env_var_id': 'ID', 'env_var_secret': 'SEC',
                               'credentials': [{'slot': 's1', 'id': 'i1'}]}}
        valid, msg = GroupConfigValidator.validate_api_keys_pool(c)
        assert valid is False and 'secret' in msg.lower()

    def test_single_empty_credential_is_invalid(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                               'credentials': [{'slot': 's1', 'key': ''}]}}
        assert GroupConfigValidator.validate_api_keys_pool(c)[0] is False

    def test_valid_single_pool(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                               'credentials': [{'slot': 's1', 'key': 'k1'}]}}
        assert GroupConfigValidator.validate_api_keys_pool(c)[0] is True

    def test_error_code_via_validate_all(self):
        c = {'api_keys_pool': {'enabled': True, 'mode': ''}}
        valid, code, _ = GroupConfigValidator.validate_all(c)
        assert valid is False and code == 'invalid_api_keys_pool'


class TestValidateVolumeMounts:
    def _check(self, mounts):
        return GroupConfigValidator.validate_volume_mounts({'volume_mounts': mounts})

    def test_empty_list_is_valid(self):
        assert self._check([])[0] is True

    def test_valid_single_mount(self):
        assert self._check([{'volume': 'proj_shared', 'mountpoint': '/mnt/shared'}])[0] is True

    def test_valid_multi_mount(self):
        mounts = [
            {'volume': 'proj_shared', 'mountpoint': '/mnt/shared'},
            {'volume': 'datasets', 'mountpoint': '/data/sets'},
        ]
        assert self._check(mounts)[0] is True

    def test_missing_volume_name_is_invalid(self):
        valid, msg = self._check([{'volume': '', 'mountpoint': '/mnt/x'}])
        assert valid is False and 'both' in msg.lower()

    def test_missing_mountpoint_is_invalid(self):
        valid, msg = self._check([{'volume': 'v', 'mountpoint': ''}])
        assert valid is False and 'both' in msg.lower()

    def test_relative_mountpoint_is_invalid(self):
        valid, msg = self._check([{'volume': 'v', 'mountpoint': 'mnt/x'}])
        assert valid is False and 'absolute' in msg.lower()

    def test_bad_volume_name_chars_invalid(self):
        valid, msg = self._check([{'volume': 'bad name!', 'mountpoint': '/mnt/x'}])
        assert valid is False and 'volume name' in msg.lower()

    def test_volume_name_cannot_start_with_dash(self):
        assert self._check([{'volume': '-v', 'mountpoint': '/mnt/x'}])[0] is False

    def test_root_mountpoint_is_protected(self):
        valid, msg = self._check([{'volume': 'v', 'mountpoint': '/'}])
        assert valid is False and 'protected' in msg.lower()

    def test_protected_system_dirs_rejected(self):
        for path in ('/etc', '/usr/local', '/home', '/home/lab/workspace', '/opt/conda', '/var/lib', '/tmp'):
            valid, msg = self._check([{'volume': 'v', 'mountpoint': path}])
            assert valid is False and 'protected' in msg.lower(), path

    def test_prefix_match_is_not_substring_match(self):
        # /homestead is NOT under /home - blacklist uses path-segment prefixes
        assert self._check([{'volume': 'v', 'mountpoint': '/homestead'}])[0] is True

    def test_duplicate_mountpoint_is_invalid(self):
        mounts = [
            {'volume': 'a', 'mountpoint': '/mnt/x'},
            {'volume': 'b', 'mountpoint': '/mnt/x/'},
        ]
        valid, msg = self._check(mounts)
        assert valid is False and 'duplicate' in msg.lower()

    def test_duplicate_volume_is_invalid(self):
        mounts = [
            {'volume': 'a', 'mountpoint': '/mnt/x'},
            {'volume': 'a', 'mountpoint': '/mnt/y'},
        ]
        valid, msg = self._check(mounts)
        assert valid is False and 'twice' in msg.lower()

    def test_error_code_via_validate_all(self):
        c = {'volume_mounts': [{'volume': 'v', 'mountpoint': '/etc/x'}]}
        valid, code, _ = GroupConfigValidator.validate_all(c)
        assert valid is False and code == 'invalid_volume_mounts'
