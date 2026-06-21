"""Shared fixtures for duoptimum_hub_services functional tests."""

import logging
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from duoptimum_hub_services.activity.model import ActivityBase
from duoptimum_hub_services.activity.monitor import ActivityMonitor
from duoptimum_hub_services.logging_setup import logger as _loguru_logger


@pytest.fixture
def caplog(caplog):
    """Bridge loguru -> pytest's caplog.

    The platform logs through the shared loguru sink, not stdlib logging, so
    caplog sees nothing by default. Add a temporary loguru sink that forwards
    each record into the caplog handler (the standard loguru recipe), so tests
    that assert on caplog.records keep working after the loguru migration.
    """
    handler_id = _loguru_logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
    )
    yield caplog
    _loguru_logger.remove(handler_id)


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
    from duoptimum_hub_services.password_cache import _password_cache
    _password_cache.clear()
    yield
    _password_cache.clear()
