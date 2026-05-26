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
        'docker_privileged': False,
        'mem_limit_enabled': False,
        'mem_limit_gb': 0,
        'mem_swap_disabled': False,
        'cpu_limit_enabled': False,
        'cpu_limit_cores': 0,
    }


def validate_gpu_selection(gpu_access, gpu_all, gpu_device_ids):
    """Validate a group's GPU selection. Returns (valid: bool, error_message: str).

    Only meaningful when GPU access is enabled. Selecting GPU access while
    deselecting 'all GPUs' requires at least one specific GPU to be chosen -
    otherwise the grant would refer to no devices at all.
    """
    if not gpu_access:
        return True, ''
    if gpu_all:
        return True, ''
    if not gpu_device_ids:
        return False, 'Select at least one GPU, or enable "All GPUs".'
    return True, ''


def validate_docker_selection(docker_access, docker_limited, docker_privileged=False):
    """Validate a group's Docker access choice. Returns (valid, error_message).

    Within one group, normal access (raw socket - sees all, no quota) and limited
    access (per-user ownership-filtering proxy) are mutually exclusive. They are
    orthogonal grants, but a single group must pick one or neither.

    Docker (root) - the --privileged flag on the user container - only makes
    sense alongside one of the two access modes (it raises the privilege of
    the same Docker access, it is not a third independent grant).
    """
    if docker_access and docker_limited:
        return False, 'A group cannot grant both normal and limited Docker access - choose one.'
    if docker_privileged and not (docker_access or docker_limited):
        return False, 'Docker (root) requires either normal or limited Docker access to be enabled.'
    return True, ''


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
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            'group_name': row.group_name,
            'description': row.description or '',
            'priority': row.priority,
            'config': config,
        }
