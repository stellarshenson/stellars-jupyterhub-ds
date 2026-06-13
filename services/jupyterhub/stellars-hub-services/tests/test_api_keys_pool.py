"""Scenario-matrix tests for the API keys pool.

The pure layer (mask, normalize, pick, env, merge, label parse) backs the
resolver, the spawn-time assignment, and the admin handler, so these matrices
pin the single source of truth. The PoolManager tests drive the assign/reconcile
critical section with a stubbed container observer (no Docker), exercising the
exclusivity invariant, same-user reuse, exhaustion, and multi-pool independence.
"""

import asyncio

import pytest

from stellars_hub_services import api_keys_pool as akp
from stellars_hub_services.api_keys_pool import (
    PoolManager,
    assignment_mask_str,
    env_for_slot,
    mask_last4,
    merge_pool_on_save,
    normalize_pool,
    parse_pool_labels,
    pick_free_slot,
    pool_label_key,
)


# ── mask_last4 ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, expected", [
    ('sk-1234567890', '****7890'),
    ('abcd', '****abcd'),
    ('ab', '****ab'),
    ('', '****'),
    (None, '****'),
])
def test_mask_last4(value, expected):
    assert mask_last4(value) == expected


# ── normalize_pool ───────────────────────────────────────────────────────────

class TestNormalizePool:
    def test_disabled_is_none(self):
        assert normalize_pool({'enabled': False, 'mode': 'single', 'env_var_key': 'K'}) is None

    def test_bad_mode_is_none(self):
        assert normalize_pool({'enabled': True, 'mode': '', 'env_var_key': 'K'}) is None

    def test_no_target_var_is_none(self):
        assert normalize_pool({'enabled': True, 'mode': 'single', 'credentials': [{'slot': 's1', 'key': 'k'}]}) is None

    def test_single_shape(self):
        pool = normalize_pool({
            'enabled': True, 'mode': 'single', 'env_var_key': 'OPENAI_API_KEY',
            'credentials': [{'slot': 's1', 'key': 'k1'}, {'slot': 's2', 'key': 'k2'}],
        })
        assert pool['mode'] == 'single'
        assert pool['env_var_key'] == 'OPENAI_API_KEY'
        assert pool['slot_ids'] == ['s1', 's2']
        assert pool['creds'] == {'s1': {'key': 'k1'}, 's2': {'key': 'k2'}}

    def test_pair_shape(self):
        pool = normalize_pool({
            'enabled': True, 'mode': 'pair', 'env_var_id': 'ID', 'env_var_secret': 'SECRET',
            'credentials': [{'slot': 's1', 'id': 'i1', 'secret': 'x1'}],
        })
        assert pool['slot_ids'] == ['s1']
        assert pool['creds'] == {'s1': {'id': 'i1', 'secret': 'x1'}}

    def test_incomplete_credentials_skipped(self):
        pool = normalize_pool({
            'enabled': True, 'mode': 'pair', 'env_var_id': 'ID', 'env_var_secret': 'SECRET',
            'credentials': [
                {'slot': 's1', 'id': 'i1', 'secret': 'x1'},
                {'slot': 's2', 'id': 'i2'},            # missing secret -> skipped
                {'id': 'i3', 'secret': 'x3'},          # missing slot -> skipped
            ],
        })
        assert pool['slot_ids'] == ['s1']

    def test_valid_names_zero_creds_still_returned(self):
        # AC-23: an enabled pool with no usable credentials still injects (empty).
        pool = normalize_pool({'enabled': True, 'mode': 'single', 'env_var_key': 'K', 'credentials': []})
        assert pool is not None
        assert pool['slot_ids'] == []


# ── pick_free_slot ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("slot_ids, in_use, reserved, expected", [
    (['a', 'b', 'c'], set(), set(), 'a'),
    (['a', 'b', 'c'], {'a'}, set(), 'b'),
    (['a', 'b', 'c'], {'a'}, {'b'}, 'c'),
    (['a', 'b', 'c'], {'a', 'b', 'c'}, set(), None),     # exhausted
    (['a', 'b'], {'x'}, set(), 'a'),                     # unknown in_use ignored
    ([], set(), set(), None),                            # empty pool
    (['a', 'b', 'c'], set(), {'a', 'b'}, 'c'),
])
def test_pick_free_slot(slot_ids, in_use, reserved, expected):
    assert pick_free_slot(slot_ids, in_use, reserved) == expected


# ── env_for_slot ─────────────────────────────────────────────────────────────

def _single_pool():
    return normalize_pool({
        'enabled': True, 'mode': 'single', 'env_var_key': 'K',
        'credentials': [{'slot': 's1', 'key': 'secret-key-1'}],
    })


def _pair_pool():
    return normalize_pool({
        'enabled': True, 'mode': 'pair', 'env_var_id': 'ID', 'env_var_secret': 'SEC',
        'credentials': [{'slot': 's1', 'id': 'id-1', 'secret': 'sec-1'}],
    })


def test_env_for_slot_single_assigned():
    assert env_for_slot(_single_pool(), 's1') == {'K': 'secret-key-1'}


def test_env_for_slot_single_exhausted():
    assert env_for_slot(_single_pool(), None) == {'K': ''}


def test_env_for_slot_pair_assigned():
    assert env_for_slot(_pair_pool(), 's1') == {'ID': 'id-1', 'SEC': 'sec-1'}


def test_env_for_slot_pair_exhausted():
    assert env_for_slot(_pair_pool(), None) == {'ID': '', 'SEC': ''}


def test_env_for_slot_unknown_slot_is_empty():
    assert env_for_slot(_single_pool(), 'nope') == {'K': ''}


# ── assignment_mask_str (logging never leaks) ────────────────────────────────

def test_assignment_mask_single():
    assert assignment_mask_str(_single_pool(), 's1') == 'key=****ey-1'


def test_assignment_mask_pair():
    assert assignment_mask_str(_pair_pool(), 's1') == 'id=****id-1 secret=****ec-1'


def test_assignment_mask_exhausted():
    assert assignment_mask_str(_single_pool(), None) == 'EXHAUSTED'


# ── label scheme ─────────────────────────────────────────────────────────────

def test_pool_label_key():
    assert pool_label_key('team-a') == 'tech.stellars.apikeys.pool.team-a.slot'


@pytest.mark.parametrize("labels, expected", [
    ({'tech.stellars.apikeys.pool.team-a.slot': 's1'}, {'team-a': 's1'}),
    ({'tech.stellars.apikeys.pool.a.slot': 's1',
      'tech.stellars.apikeys.pool.b.slot': 's2'}, {'a': 's1', 'b': 's2'}),
    ({'com.docker.compose.project': 'x'}, {}),                 # unrelated labels
    ({}, {}),                                                  # legacy/no labels (AC-21)
    (None, {}),
])
def test_parse_pool_labels(labels, expected):
    assert parse_pool_labels(labels) == expected


# ── merge_pool_on_save (admin UI stores full values; slot ids stay stable) ───

class TestMergePoolOnSave:
    def _counter(self):
        seq = iter(['new1', 'new2', 'new3'])
        return lambda: next(seq)

    def test_full_value_stored_verbatim(self):
        existing = {'mode': 'single', 'credentials': [{'slot': 's1', 'key': 'real-secret-1234'}]}
        incoming = {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                    'credentials': [{'slot': 's1', 'key': 'real-secret-1234'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert out['credentials'] == [{'slot': 's1', 'key': 'real-secret-1234', 'description': ''}]

    def test_real_new_value_replaces(self):
        existing = {'mode': 'single', 'credentials': [{'slot': 's1', 'key': 'old'}]}
        incoming = {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                    'credentials': [{'slot': 's1', 'key': 'brand-new-value'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert out['credentials'][0]['key'] == 'brand-new-value'
        assert out['credentials'][0]['slot'] == 's1'   # slot preserved

    def test_new_entry_gets_minted_slot(self):
        existing = {'mode': 'single', 'credentials': []}
        incoming = {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                    'credentials': [{'key': 'k-new'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert out['credentials'] == [{'slot': 'new1', 'key': 'k-new', 'description': ''}]

    def test_stale_slot_is_reminted(self):
        # a slot not in the stored set (e.g. client sent a bogus id) is re-minted
        existing = {'mode': 'single', 'credentials': [{'slot': 's1', 'key': 'k1'}]}
        incoming = {'enabled': True, 'mode': 'single', 'env_var_key': 'K',
                    'credentials': [{'slot': 'ghost', 'key': 'k2'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert out['credentials'][0]['slot'] == 'new1'

    def test_description_stored_verbatim(self):
        existing = {'mode': 'single', 'credentials': [{'slot': 's1', 'key': 'k1', 'description': 'prod key'}]}
        incoming = {'enabled': True, 'mode': 'single', 'env_var_key': 'K', 'credentials': [
            {'slot': 's1', 'key': 'k1', 'description': 'prod key'},
            {'key': 'k2', 'description': 'dev key'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert out['credentials'][0]['description'] == 'prod key'
        assert out['credentials'][1]['description'] == 'dev key'

    def test_reorder_keeps_slot_ids(self):
        existing = {'mode': 'single', 'credentials': [
            {'slot': 's1', 'key': 'k1'}, {'slot': 's2', 'key': 'k2'}]}
        incoming = {'enabled': True, 'mode': 'single', 'env_var_key': 'K', 'credentials': [
            {'slot': 's2', 'key': 'k2'},
            {'slot': 's1', 'key': 'k1'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert [c['slot'] for c in out['credentials']] == ['s2', 's1']
        assert [c['key'] for c in out['credentials']] == ['k2', 'k1']

    def test_pair_values_stored(self):
        existing = {'mode': 'pair', 'credentials': [{'slot': 's1', 'id': 'id-aaaa', 'secret': 'sec-bbbb'}]}
        incoming = {'enabled': True, 'mode': 'pair', 'env_var_id': 'ID', 'env_var_secret': 'SEC',
                    'credentials': [{'slot': 's1', 'id': 'id-aaaa', 'secret': 'sec-NEW'}]}
        out = merge_pool_on_save(incoming, existing, self._counter())
        assert out['credentials'][0]['id'] == 'id-aaaa'
        assert out['credentials'][0]['secret'] == 'sec-NEW'


# ── PoolManager.assign / reconcile (stubbed observer, no Docker) ─────────────

@pytest.fixture
def manager(monkeypatch):
    """Fresh PoolManager with a controllable in-memory container observer."""
    PoolManager._instance = None
    state = {'by_pool': {}, 'by_container': {}}

    async def fake_observe():
        return dict(state['by_pool']), dict(state['by_container'])

    monkeypatch.setattr(akp, 'observe_in_use', fake_observe)
    monkeypatch.setattr(akp, '_container_name', lambda u: f'jupyterlab-{u}')
    mgr = PoolManager.get_instance()
    yield mgr, state
    PoolManager._instance = None


def _pool(pool_id, *keys):
    p = normalize_pool({
        'enabled': True, 'mode': 'single', 'env_var_key': f'KEY_{pool_id.upper()}',
        'credentials': [{'slot': f'{pool_id}-{i}', 'key': k} for i, k in enumerate(keys)],
    })
    p['pool_id'] = pool_id
    return p


class TestPoolManagerAssign:
    def test_exclusivity_two_users_distinct_slots(self, manager):
        mgr, _ = manager
        pool = _pool('p', 'k0', 'k1')
        a = asyncio.run(mgr.assign('alice', [_pool('p', 'k0', 'k1')]))
        b = asyncio.run(mgr.assign('bob', [pool]))
        slot_a = a['labels'][pool_label_key('p')]
        slot_b = b['labels'][pool_label_key('p')]
        assert slot_a != slot_b                       # AC-13: no shared credential
        assert a['env']['KEY_P'] != b['env']['KEY_P']

    def test_same_user_duplicate_spawn_reuses_slot(self, manager):
        mgr, _ = manager
        first = asyncio.run(mgr.assign('alice', [_pool('p', 'k0', 'k1')]))
        second = asyncio.run(mgr.assign('alice', [_pool('p', 'k0', 'k1')]))
        assert first['labels'] == second['labels']    # AC-15: same slot reused

    def test_reuse_from_running_container_label(self, manager):
        mgr, state = manager
        # alice already has a running container holding slot p-1 (durable label)
        state['by_pool'] = {'p': {'p-1'}}
        state['by_container'] = {'jupyterlab-alice': {'p': 'p-1'}}
        res = asyncio.run(mgr.assign('alice', [_pool('p', 'k0', 'k1')]))
        assert res['labels'][pool_label_key('p')] == 'p-1'
        assert res['env']['KEY_P'] == 'k1'

    def test_exhaustion_sets_empty_and_flags(self, manager):
        mgr, _ = manager
        asyncio.run(mgr.assign('alice', [_pool('p', 'only')]))   # takes the only slot
        res = asyncio.run(mgr.assign('bob', [_pool('p', 'only')]))
        assert res['env'] == {'KEY_P': ''}                       # AC-23 empty var
        assert res['labels'] == {}                               # no slot label
        assert res['assignments'][0]['slot'] is None             # AC-24 exhausted
        assert res['assignments'][0]['masked'] == 'EXHAUSTED'

    def test_multi_pool_independent_assignment(self, manager):
        mgr, _ = manager
        pools = [_pool('a', 'ka0'), _pool('b', 'kb0')]
        res = asyncio.run(mgr.assign('alice', pools))            # AC-29
        assert res['env'] == {'KEY_A': 'ka0', 'KEY_B': 'kb0'}
        assert set(res['labels']) == {pool_label_key('a'), pool_label_key('b')}

    def test_two_pools_same_var_higher_group_wins(self, manager):
        # AC-30: two pools target the same env var; the group higher in the list
        # (lower group_index) supplies the value, the lower one is shadowed.
        mgr, _ = manager
        hi = _pool('hi', 'hi-key'); hi['env_var_key'] = 'SHARED'; hi['group_index'] = 0
        lo = _pool('lo', 'lo-key'); lo['env_var_key'] = 'SHARED'; lo['group_index'] = 1
        res = asyncio.run(mgr.assign('alice', [hi, lo]))
        assert res['env']['SHARED'] == 'hi-key'
        assert res['env_sources']['SHARED'] == 0           # winner's group index
        # both still get their own durable label (independent slot bookkeeping)
        assert set(res['labels']) == {pool_label_key('hi'), pool_label_key('lo')}


class TestPoolManagerReconcile:
    def test_reaps_tentative_when_user_gone(self, manager):
        mgr, state = manager
        asyncio.run(mgr.assign('alice', [_pool('p', 'k0')]))     # tentative p-0
        # alice never produced a running container -> reconcile releases the slot
        summary = asyncio.run(mgr.reconcile())
        assert summary['reaped'] == 1
        # slot is now free again for the next assignment
        res = asyncio.run(mgr.assign('bob', [_pool('p', 'k0')]))
        assert res['labels'][pool_label_key('p')] == 'p-0'

    def test_promotes_tentative_when_label_durable(self, manager):
        mgr, state = manager
        asyncio.run(mgr.assign('alice', [_pool('p', 'k0')]))
        # alice's container is now running with the durable label
        state['by_pool'] = {'p': {'p-0'}}
        state['by_container'] = {'jupyterlab-alice': {'p': 'p-0'}}
        summary = asyncio.run(mgr.reconcile())
        assert summary['reaped'] == 1                            # tentative cleared
        assert summary['in_use'] == 1                            # observed durably


class TestRestartPersistence:
    """A spawned lab outlives the hub, so the in-use set must survive a hub
    restart - rebuilt from the durable per-container slot label - or two running
    labs collide on the same credential. The `manager` fixture hands us a fresh
    PoolManager (empty tentative bookkeeping), exactly the post-restart state;
    the observer reports the labs that survived."""

    def test_no_collision_after_hub_restart(self, manager):
        mgr, state = manager
        # Two labs survived the restart, each holding a durable slot label.
        state['by_pool'] = {'p': {'p-0', 'p-1'}}
        state['by_container'] = {
            'jupyterlab-alice': {'p': 'p-0'},
            'jupyterlab-bob': {'p': 'p-1'},
        }
        # A third user spawns against the rebuilt-from-labels in-use set.
        res = asyncio.run(mgr.assign('carol', [_pool('p', 'k0', 'k1', 'k2')]))
        slot = res['labels'].get(pool_label_key('p'))
        assert slot == 'p-2'                       # the only free slot
        assert slot not in {'p-0', 'p-1'}          # neither survivor re-handed-out

    def test_survivor_keeps_own_slot_after_restart(self, manager):
        mgr, state = manager
        # alice's lab survived the restart holding p-1; her next spawn reuses it
        # (label-derived), never allocating a second credential.
        state['by_pool'] = {'p': {'p-1'}}
        state['by_container'] = {'jupyterlab-alice': {'p': 'p-1'}}
        res = asyncio.run(mgr.assign('alice', [_pool('p', 'k0', 'k1')]))
        assert res['labels'][pool_label_key('p')] == 'p-1'

    def test_exhausted_after_restart_never_reuses_live_slot(self, manager):
        mgr, state = manager
        # All slots held by survivors -> a new user gets EXHAUSTED, never a
        # collision with a live credential.
        state['by_pool'] = {'p': {'p-0', 'p-1'}}
        state['by_container'] = {
            'jupyterlab-alice': {'p': 'p-0'},
            'jupyterlab-bob': {'p': 'p-1'},
        }
        res = asyncio.run(mgr.assign('carol', [_pool('p', 'k0', 'k1')]))
        assert res['labels'] == {}                 # no slot stamped
        assert res['assignments'][0]['slot'] is None
        assert res['assignments'][0]['masked'] == 'EXHAUSTED'
