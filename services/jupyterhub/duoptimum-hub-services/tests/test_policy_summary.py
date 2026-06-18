"""Display-facet tests: summarize_config is the single source for the admin UI's
group badges and hover tooltip (the client renders these strings, never recomputes).
"""

from duoptimum_hub_services.policy import default_config, summarize_config


def _badges(summary):
    return [s['badge'] for s in summary]


def _details(summary):
    return [s['detail'] for s in summary]


def test_empty_config_no_summaries():
    assert summarize_config(default_config()) == []


def test_inactive_sections_excluded():
    c = default_config()
    c.update({'env_vars': [{'name': 'A', 'value': '1'}],  # data present but section off
              'sudo_enable': False})                        # value set but sudo_active off
    assert summarize_config(c) == []


def test_active_sections_summarised_in_registry_order():
    c = default_config()
    c.update({
        'gpu_access': True, 'gpu_all': False, 'gpu_device_ids': ['0', '2'],
        'mem_limit_enabled': True, 'mem_limit_gb': 32, 'mem_swap_disabled': True,
        'sudo_active': True, 'sudo_enable': False,
        'downloads_active': True, 'downloads_allow': False,
    })
    summary = summarize_config(c)
    assert [s['key'] for s in summary] == ['gpu', 'mem', 'sudo', 'downloads']
    assert _badges(summary) == ['GPU', 'Mem', 'Sudo off', 'Downloads off']
    assert _details(summary) == [
        'GPU: 0,2',
        'Memory: 32G (no swap)',
        'Sudo: off',
        'Downloads: blocked',
    ]


def test_each_entry_has_key_badge_detail():
    c = default_config()
    c.update({'gpu_access': True})
    s = summarize_config(c)[0]
    assert set(s) == {'key', 'badge', 'detail'}
    assert s == {'key': 'gpu', 'badge': 'GPU', 'detail': 'GPU: all'}
