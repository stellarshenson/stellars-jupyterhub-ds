"""User profile persistence - first/last name + email alongside JupyterHub's orm.User.

JupyterHub's built-in User model only carries the username; NativeAuthenticator's
UserInfo only adds password + authorization. This module stores the display
profile (first name, last name, email) the admin Configure-user and self-service
Profile pages edit, in a separate SQLite database to avoid contention with the
hub's main DB - the same pattern as groups_config.

The DB path defaults to /data/user_profiles.sqlite; override with the
STELLARS_USER_PROFILES_DB_PATH env var (used by tests to point at a temp file).
"""

import logging
import os
import threading

from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

log = logging.getLogger('jupyterhub.user_profiles')

UserProfilesBase = declarative_base()


class UserProfile(UserProfilesBase):
    """One display profile per username."""

    __tablename__ = 'user_profiles'

    username = Column(String(255), primary_key=True)
    first_name = Column(Text, nullable=False, default='')
    last_name = Column(Text, nullable=False, default='')
    email = Column(Text, nullable=False, default='')


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
        self._session_factory = sessionmaker(bind=self._engine)
        log.info(f'[UserProfiles] Database initialized: {db_url}')
        return self._session_factory()

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
            return {'username': username, 'first_name': '', 'last_name': '', 'email': ''}
        return {
            'username': row.username,
            'first_name': row.first_name or '',
            'last_name': row.last_name or '',
            'email': row.email or '',
        }
