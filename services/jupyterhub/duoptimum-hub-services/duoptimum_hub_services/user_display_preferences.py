"""Per-user display preferences - the portal's client-owned UI options.

Stores each user's Display Options (e.g. how CPU is shown per surface) so the
choice follows the user across browsers/devices rather than living in one
browser's localStorage. The schema is OWNED BY THE CLIENT: the value is an opaque
JSON object, so new options ship as registry entries on the frontend with no
backend change. The store only persists and returns the blob; the client resolves
it against its option registry (defaults for anything missing or invalid).

Separate SQLite DB to avoid contention with the hub's main DB - the same pattern
as user_profiles / groups_config. Defaults to /data/user_display_preferences.sqlite;
override with STELLARS_USER_DISPLAY_PREFS_DB_PATH (used by tests for a temp file).
"""

import json
import os
import threading

from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from .logging_setup import log

UserDisplayPreferencesBase = declarative_base()

# Defensive cap on the serialized blob - the client only ever stores a handful of
# short option keys; anything larger is a bug or abuse, not a legitimate pref set.
MAX_PREFS_BYTES = 8192


class UserDisplayPreferences(UserDisplayPreferencesBase):
    """One opaque JSON prefs blob per username."""

    __tablename__ = 'user_display_preferences'

    username = Column(String(255), primary_key=True)
    prefs = Column(Text, nullable=False, default='{}')


class UserDisplayPreferencesManager:
    """Singleton manager for per-user display-preference CRUD."""

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
        """Lazy-initialize the database connection and create the table."""
        if self._session_factory is not None:
            return self._session_factory()

        path = os.environ.get('STELLARS_USER_DISPLAY_PREFS_DB_PATH', '/data/user_display_preferences.sqlite')
        db_url = f'sqlite:///{path}'
        self._engine = create_engine(db_url)
        UserDisplayPreferencesBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)
        log.info(f'[UserDisplayPreferences] Database initialized: {db_url}')
        return self._session_factory()

    @staticmethod
    def _parse(blob):
        """Tolerant JSON read - a corrupt/empty blob reads as no prefs, never raises."""
        if not blob:
            return {}
        try:
            value = json.loads(blob)
            return value if isinstance(value, dict) else {}
        except (ValueError, TypeError):
            return {}

    def get_prefs(self, username):
        """Return the stored prefs dict for a username, or {} if none."""
        db = self._get_db()
        try:
            row = db.query(UserDisplayPreferences).filter(UserDisplayPreferences.username == username).first()
            return self._parse(row.prefs) if row else {}
        finally:
            db.close()

    def save_prefs(self, username, prefs):
        """Merge the given keys into the user's prefs (partial update) and return
        the merged dict. Only provided keys change; unknown keys are kept verbatim
        (the client owns the schema). Raises ValueError on a non-object or an
        over-cap blob (the handler maps that to a 400)."""
        if not isinstance(prefs, dict):
            raise ValueError('prefs must be a JSON object')
        db = self._get_db()
        try:
            row = db.query(UserDisplayPreferences).filter(UserDisplayPreferences.username == username).first()
            merged = {**self._parse(row.prefs if row else None), **prefs}
            blob = json.dumps(merged, separators=(',', ':'), sort_keys=True)
            if len(blob.encode('utf-8')) > MAX_PREFS_BYTES:
                raise ValueError('preferences payload too large')
            if row is None:
                row = UserDisplayPreferences(username=username, prefs=blob)
                db.add(row)
            else:
                row.prefs = blob
            db.commit()
            return merged
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_prefs(self, username):
        """Delete a user's prefs (called when the user is deleted)."""
        db = self._get_db()
        try:
            db.query(UserDisplayPreferences).filter(UserDisplayPreferences.username == username).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def rename_user(self, old_username, new_username):
        """Move a prefs row to a new username (called on user rename)."""
        db = self._get_db()
        try:
            row = db.query(UserDisplayPreferences).filter(UserDisplayPreferences.username == old_username).first()
            if row is not None:
                row.username = new_username
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
