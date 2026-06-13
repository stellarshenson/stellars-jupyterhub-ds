"""Group policy bundle round-trip - the import/export foundation.

A group serialises to ``{group_name, description, priority, policies}`` where
``policies`` is the registry-typed config dict. Exporting then importing the
bundle (JSON out, JSON in, coerce each slice back through the registry) must
reproduce the source config - the contract import/export will build on. Re-import
uses the bundle as its own ``existing`` so api-keys slot ids are preserved (a
fresh-group import intentionally re-mints them).
"""

import json

from stellars_hub_services.policy import (
    PolicyCtx,
    coerce_config,
    default_config,
    validate_all,
)


def _sample_config():
    cfg = default_config()
    cfg.update({
        'env_vars_active': True,
        'env_vars': [{'name': 'ENV', 'value': 'prod'}, {'name': 'EXTRA', 'value': '1'}],
        'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': ['0', '2'],
        'docker_active': True, 'docker_limited': True, 'docker_limited_max_containers': 25,
        'mem_limit_enabled': True, 'mem_limit_gb': 32, 'mem_swap_disabled': True,
        'cpu_limit_enabled': True, 'cpu_limit_cores': 8,
        'sudo_active': True, 'sudo_enable': False,
        'downloads_active': True, 'downloads_allow': False,
        'volume_mounts_active': True,
        'volume_mounts': [{'volume': 'data', 'mountpoint': '/mnt/data'}],
        'api_keys_pool': {
            'enabled': True, 'mode': 'single', 'env_var_id': '', 'env_var_secret': '',
            'env_var_key': 'TOKEN',
            'credentials': [{'slot': 'fixed-slot', 'key': 't-1', 'description': ''}],
        },
    })
    return cfg


def _export_bundle(group_name, description, priority, config):
    return {'group_name': group_name, 'description': description,
            'priority': priority, 'policies': config}


def _import_bundle(bundle):
    """Re-materialise a config from a bundle's policies via the registry."""
    ctx = PolicyCtx()
    policies = bundle['policies']
    config = default_config()
    config.update(coerce_config(policies, policies, ctx))
    return config


def test_bundle_round_trips_deep_equal():
    cfg = _sample_config()
    bundle = _export_bundle('analysts', 'data team', 7, cfg)

    # Serialise out and back (the export/import wire format is JSON).
    restored = json.loads(json.dumps(bundle))
    assert restored['group_name'] == 'analysts'
    assert restored['description'] == 'data team'
    assert restored['priority'] == 7

    reimported = _import_bundle(restored)
    assert reimported == cfg


def test_reimported_bundle_validates():
    cfg = _sample_config()
    bundle = json.loads(json.dumps(_export_bundle('g', '', 0, cfg)))
    reimported = _import_bundle(bundle)
    ok, code, msg = validate_all(reimported)
    assert ok is True, f"{code}: {msg}"


def test_empty_group_round_trips():
    cfg = default_config()
    bundle = json.loads(json.dumps(_export_bundle('blank', '', 0, cfg)))
    assert _import_bundle(bundle) == cfg
