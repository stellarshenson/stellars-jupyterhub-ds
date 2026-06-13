"""Group configuration persistence - custom DB table alongside JupyterHub's orm.Group.

JupyterHub's built-in Group model only has name and users. This module adds
a separate SQLite database to store group configuration: description, priority
order, environment variables, GPU access, and Docker access settings.
"""

import json
import logging
import re
import threading

from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

log = logging.getLogger('jupyterhub.groups_config')

GroupsConfigBase = declarative_base()

# Valid group name: starts with letter, then letters/digits/hyphens/underscores
_GROUP_NAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')

# Valid Docker volume name (Docker's own constraint)
_VOLUME_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')

# Mountpoint blacklist: container paths a group volume may never mount onto.
# Prefix semantics - a mountpoint equal to OR under any of these is rejected
# (mounting over system dirs, the conda env, or the per-user /home tree would
# break or hijack the lab). Admin-managed mounts belong under /mnt, /data etc.
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


class GroupConfig(GroupsConfigBase):
    """Persistent configuration for a JupyterHub group."""
    __tablename__ = 'groups_config'

    group_name = Column(String(255), primary_key=True)
    description = Column(Text, nullable=True, default='')
    priority = Column(Integer, nullable=False, default=0)
    config = Column(Text, nullable=False, default='{}')


def default_config():
    """Return default empty group configuration."""
    return {
        # Section active flags: when False the resolver treats the section as
        # unconfigured but its data persists (re-enabling restores it). GPU,
        # memory, CPU and API-keys sections reuse their own enable flags
        # (gpu_access / mem_limit_enabled / cpu_limit_enabled /
        # api_keys_pool.enabled) for the same semantics.
        'env_vars_active': False,
        'docker_active': False,
        'volume_mounts_active': False,
        # File downloads (best-effort, hub-side): section-gated, priority-wins.
        # When downloads_active is on the group explicitly configures member
        # downloads to downloads_allow (True=allow/False=block) and the highest-
        # priority configuring group wins; section off = does not configure
        # (resolver returns None, the hook applies the platform default derived
        # from JUPYTERHUB_LAB_BLOCK_FILE_DOWNLOADS). downloads_allow defaults True so
        # a freshly-enabled section allows downloads until explicitly blocked.
        # No inference for legacy rows (absent active flag = not configured),
        # no validator - both are always-valid booleans.
        'downloads_active': False,
        'downloads_allow': True,
        # Sudo access: section-gated, priority-wins. When sudo_active is on the
        # group explicitly configures member sudo to sudo_enable (True=1/False=0)
        # and the highest-priority configuring group wins; section off = does
        # not configure (resolver returns None, the hook applies the platform
        # JUPYTERHUB_LAB_SUDO_ENABLE). sudo_enable defaults True so a
        # freshly-enabled section grants sudo until explicitly disabled.
        'sudo_active': False,
        'sudo_enable': True,
        'env_vars': [],
        'gpu_access': False,
        'gpu_all': True,          # all GPUs (default); when False, gpu_device_ids applies
        'gpu_device_ids': [],     # specific GPU index strings, e.g. ['0', '2']
        'docker_access': False,        # normal: raw host docker.sock (sees all, no quota)
        'docker_limited': False,       # limited: per-user ownership-filtering proxy
        'docker_limited_max_containers': 10,
        'docker_limited_max_volumes': 10,
        'docker_limited_max_networks': 3,
        'docker_limited_max_storage_gb': 50,
        'docker_limited_cpu_cap_cores': 2,
        'docker_limited_mem_cap_gb': 8,
        # OFF by default. When True, the limited proxy stops rejecting host
        # bind mounts, host net/pid, cap-add, and device passthrough for this
        # user. Ownership labelling and quota caps still apply. Surfaced in
        # the admin UI with a strong warning - flipping it on hands the user
        # the kernel-level escape vectors via the proxy.
        'docker_limited_allow_dangerous_flags': False,
        # Per-user compose-project enforcement. When enabled, ad-hoc `docker run`s
        # are stamped with a per-user project label rendered from a platform
        # template (default `{username}_containers`). When
        # allow_override is True the user can still pass `-p name` to their own
        # `docker compose` and it is respected; when False the proxy rewrites
        # the user's label too. Both default True - feel free to turn enforcement
        # off for groups whose users should remain in the hub's compose project.
        'docker_limited_user_compose_project_enabled': True,
        'docker_limited_user_compose_project_allow_override': True,
        # ON by default. When True, the user's filtered docker socket grants
        # full access to the hub's docker network (from JUPYTERHUB_NETWORK_NAME):
        # the network appears in `docker network ls`, containers can attach via
        # `--network <hub-net>` on create, and `docker network connect <hub-net>`
        # works - so user containers can resolve other containers (incl. the hub
        # services) by DNS. Off = the hub network is invisible AND inaccessible:
        # network ls hides it; container create with --network <hub-net> is
        # rejected; connect/disconnect actions return 404. Owned networks and
        # built-in modes (bridge/none/default/container:*) are unaffected.
        'docker_limited_hub_network_access': True,
        'docker_privileged': False,
        'mem_limit_enabled': False,
        'mem_limit_gb': 0,
        'mem_swap_disabled': False,
        'cpu_limit_enabled': False,
        'cpu_limit_cores': 0,
        # API keys pool: a finite set of credentials handed out one-per-running-
        # container (see api_keys_pool.py). mode 'pair' uses env_var_id +
        # env_var_secret; mode 'single' uses env_var_key. Each credential carries
        # a stable `slot` id; secrets are stored verbatim here and masked at the
        # API boundary.
        'api_keys_pool': {
            'enabled': False,
            'mode': '',               # '' | 'pair' | 'single'
            'env_var_id': '',
            'env_var_secret': '',
            'env_var_key': '',
            'credentials': [],        # [{slot, id, secret, description}] (pair) | [{slot, key, description}] (single)
        },
        # Volume mounts: named Docker volumes mounted into member containers
        # at spawn. OFF by default (empty) - the platform shared volume is no
        # longer auto-mounted; admins grant it per group. Missing volumes are
        # auto-created by Docker on first spawn (same as per-user volumes).
        'volume_mounts': [],          # [{volume: <docker volume name>, mountpoint: <absolute path>}]
    }


def infer_active_flags(config, stored):
    """Fill missing section-active flags on legacy rows by inferring from data.

    ``config`` is the merged dict (defaults + stored), mutated in place;
    ``stored`` is the raw dict loaded from the DB. A flag explicitly present
    in ``stored`` is authoritative (a deactivated section keeps its data but
    stays off). A flag absent from ``stored`` predates the feature - infer it
    so existing groups keep working: active iff the section carries config.
    """
    if 'env_vars_active' not in stored:
        config['env_vars_active'] = bool(config.get('env_vars'))
    if 'docker_active' not in stored:
        config['docker_active'] = bool(
            config.get('docker_access') or config.get('docker_limited')
            or config.get('docker_privileged')
        )
    if 'volume_mounts_active' not in stored:
        config['volume_mounts_active'] = bool(config.get('volume_mounts'))
    return config


class GroupConfigValidator:
    """Field-level validators for group config dicts.

    Each class method takes a partial config dict and returns
    ``(valid: bool, error_message: str)``. ``validate_all`` runs every
    validator in turn and returns the first failure, or ``(True, '')`` if
    they all pass. Errors carry an ``error`` code (used by handlers) and a
    user-facing ``message``; the handler maps them to HTTP 400 responses.

    The class is stateless - all methods are pure functions of the input
    dict, no DB / I/O. Defaults align with ``default_config()`` so partial
    dicts validate the same way as full ones.
    """

    @classmethod
    def validate_gpu(cls, config):
        """GPU access on + not "all" + no specific device id is incoherent.

        ``code = 'invalid_gpu_selection'`` on failure.
        """
        if not config.get('gpu_access'):
            return True, ''
        if config.get('gpu_all', True):
            return True, ''
        if not (config.get('gpu_device_ids') or []):
            return False, 'Select at least one GPU, or enable "All GPUs".'
        return True, ''

    @classmethod
    def validate_docker(cls, config):
        """Mutual exclusivity of access modes within one group + sanity on the
        limited-Docker quotas. Docker (root) is orthogonal - allowed standalone
        OR combined with either access mode.

        Skipped when the Docker section is inactive (``docker_active`` falsy
        and the flag explicitly present) - inactive means unconfigured, so
        stale data in a folded section never blocks saving.

        ``code = 'invalid_docker_selection'`` on failure.
        """
        if 'docker_active' in config and not config.get('docker_active'):
            return True, ''
        docker_access = config.get('docker_access')
        docker_limited = config.get('docker_limited')
        if docker_access and docker_limited:
            return False, 'A group cannot grant both normal and limited Docker access - choose one.'
        if docker_limited:
            for key in ('docker_limited_max_containers', 'docker_limited_max_volumes',
                        'docker_limited_max_networks', 'docker_limited_max_storage_gb',
                        'docker_limited_cpu_cap_cores', 'docker_limited_mem_cap_gb'):
                try:
                    val = float(config.get(key) or 0)
                except (TypeError, ValueError):
                    return False, f'{key} must be a number.'
                if val < 0:
                    return False, f'{key} cannot be negative.'
        return True, ''

    @classmethod
    def validate_cpu(cls, config):
        """When the CPU cap is enabled, cores must be a positive number.
        A zero cap with "enabled" is meaningless (would translate to no quota
        at spawn-time and silently render the toggle inert).

        ``code = 'invalid_cpu_limit'`` on failure.
        """
        if not config.get('cpu_limit_enabled'):
            return True, ''
        try:
            cores = float(config.get('cpu_limit_cores') or 0)
        except (TypeError, ValueError):
            return False, 'CPU limit (cores) must be a number.'
        if cores <= 0:
            return False, 'CPU limit (cores) must be greater than zero when enabled.'
        return True, ''

    @classmethod
    def validate_mem(cls, config):
        """When the memory cap is enabled, GB must be a positive number. Swap
        policy is independent and needs no validation (its truthiness flows to
        the spawner only when a cap is set).

        ``code = 'invalid_mem_limit'`` on failure.
        """
        if not config.get('mem_limit_enabled'):
            return True, ''
        try:
            gb = float(config.get('mem_limit_gb') or 0)
        except (TypeError, ValueError):
            return False, 'Memory limit (GB) must be a number.'
        if gb <= 0:
            return False, 'Memory limit (GB) must be greater than zero when enabled.'
        return True, ''

    @classmethod
    def validate_api_keys_pool(cls, config):
        """When the API keys pool is enabled, a mode is required and the matching
        target variable names plus complete credentials must be present. Reserved
        target names are rejected separately by the handler (same as env_vars).

        ``code = 'invalid_api_keys_pool'`` on failure.
        """
        pool = config.get('api_keys_pool') or {}
        if not pool.get('enabled'):
            return True, ''
        mode = pool.get('mode')
        if mode not in ('pair', 'single'):
            return False, 'Select an API keys pool mode: key-id/secret pair or single api key.'
        creds = pool.get('credentials') or []
        if mode == 'pair':
            if not (pool.get('env_var_id') or '').strip() or not (pool.get('env_var_secret') or '').strip():
                return False, 'Pair mode requires both a key-id and a key-secret variable name.'
            for c in creds:
                if not (c.get('id') or '').strip() or not (c.get('secret') or '').strip():
                    return False, 'Every pair credential needs both an id and a secret.'
        else:
            if not (pool.get('env_var_key') or '').strip():
                return False, 'Single mode requires an api-key variable name.'
            for c in creds:
                if not (c.get('key') or '').strip():
                    return False, 'Every single credential needs a key value.'
        return True, ''

    @classmethod
    def validate_volume_mounts(cls, config):
        """Each volume mount needs a valid Docker volume name and an absolute,
        non-protected mountpoint; mountpoints must be unique within the group.
        The PROTECTED_MOUNTPOINTS blacklist is enforced here, i.e. at save time
        - a config that mounts over a system dir never reaches the database.

        Skipped when the section is inactive (``volume_mounts_active`` falsy
        and the flag explicitly present) - same rationale as Docker above.

        ``code = 'invalid_volume_mounts'`` on failure.
        """
        if 'volume_mounts_active' in config and not config.get('volume_mounts_active'):
            return True, ''
        mounts = config.get('volume_mounts') or []
        seen_mountpoints = set()
        seen_volumes = set()
        for entry in mounts:
            volume = (entry.get('volume') or '').strip()
            mountpoint = (entry.get('mountpoint') or '').strip()
            if not volume or not mountpoint:
                return False, 'Every volume mount needs both a volume name and a mountpoint.'
            if not _VOLUME_NAME_RE.match(volume):
                return False, f'Invalid volume name "{volume}" - use letters, digits, ".", "_" or "-".'
            if not mountpoint.startswith('/'):
                return False, f'Mountpoint "{mountpoint}" must be an absolute path.'
            if is_protected_mountpoint(mountpoint):
                return False, f'Mountpoint "{mountpoint}" is a protected location - mount under /mnt or /data instead.'
            norm = '/' + mountpoint.strip('/')
            if norm in seen_mountpoints:
                return False, f'Duplicate mountpoint "{norm}" - each mountpoint can hold one volume.'
            # Docker mounts are keyed by volume name - one volume, one mountpoint
            if volume in seen_volumes:
                return False, f'Volume "{volume}" is listed twice - a volume can be mounted at one mountpoint only.'
            seen_mountpoints.add(norm)
            seen_volumes.add(volume)
        return True, ''

    _ALL = (
        ('invalid_gpu_selection', 'validate_gpu'),
        ('invalid_docker_selection', 'validate_docker'),
        ('invalid_cpu_limit', 'validate_cpu'),
        ('invalid_mem_limit', 'validate_mem'),
        ('invalid_api_keys_pool', 'validate_api_keys_pool'),
        ('invalid_volume_mounts', 'validate_volume_mounts'),
    )

    @classmethod
    def validate_all(cls, config):
        """Run every validator. Returns ``(valid, error_code, message)`` -
        first failure wins so the user is shown one error at a time. Returns
        ``(True, '', '')`` when all checks pass.
        """
        for code, name in cls._ALL:
            valid, msg = getattr(cls, name)(config)
            if not valid:
                return False, code, msg
        return True, '', ''


def validate_gpu_selection(gpu_access, gpu_all, gpu_device_ids):
    """Thin backward-compatible wrapper around ``GroupConfigValidator.validate_gpu``."""
    return GroupConfigValidator.validate_gpu({
        'gpu_access': gpu_access,
        'gpu_all': gpu_all,
        'gpu_device_ids': gpu_device_ids,
    })


def validate_docker_selection(docker_access, docker_limited, docker_privileged=False):
    """Thin backward-compatible wrapper around ``GroupConfigValidator.validate_docker``."""
    return GroupConfigValidator.validate_docker({
        'docker_access': docker_access,
        'docker_limited': docker_limited,
        'docker_privileged': docker_privileged,
    })


def validate_group_name(name):
    """Validate group name for JupyterHub compatibility.

    Returns (valid: bool, error_message: str).
    """
    if not name:
        return False, 'Group name cannot be empty'
    if len(name) > 255:
        return False, 'Group name cannot exceed 255 characters'
    if not _GROUP_NAME_RE.match(name):
        return False, 'Group name must start with a letter and contain only letters, digits, hyphens, and underscores'
    return True, ''


class GroupsConfigManager:
    """Singleton manager for group configuration CRUD operations.

    Uses a separate SQLite database at /data/groups_config.sqlite to avoid
    contention with JupyterHub's main database.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._engine = None
        self._session_factory = None

    def _get_db(self):
        """Lazy-initialize database connection and create tables."""
        if self._session_factory is not None:
            return self._session_factory()

        db_url = 'sqlite:////data/groups_config.sqlite'
        self._engine = create_engine(db_url)
        GroupsConfigBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)
        log.info(f'[GroupsConfig] Database initialized: {db_url}')
        return self._session_factory()

    def get_all_configs(self):
        """Return all group configs as list of dicts, sorted by priority descending."""
        db = self._get_db()
        try:
            rows = db.query(GroupConfig).order_by(GroupConfig.priority.desc()).all()
            return [self._row_to_dict(r) for r in rows]
        finally:
            db.close()

    def get_config(self, group_name):
        """Return config for one group, or None if not found."""
        db = self._get_db()
        try:
            row = db.query(GroupConfig).filter(GroupConfig.group_name == group_name).first()
            return self._row_to_dict(row) if row else None
        finally:
            db.close()

    def ensure_config(self, group_name):
        """Return config for a group, creating default if missing."""
        existing = self.get_config(group_name)
        if existing:
            return existing
        return self.save_config(group_name, description='', priority=0, config_dict=default_config())

    def save_config(self, group_name, description=None, priority=None, config_dict=None):
        """Create or update group configuration. Returns the saved config dict."""
        db = self._get_db()
        try:
            row = db.query(GroupConfig).filter(GroupConfig.group_name == group_name).first()
            if row is None:
                row = GroupConfig(
                    group_name=group_name,
                    description=description or '',
                    priority=priority if priority is not None else 0,
                    config=json.dumps(config_dict if config_dict is not None else default_config()),
                )
                db.add(row)
            else:
                if description is not None:
                    row.description = description
                if priority is not None:
                    row.priority = priority
                if config_dict is not None:
                    row.config = json.dumps(config_dict)
            db.commit()
            result = self._row_to_dict(row)
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_config(self, group_name):
        """Delete configuration for a group."""
        db = self._get_db()
        try:
            db.query(GroupConfig).filter(GroupConfig.group_name == group_name).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def reorder(self, groups_priorities):
        """Bulk update priorities. groups_priorities: list of {name, priority}."""
        db = self._get_db()
        try:
            for item in groups_priorities:
                row = db.query(GroupConfig).filter(
                    GroupConfig.group_name == item['name']
                ).first()
                if row:
                    row.priority = item['priority']
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _row_to_dict(row):
        """Convert a GroupConfig row to a plain dict."""
        config = default_config()
        try:
            stored = json.loads(row.config or '{}')
            config.update(stored)
            infer_active_flags(config, stored)
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            'group_name': row.group_name,
            'description': row.description or '',
            'priority': row.priority,
            'config': config,
        }
