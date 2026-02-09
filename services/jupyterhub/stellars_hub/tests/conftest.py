"""Shared fixtures for stellars_hub functional tests."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stellars_hub.activity.model import ActivityBase
from stellars_hub.activity.monitor import ActivityMonitor


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Strip JUPYTERHUB_* env vars for test isolation."""
    for key in list(os.environ):
        if key.startswith("JUPYTERHUB_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def reset_activity_monitor():
    """Clear ActivityMonitor singleton before and after test."""
    ActivityMonitor._instance = None
    yield
    ActivityMonitor._instance = None


@pytest.fixture
def memory_db_monitor(reset_activity_monitor):
    """Create ActivityMonitor wired to in-memory SQLite. Returns ready instance."""
    monitor = ActivityMonitor.get_instance()

    engine = create_engine("sqlite:///:memory:")
    ActivityBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    monitor._engine = engine
    monitor._db_session = session
    monitor._initialized = True

    return monitor


@pytest.fixture
def clean_password_cache():
    """Clear password cache before and after test."""
    from stellars_hub.password_cache import _password_cache
    _password_cache.clear()
    yield
    _password_cache.clear()
