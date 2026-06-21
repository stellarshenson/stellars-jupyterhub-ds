"""User profile persistence - first/last name + email alongside JupyterHub's orm.User.

JupyterHub's built-in User model only carries the username; NativeAuthenticator's
UserInfo only adds password + authorization. This module stores the display
profile (first name, last name, email) the admin Configure-user and self-service
Profile pages edit, in a separate SQLite database to avoid contention with the
hub's main DB - the same pattern as groups_config.

The DB path defaults to /data/user_profiles.sqlite; override with the
STELLARS_USER_PROFILES_DB_PATH env var (used by tests to point at a temp file).
"""

import os
import threading

from sqlalchemy import Boolean, Column, String, Text, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .logging_setup import log

UserProfilesBase = declarative_base()


class UserProfile(UserProfilesBase):
    """One display profile per username."""

    __tablename__ = 'user_profiles'

    username = Column(String(255), primary_key=True)
    first_name = Column(Text, nullable=False, default='')
    last_name = Column(Text, nullable=False, default='')
    email = Column(Text, nullable=False, default='')
    # force the user to change their password before they can use the platform;
    # set by an admin, cleared on a successful change (see jupyterhub_config)
    must_change_password = Column(Boolean, nullable=False, default=False)


class UserProfileManager:
    """Singleton manager for user-profile CRUD."""

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

        path = os.environ.get('STELLARS_USER_PROFILES_DB_PATH', '/data/user_profiles.sqlite')
        db_url = f'sqlite:///{path}'
        self._engine = create_engine(db_url)
        UserProfilesBase.metadata.create_all(self._engine)
        self._migrate_must_change_password(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)
        log.info(f'[UserProfiles] Database initialized: {db_url}')
        return self._session_factory()

    @staticmethod
    def _migrate_must_change_password(engine):
        """Add the must_change_password column to a pre-existing table - create_all
        only creates missing tables, it never ALTERs an existing one. Idempotent:
        checks the column list first, so a fresh DB (column already present) and an
        old DB (column added here) both end up consistent."""
        cols = {c['name'] for c in inspect(engine).get_columns('user_profiles')}
        if 'must_change_password' not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    'ALTER TABLE user_profiles ADD COLUMN '
                    'must_change_password BOOLEAN NOT NULL DEFAULT 0'))
            log.info('[UserProfiles] migrated: added must_change_password column')

    def get_profile(self, username):
        """Return the stored profile dict for a username, or an empty one if none."""
        db = self._get_db()
        try:
            row = db.query(UserProfile).filter(UserProfile.username == username).first()
            return self._row_to_dict(row, username)
        finally:
            db.close()

    def get_all_profiles(self):
        """Return {username: profile_dict} for every stored profile.

        Backs the admin Users list, which shows each user's display name under
        the username - one read instead of an N+1 per-user fetch.
        """
        db = self._get_db()
        try:
            return {
                row.username: self._row_to_dict(row, row.username)
                for row in db.query(UserProfile).all()
            }
        finally:
            db.close()

    def save_profile(self, username, first_name=None, last_name=None, email=None):
        """Create or update a profile. Only the provided fields are changed."""
        db = self._get_db()
        try:
            row = db.query(UserProfile).filter(UserProfile.username == username).first()
            if row is None:
                row = UserProfile(
                    username=username,
                    first_name=first_name or '',
                    last_name=last_name or '',
                    email=email or '',
                )
                db.add(row)
            else:
                if first_name is not None:
                    row.first_name = first_name
                if last_name is not None:
                    row.last_name = last_name
                if email is not None:
                    row.email = email
            db.commit()
            return self._row_to_dict(row, username)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_must_change_password(self, username):
        """True when the user must change their password before using the platform."""
        db = self._get_db()
        try:
            row = db.query(UserProfile).filter(UserProfile.username == username).first()
            return bool(row.must_change_password) if row else False
        finally:
            db.close()

    def set_must_change_password(self, username, value):
        """Set/clear the force-password-change flag, creating the row if needed.
        Admins set it; the change-password flow clears it on success."""
        db = self._get_db()
        try:
            row = db.query(UserProfile).filter(UserProfile.username == username).first()
            if row is None:
                row = UserProfile(username=username, must_change_password=bool(value))
                db.add(row)
            else:
                row.must_change_password = bool(value)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_profile(self, username):
        """Delete a user's profile (called when the user is deleted)."""
        db = self._get_db()
        try:
            db.query(UserProfile).filter(UserProfile.username == username).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def rename_user(self, old_username, new_username):
        """Move a profile to a new username (called on user rename)."""
        db = self._get_db()
        try:
            row = db.query(UserProfile).filter(UserProfile.username == old_username).first()
            if row is not None:
                row.username = new_username
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _row_to_dict(row, username):
        if row is None:
            return {'username': username, 'first_name': '', 'last_name': '', 'email': '', 'must_change_password': False}
        return {
            'username': row.username,
            'first_name': row.first_name or '',
            'last_name': row.last_name or '',
            'email': row.email or '',
            'must_change_password': bool(row.must_change_password),
        }
