"""Unit tests for the protected-env dictionary loader."""

import pytest

from duoptimum_hub_services.protected_env import (
    DEFAULT_PROTECTED_NAMES,
    DEFAULT_PROTECTED_PREFIXES,
    load_protected_env,
)


def test_missing_file_falls_back_to_defaults(tmp_path):
    names, prefixes = load_protected_env(str(tmp_path / 'nope.yml'))
    assert names == set(DEFAULT_PROTECTED_NAMES)
    assert prefixes == tuple(DEFAULT_PROTECTED_PREFIXES)


def test_empty_path_falls_back_to_defaults():
    names, prefixes = load_protected_env('')
    assert names == set(DEFAULT_PROTECTED_NAMES)
    assert prefixes == tuple(DEFAULT_PROTECTED_PREFIXES)


def test_loads_names_and_prefixes(tmp_path):
    p = tmp_path / 'protected.yml'
    p.write_text('names:\n  - FOO\n  - BAR\nprefixes:\n  - X_\n  - Y_\n')
    names, prefixes = load_protected_env(str(p))
    assert names == {'FOO', 'BAR'}
    assert prefixes == ('X_', 'Y_')


def test_returns_types_set_and_tuple(tmp_path):
    p = tmp_path / 'protected.yml'
    p.write_text('names: [A]\nprefixes: [B_]\n')
    names, prefixes = load_protected_env(str(p))
    assert isinstance(names, set)
    assert isinstance(prefixes, tuple)


def test_missing_keys_yield_empty(tmp_path):
    p = tmp_path / 'protected.yml'
    p.write_text('names: [A]\n')  # no prefixes key
    names, prefixes = load_protected_env(str(p))
    assert names == {'A'}
    assert prefixes == ()


def test_non_mapping_raises(tmp_path):
    p = tmp_path / 'protected.yml'
    p.write_text('- just\n- a\n- list\n')
    with pytest.raises(ValueError):
        load_protected_env(str(p))


def test_non_list_values_raise(tmp_path):
    p = tmp_path / 'protected.yml'
    p.write_text('names: FOO\nprefixes: X_\n')
    with pytest.raises(ValueError):
        load_protected_env(str(p))


def test_real_dictionary_has_expected_protected_names():
    """The shipped dictionary must protect the policy-owned names + the hub prefixes."""
    import os
    here = os.path.dirname(__file__)
    real = os.path.normpath(os.path.join(here, '..', '..', 'conf', 'protected_env_dictionary.yml'))
    names, prefixes = load_protected_env(real)
    assert {'NVIDIA_VISIBLE_DEVICES', 'CUDA_VISIBLE_DEVICES', 'DOCKER_HOST', 'JUPYTERLAB_SUDO_ENABLE',
            'JUPYTERLAB_USER_ENV_ENABLE'} <= names
    # docker-stacks root-time privilege levers must be protected (sudo-policy bypass)
    assert {'GRANT_SUDO', 'NB_UID', 'NB_GID', 'CHOWN_HOME', 'CHOWN_EXTRA'} <= names
    assert 'JUPYTERHUB_' in prefixes
