"""Policy model base - the interface every group permission implements.

A policy type is a self-contained *model*: one class owning its whole lifecycle.

- ``default()``     - the off-state slice it contributes to ``default_config()``
- ``coerce()``      - normalise + reject an incoming admin write (may raise
  ``PolicyCoerceError``)
- ``validate()``    - coherence check on the merged config, ``(ok, msg)``; the
  engine tags failures with ``validate_code``
- ``resolve()``     - collapse this type's value across a user's matched groups
  (priority-descending) into the effective slice; owns the combine strategy
- ``summarize()``   - display facet: ``{'badge', 'detail'} | None`` for one
  group's config (the admin UI renders these strings, never recomputes them)
- ``apply()``       - impose the resolved value on a spawning server (the
  controller); async, mutates the spawner / registers routes / assigns slots
- ``on_hub_startup()`` - re-impose / reconcile for servers that survived a hub
  restart (pre_spawn_hook only fires on new spawns)

Leaf module: standard library only, no imports from the rest of the package, so
both the models and ``groups_config`` can import it with no cycle. Heavy imports
(docker, jupyterhub, tornado) belong inside ``apply`` / ``on_hub_startup`` bodies.
"""

import re
from dataclasses import dataclass


# ── Mountpoint protection + reserved env names (shared leaf helpers) ──────────

# Valid Docker volume name (Docker's own constraint)
_VOLUME_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')

# The standard shared volume's fixed mountpoint. The volume itself is NEVER stored
# by name in a group config - the hub resolves it by label (role=shared) at spawn,
# so a volume rename never strands a group on a stale name. A group config only
# carries an allow flag + access mode for it. The literal-name-as-custom-mount form
# the old one-click quick-add saved is migrated to this allow flag (by mountpoint).
SHARED_MOUNTPOINT = '/mnt/shared'

# Per-volume access modes (Docker bind modes). rw is the default (full access).
VOLUME_MODES = ('ro', 'rw')
DEFAULT_VOLUME_MODE = 'rw'

# Container paths a group volume may never mount onto. Prefix semantics - a
# mountpoint equal to OR under any of these is rejected (mounting over system
# dirs, the conda env, or the per-user /home tree would break or hijack the lab).
PROTECTED_MOUNTPOINTS = (
    '/bin', '/boot', '/dev', '/etc', '/home', '/lib', '/lib64', '/opt',
    '/proc', '/root', '/run', '/sbin', '/srv', '/sys', '/tmp', '/usr', '/var',
)


def is_protected_mountpoint(path):
    """True when ``path`` is ``/``, a protected dir, or nested under one."""
    norm = '/' + (path or '').strip().strip('/')
    if norm == '/':
        return True
    return any(norm == p or norm.startswith(p + '/') for p in PROTECTED_MOUNTPOINTS)


def is_reserved_env_var(name, reserved_names, reserved_prefixes):
    """Return True if the env var name is reserved (cannot be set by a group)."""
    if not name:
        return True
    if name in reserved_names:
        return True
    for prefix in reserved_prefixes:
        if name.startswith(prefix):
            return True
    return False


# ── Contexts + error ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyCtx:
    """Inputs a resolve/coerce needs that are not in the group config itself."""
    gpu_available: bool = False
    reserved_names: frozenset = frozenset()
    reserved_prefixes: tuple = ()


@dataclass(frozen=True)
class ApplyContext:
    """Spawn-time hub configuration the ``apply`` / ``on_hub_startup`` methods
    need - captured once from ``jupyterhub_config.py`` and threaded through.

    ``app`` and ``username`` are filled per spawn; the rest are static hub config.
    """
    app: object = None
    username: str = ''
    gpu_uuid_by_index: dict = None
    compose_project: str = ''
    docker_proxy_socket_dir: str = ''
    docker_proxy_volume_name: str = ''
    user_compose_project_template: str = ''
    hub_network_name: str = ''
    block_file_downloads: int = 0
    lab_sudo_enable_default: int = 1
    # standard shared volume resolved by label (role=shared) at boot; '' when absent
    # -> the standard mount cannot be placed (allow has no effect, spawn skips it)
    shared_volume_name: str = ''
    # resolve inputs reused by on_hub_startup (it re-resolves per active user)
    gpu_available: bool = False
    reserved_names: frozenset = frozenset()
    reserved_prefixes: tuple = ()
    api_keys_reconcile_interval: int = 0


class PolicyCoerceError(Exception):
    """Raised by a type's ``coerce`` to reject an admin write.

    ``structured`` selects the response shape: structured errors render the
    stable ``{'error': code, 'message': ..., **extra}`` JSON (reserved-name
    rejections); plain errors map to a bare HTTP 400 with the message.
    """

    def __init__(self, message, *, code=None, extra=None, structured=False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.extra = extra or {}
        self.structured = structured


# ── The model interface ────────────────────────────────────────────────────────

class Policy:
    """Base class every policy type subclasses. Defaults make every facet
    optional except ``key``, ``default`` and ``resolve``; a type overrides only
    what it needs."""

    key = ''
    validate_code = ''

    def default(self):
        """Off-state slice this type contributes to ``default_config()``."""
        raise NotImplementedError

    def coerce(self, body, existing, ctx):
        """Normalise an incoming admin write into a config slice (only keys
        present in ``body``). May raise ``PolicyCoerceError``."""
        return {}

    def validate(self, config):
        """Coherence check on the merged config. Returns ``(ok, message)``."""
        return True, ''

    def resolve(self, matched, ctx):
        """Collapse this type's value across the user's matched groups."""
        raise NotImplementedError

    def summarize(self, config):
        """Display facet: ``{'badge', 'detail'}`` or ``None`` when inactive."""
        return None

    async def apply(self, spawner, resolved, actx):
        """Impose the resolved value on a spawning server (the controller)."""
        return None

    async def on_hub_startup(self, app, actx):
        """Re-impose / reconcile for servers that survived a hub restart."""
        return None
