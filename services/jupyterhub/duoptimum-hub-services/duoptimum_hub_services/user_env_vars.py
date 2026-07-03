"""Per-user environment variables - a self-service (or admin-managed) set of
name/value/description entries injected into the user's lab container on spawn.

Same wire shape as the group policy env-var editor (list of ``{name, value,
description}``) and guarded by the SAME blacklist (``is_reserved_env_var`` against
the platform/policy-owned reserved names + prefixes), so a user cannot shadow
``JUPYTERHUB_*``, the GPU selectors, ``DOCKER_HOST``, etc. ``description`` is UI
metadata only - it is stored and shown but NEVER injected as an env var.

Separate SQLite DB to avoid contention with the hub's main DB - fixed at
/data/user_env_vars.sqlite (the hub data volume, beside jupyterhub.sqlite). Tests
point the class-level ``db_path`` at a temp file; there is no env override.

Storage is REPLACE, not merge: ``set_env_vars`` overwrites the whole set so removing
a variable actually removes it (unlike the display-prefs merge).
"""

import json
import re
import threading

from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .logging_setup import log
from .policy.base import is_reserved_env_var

UserEnvVarsBase = declarative_base()

# Defensive caps - a personal env set is a handful of short vars; anything larger
# is a bug or abuse, not a legitimate set.
MAX_ENV_BYTES = 16384
MAX_ENV_COUNT = 100

# POSIX-ish env var name rule: a letter/underscore then alnum/underscore.
_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class EnvVarError(ValueError):
    """Validation failure carrying a machine ``code`` + the offending ``rejected``
    names, so the handler returns a structured 400 the SPA can map to rows."""

    def __init__(self, message, code='invalid_env_vars', rejected=None):
        super().__init__(message)
        self.code = code
        self.rejected = rejected or []


class UserEnvVars(UserEnvVarsBase):
    """One JSON list of {name, value, description} per username."""

    __tablename__ = 'user_env_vars'

    username = Column(String(255), primary_key=True)
    env_vars = Column(Text, nullable=False, default='[]')


def _normalize(env_vars, reserved_names, reserved_prefixes):
    """Validate + clean a raw env_vars list into the stored form.

    Drops blank-name rows (the editor's empty rows); strips names; enforces the
    name rule, the reserved blacklist, uniqueness and the count cap. Raises
    ``EnvVarError`` (reserved > invalid-name > duplicate > count) on any violation.
    """
    if not isinstance(env_vars, list):
        raise EnvVarError('env_vars must be a list', code='invalid_env_vars')
    cleaned, seen, bad_names, reserved_hit, dup = [], set(), [], [], []
    for entry in env_vars:
        if not isinstance(entry, dict) or 'name' not in entry:
            raise EnvVarError("Each env var must be an object with a 'name'", code='invalid_env_vars')
        name = (entry.get('name') or '').strip()
        if not name:
            continue  # blank row from the editor - drop silently
        if not _NAME_RE.match(name):
            bad_names.append(name)
            continue
        if is_reserved_env_var(name, reserved_names, reserved_prefixes):
            reserved_hit.append(name)
            continue
        if name in seen:
            dup.append(name)
            continue
        seen.add(name)
        value = entry.get('value', '')
        desc = entry.get('description', '')
        cleaned.append({
            'name': name,
            'value': '' if value is None else str(value),
            'description': '' if desc is None else str(desc),
        })
    if reserved_hit:
        raise EnvVarError(
            'Reserved variable names cannot be set: ' + ', '.join(sorted(set(reserved_hit)))
            + '. These are controlled by JupyterHub or the platform.',
            code='reserved_env_var_names', rejected=sorted(set(reserved_hit)))
    if bad_names:
        raise EnvVarError(
            'Invalid variable names (letters, digits, underscore; not starting with a digit): '
            + ', '.join(sorted(set(bad_names))),
            code='invalid_env_var_names', rejected=sorted(set(bad_names)))
    if dup:
        raise EnvVarError('Duplicate variable names: ' + ', '.join(sorted(set(dup))),
                          code='duplicate_env_var_names', rejected=sorted(set(dup)))
    if len(cleaned) > MAX_ENV_COUNT:
        raise EnvVarError(f'Too many variables (max {MAX_ENV_COUNT})', code='too_many')
    return cleaned


class UserEnvVarsManager:
    """Singleton manager for per-user env-var CRUD."""

    _instance = None
    _lock = threading.Lock()

    # Fixed store path in the hub data volume (beside jupyterhub.sqlite). A plain
    # constant, not an env knob; tests point it at a temp file via the class attribute.
    db_path = '/data/user_env_vars.sqlite'

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
        """Lazy-initialize the database connection and create the table."""
        if self._session_factory is not None:
            return self._session_factory()
        db_url = f'sqlite:///{self.db_path}'
        self._engine = create_engine(db_url)
        UserEnvVarsBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)
        log.info(f'[UserEnvVars] Database initialized: {db_url}')
        return self._session_factory()

    @staticmethod
    def _parse(blob):
        """Tolerant read - a corrupt/empty/non-list blob reads as no vars, and any
        malformed entry is dropped, so a bad row never breaks a spawn."""
        if not blob:
            return []
        try:
            value = json.loads(blob)
        except (ValueError, TypeError):
            return []
        if not isinstance(value, list):
            return []
        out = []
        for e in value:
            if isinstance(e, dict) and isinstance(e.get('name'), str) and e['name']:
                out.append({
                    'name': e['name'],
                    'value': str(e.get('value', '')),
                    'description': str(e.get('description', '')),
                })
        return out

    def get_env_vars(self, username):
        """Return the stored list of {name, value, description} for a username, or []."""
        db = self._get_db()
        try:
            row = db.query(UserEnvVars).filter(UserEnvVars.username == username).first()
            return self._parse(row.env_vars) if row else []
        finally:
            db.close()

    def set_env_vars(self, username, env_vars, reserved_names=frozenset(), reserved_prefixes=()):
        """Validate + REPLACE the user's whole env set; return the stored list.
        Raises ``EnvVarError`` (handler maps to 400) on a reserved/invalid/duplicate
        name or an over-cap payload."""
        cleaned = _normalize(env_vars, reserved_names, reserved_prefixes)
        blob = json.dumps(cleaned, separators=(',', ':'))
        if len(blob.encode('utf-8')) > MAX_ENV_BYTES:
            raise EnvVarError('environment payload too large', code='too_large')
        db = self._get_db()
        try:
            row = db.query(UserEnvVars).filter(UserEnvVars.username == username).first()
            if row is None:
                row = UserEnvVars(username=username, env_vars=blob)
                db.add(row)
            else:
                row.env_vars = blob
            db.commit()
            return cleaned
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_injectable(self, username, reserved_names=frozenset(), reserved_prefixes=()):
        """name->value dict for spawn injection: ``description`` dropped (UI metadata,
        not an env var) and reserved names filtered again as defense-in-depth against
        a reserved set that changed after the vars were saved."""
        return {
            e['name']: e['value']
            for e in self.get_env_vars(username)
            if not is_reserved_env_var(e['name'], reserved_names, reserved_prefixes)
        }

    def delete_env_vars(self, username):
        """Delete a user's env vars (called when the user is deleted)."""
        db = self._get_db()
        try:
            db.query(UserEnvVars).filter(UserEnvVars.username == username).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def rename_user(self, old_username, new_username):
        """Move an env-vars row to a new username (called on user rename)."""
        db = self._get_db()
        try:
            row = db.query(UserEnvVars).filter(UserEnvVars.username == old_username).first()
            if row is not None:
                row.username = new_username
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
