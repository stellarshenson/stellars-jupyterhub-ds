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
