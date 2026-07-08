"""Unit tests for the per-user environment-variables store, its blacklist
validation, the handler auth split, and spawn-time injection."""

import asyncio
import logging
import os
import types
from types import SimpleNamespace

import pytest
from tornado import web

from duoptimum_hub_services.user_env_vars import (
    EnvVarError,
    MAX_ENV_BYTES,
    MAX_ENV_COUNT,
    UserEnvVars,
    UserEnvVarsManager,
)

RESERVED_NAMES = frozenset({'JUPYTERLAB_TIMEZONE', 'DOCKER_HOST'})
RESERVED_PREFIXES = ('JUPYTERHUB_', 'CPU_')


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """A fresh manager backed by a temp SQLite file (never touches /data)."""
    monkeypatch.setattr(UserEnvVarsManager, 'db_path', str(tmp_path / 'env.sqlite'))
    UserEnvVarsManager._instance = None
    mgr = UserEnvVarsManager.get_instance()
    yield mgr
    UserEnvVarsManager._instance = None


def _ev(name, value='', description=''):
    return {'name': name, 'value': value, 'description': description}


# ── store CRUD ───────────────────────────────────────────────────────────────

def test_get_missing_returns_empty(manager):
    assert manager.get_env_vars('alice') == []


def test_set_then_get_roundtrips(manager):
    manager.set_env_vars('alice', [_ev('EDITOR', 'vim', 'my editor')])
    assert manager.get_env_vars('alice') == [{'name': 'EDITOR', 'value': 'vim', 'description': 'my editor'}]


def test_replace_semantics_removes(manager):
    """REPLACE, not merge: a var absent from the new set is gone (removal works)."""
    manager.set_env_vars('alice', [_ev('A', '1'), _ev('B', '2')])
    manager.set_env_vars('alice', [_ev('A', '1')])
    names = [e['name'] for e in manager.get_env_vars('alice')]
    assert names == ['A']


def test_description_preserved(manager):
    manager.set_env_vars('alice', [_ev('A', '1', 'the a var')])
    assert manager.get_env_vars('alice')[0]['description'] == 'the a var'


def test_value_coerced_to_str(manager):
    manager.set_env_vars('alice', [{'name': 'A', 'value': None}, {'name': 'B', 'value': 7}])
    got = {e['name']: e['value'] for e in manager.get_env_vars('alice')}
    assert got == {'A': '', 'B': '7'}


def test_blank_name_rows_dropped(manager):
    stored = manager.set_env_vars('alice', [_ev('', 'ignored'), _ev('A', '1'), _ev('   ', 'x')])
    assert [e['name'] for e in stored] == ['A']


# ── blacklist validation ─────────────────────────────────────────────────────

def test_reserved_exact_name_rejected(manager):
    with pytest.raises(EnvVarError) as exc:
        manager.set_env_vars('alice', [_ev('DOCKER_HOST', 'x')], RESERVED_NAMES, RESERVED_PREFIXES)
    assert exc.value.code == 'reserved_env_var_names'
    assert 'DOCKER_HOST' in exc.value.rejected


def test_reserved_prefix_rejected(manager):
    with pytest.raises(EnvVarError) as exc:
        manager.set_env_vars('alice', [_ev('JUPYTERHUB_FOO', 'x')], RESERVED_NAMES, RESERVED_PREFIXES)
    assert exc.value.code == 'reserved_env_var_names'
    assert 'JUPYTERHUB_FOO' in exc.value.rejected


def test_invalid_name_rejected(manager):
    with pytest.raises(EnvVarError) as exc:
        manager.set_env_vars('alice', [_ev('1BAD', 'x'), _ev('has space', 'y')])
    assert exc.value.code == 'invalid_env_var_names'
    assert set(exc.value.rejected) == {'1BAD', 'has space'}


def test_duplicate_name_rejected(manager):
    with pytest.raises(EnvVarError) as exc:
        manager.set_env_vars('alice', [_ev('A', '1'), _ev('A', '2')])
    assert exc.value.code == 'duplicate_env_var_names'
    assert exc.value.rejected == ['A']


def test_non_list_rejected(manager):
    with pytest.raises(EnvVarError):
        manager.set_env_vars('alice', {'not': 'a list'})


def test_too_many_rejected(manager):
    many = [_ev(f'V{i}', str(i)) for i in range(MAX_ENV_COUNT + 1)]
    with pytest.raises(EnvVarError) as exc:
        manager.set_env_vars('alice', many)
    assert exc.value.code == 'too_many'


def test_oversize_rejected(manager):
    with pytest.raises(EnvVarError) as exc:
        manager.set_env_vars('alice', [_ev('BIG', 'x' * (MAX_ENV_BYTES + 1))])
    assert exc.value.code == 'too_large'


def test_valid_names_accepted_when_reserved_supplied(manager):
    stored = manager.set_env_vars('alice', [_ev('MY_VAR', 'ok')], RESERVED_NAMES, RESERVED_PREFIXES)
    assert stored == [{'name': 'MY_VAR', 'value': 'ok', 'description': ''}]


# ── lifecycle + resilience ───────────────────────────────────────────────────

def test_rename_moves(manager):
    manager.set_env_vars('alice', [_ev('A', '1')])
    manager.rename_user('alice', 'alicia')
    assert manager.get_env_vars('alice') == []
    assert [e['name'] for e in manager.get_env_vars('alicia')] == ['A']


def test_delete_removes(manager):
    manager.set_env_vars('bob', [_ev('A', '1')])
    manager.delete_env_vars('bob')
    assert manager.get_env_vars('bob') == []


def test_db_uses_overridden_path(manager, tmp_path):
    manager.set_env_vars('carol', [_ev('A', '1')])
    assert os.path.exists(str(tmp_path / 'env.sqlite'))


def test_corrupt_blob_reads_empty(manager):
    db = manager._get_db()
    try:
        db.add(UserEnvVars(username='dave', env_vars='{not valid json'))
        db.commit()
    finally:
        db.close()
    assert manager.get_env_vars('dave') == []
    # a subsequent save still works (overwrites the corrupt blob)
    assert manager.set_env_vars('dave', [_ev('OK', '1')]) == [{'name': 'OK', 'value': '1', 'description': ''}]


# ── injection view ───────────────────────────────────────────────────────────

def test_get_injectable_drops_description_and_returns_name_value(manager):
    manager.set_env_vars('alice', [_ev('EDITOR', 'vim', 'desc'), _ev('PAGER', 'less')])
    assert manager.get_injectable('alice') == {'EDITOR': 'vim', 'PAGER': 'less'}


def test_get_injectable_filters_reserved_defensively(manager):
    """A reserved name that somehow got stored is filtered at injection time even
    though set_env_vars would have rejected it - defense-in-depth vs a reserved set
    that changed after the vars were saved."""
    # write a reserved var directly, bypassing set_env_vars validation
    db = manager._get_db()
    try:
        db.add(UserEnvVars(username='eve', env_vars='[{"name":"DOCKER_HOST","value":"evil"},{"name":"OK","value":"1"}]'))
        db.commit()
    finally:
        db.close()
    inj = manager.get_injectable('eve', RESERVED_NAMES, RESERVED_PREFIXES)
    assert inj == {'OK': '1'}


# ── handler auth (self-or-admin) ─────────────────────────────────────────────

def _stub_handler(current_user):
    """Build the handler without booting a hub. current_user is a read-only property
    on JupyterHub's BaseHandler, so shadow it on a throwaway subclass rather than
    assigning the instance attribute."""
    from duoptimum_hub_services.handlers.user_env_vars import UserEnvVarsHandler

    class _StubHandler(UserEnvVarsHandler):
        pass

    _StubHandler.current_user = property(lambda self: current_user)
    return _StubHandler.__new__(_StubHandler)


def test_authorize_admin_allows_any():
    _stub_handler(SimpleNamespace(admin=True, name='root'))._authorize('someone-else')  # no raise


def test_authorize_self_allows_own():
    _stub_handler(SimpleNamespace(admin=False, name='alice'))._authorize('alice')  # no raise


def test_authorize_other_forbidden():
    with pytest.raises(web.HTTPError) as exc:
        _stub_handler(SimpleNamespace(admin=False, name='alice'))._authorize('bob')
    assert exc.value.status_code == 403


def test_authorize_anonymous_forbidden():
    with pytest.raises(web.HTTPError) as exc:
        _stub_handler(None)._authorize('alice')
    assert exc.value.status_code == 403


# ── spawn injection through the real pre_spawn_hook ──────────────────────────

def test_hook_injects_user_env_and_strips_reserved(manager):
    from duoptimum_hub_services.hooks import make_pre_spawn_hook

    # store a legit var plus a reserved one written directly (bypassing validation)
    manager.set_env_vars('alice', [_ev('EDITOR', 'vim')])
    db = manager._get_db()
    try:
        row = db.query(UserEnvVars).filter(UserEnvVars.username == 'alice').first()
        row.env_vars = '[{"name":"EDITOR","value":"vim"},{"name":"JUPYTERHUB_X","value":"sneak"}]'
        db.commit()
    finally:
        db.close()

    hook = make_pre_spawn_hook(
        {'lab_main_icon_static': '', 'lab_main_icon_url': '', 'lab_splash_icon_static': '', 'lab_splash_icon_url': ''},
        gpu_available=False,
        reserved_env_var_names=RESERVED_NAMES,
        reserved_env_var_prefixes=RESERVED_PREFIXES,
        compose_project='',
    )
    spawner = types.SimpleNamespace(
        user=types.SimpleNamespace(name='alice', groups=[]),
        volumes={}, extra_host_config={}, environment={}, extra_create_kwargs={},
        mem_limit=None, log=logging.getLogger('test_env_hook'),
    )
    asyncio.run(hook(spawner))
    assert spawner.environment.get('EDITOR') == 'vim'
    assert 'JUPYTERHUB_X' not in spawner.environment  # reserved stripped defensively


_ICONS = {'lab_main_icon_static': '', 'lab_main_icon_url': '',
          'lab_splash_icon_static': '', 'lab_splash_icon_url': ''}


def _spawner(environment):
    return types.SimpleNamespace(
        user=types.SimpleNamespace(name='alice', groups=[]),
        volumes={}, extra_host_config={}, environment=environment, extra_create_kwargs={},
        mem_limit=None, log=logging.getLogger('test_env_hook'),
    )


def test_hook_system_env_on_injects_flag_and_user_env(manager):
    """System-env on (lab default): the flag is 1, the user's vars inject, sudo stays on."""
    from duoptimum_hub_services.hooks import make_pre_spawn_hook
    manager.set_env_vars('alice', [_ev('EDITOR', 'vim')])
    hook = make_pre_spawn_hook(
        _ICONS, gpu_available=False,
        reserved_env_var_names=RESERVED_NAMES, reserved_env_var_prefixes=RESERVED_PREFIXES,
        compose_project='', lab_user_env_enable_default=1, lab_sudo_enable_default=1)
    spawner = _spawner({})
    asyncio.run(hook(spawner))
    assert spawner.environment.get('EDITOR') == 'vim'
    assert spawner.environment.get('JUPYTERLAB_USER_ENV_ENABLE') == '1'
    assert spawner.environment.get('JUPYTERLAB_SUDO_ENABLE') == '1'


def _hook(user_env_default, sudo_default=1):
    from duoptimum_hub_services.hooks import make_pre_spawn_hook
    return make_pre_spawn_hook(
        _ICONS, gpu_available=False,
        reserved_env_var_names=RESERVED_NAMES, reserved_env_var_prefixes=RESERVED_PREFIXES,
        compose_project='', lab_user_env_enable_default=user_env_default,
        lab_sudo_enable_default=sudo_default)


def test_hook_system_env_off_removes_stale_user_env_and_gates_sudo(manager):
    """Reused spawner across a system-env-off flip: a var injected on the prior
    (system-env on) spawn is ACTIVELY removed on the next spawn - not merely skipped
    (regression: add-only update would leak it into the container until a hub restart)."""
    manager.set_env_vars('alice', [_ev('EDITOR', 'vim')])
    spawner = _spawner({})
    asyncio.run(_hook(1)(spawner))                        # spawn 1: system-env ON
    assert spawner.environment.get('EDITOR') == 'vim'
    asyncio.run(_hook(0)(spawner))                        # operator flips OFF; same spawner
    assert 'EDITOR' not in spawner.environment            # stale user var removed
    assert spawner.environment.get('JUPYTERLAB_USER_ENV_ENABLE') == '0'
    assert spawner.environment.get('JUPYTERLAB_SUDO_ENABLE') == '0'  # gate forces sudo off


def test_hook_removes_var_deleted_from_store_on_respawn(manager):
    """Store-independent removal also clears a var the user DELETED from their store
    between spawns (system-env stays on) - the tracked-key approach, not a store recompute."""
    manager.set_env_vars('alice', [_ev('FOO', '1'), _ev('BAR', '2')])
    spawner = _spawner({})
    asyncio.run(_hook(1)(spawner))
    assert spawner.environment.get('BAR') == '2'
    manager.set_env_vars('alice', [_ev('FOO', '1')])      # user deletes BAR
    asyncio.run(_hook(1)(spawner))                        # respawn, same spawner
    assert 'BAR' not in spawner.environment               # deleted var no longer stale
    assert spawner.environment.get('FOO') == '1'


def test_hook_group_system_env_off_reaches_resolved(manager, monkeypatch):
    """A GROUP-level system-env off (lab default ON) must reach the hook's resolved dict:
    no per-user injection, flag 0, sudo forced off. Proves resolved is the flat merge the
    policy apply also reads (hook and apply cannot disagree)."""
    from duoptimum_hub_services.groups_config import GroupsConfigManager
    manager.set_env_vars('alice', [_ev('EDITOR', 'vim')])
    cfg = {'group_name': 'g1',
           'config': {'sudo_active': True, 'sudo_enable': False, 'user_env_enable': False}}
    monkeypatch.setattr(GroupsConfigManager, 'get_all_configs', lambda self: [cfg])
    spawner = _spawner({})
    spawner.user.groups = [types.SimpleNamespace(name='g1')]
    asyncio.run(_hook(1)(spawner))                        # lab default ON, group forces OFF
    assert 'EDITOR' not in spawner.environment
    assert spawner.environment.get('JUPYTERLAB_USER_ENV_ENABLE') == '0'
    assert spawner.environment.get('JUPYTERLAB_SUDO_ENABLE') == '0'
