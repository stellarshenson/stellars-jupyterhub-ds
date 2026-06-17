"""Platform event log - a lightweight audit feed for the portal Overview + Events page.

JupyterHub keeps no queryable event history, so this records discrete admin-facing
events (user/group lifecycle, policy changes, broadcasts) into a separate SQLite
database - the same pattern as groups_config / user_profiles. The stored `text` is
pre-escaped HTML (subject in <b>...</b>), safe for the portal to render directly.

The DB path defaults to /data/event_log.sqlite; override with the
STELLARS_EVENT_LOG_DB_PATH env var (tests point it at a temp file).
"""

import logging
import os
import threading
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

log = logging.getLogger('jupyterhub.event_log')

EventLogBase = declarative_base()

# keep the table bounded - prune to the most recent N rows on each record
_MAX_ROWS = 1000


class Event(EventLogBase):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(String(40), nullable=False)
    type = Column(String(40), nullable=False)
    text = Column(Text, nullable=False, default='')


class EventLogManager:
    """Singleton manager for the append-only event log."""

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
        if self._session_factory is not None:
            return self._session_factory()

        path = os.environ.get('STELLARS_EVENT_LOG_DB_PATH', '/data/event_log.sqlite')
        db_url = f'sqlite:///{path}'
        self._engine = create_engine(db_url)
        EventLogBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)
        log.info(f'[EventLog] Database initialized: {db_url}')
        return self._session_factory()

    def record(self, event_type, text):
        """Append an event (ts stamped here). Prunes to the most recent _MAX_ROWS."""
        db = self._get_db()
        try:
            db.add(Event(ts=datetime.now(timezone.utc).isoformat(), type=str(event_type), text=str(text)))
            db.commit()
            # bound the table: delete everything older than the newest _MAX_ROWS
            cutoff = db.query(Event.id).order_by(Event.id.desc()).offset(_MAX_ROWS).first()
            if cutoff:
                db.query(Event).filter(Event.id <= cutoff[0]).delete()
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def recent(self, limit=100):
        """Return the most recent events, newest first, as plain dicts."""
        db = self._get_db()
        try:
            rows = db.query(Event).order_by(Event.id.desc()).limit(limit).all()
            return [{'id': str(r.id), 'ts': r.ts, 'type': r.type, 'text': r.text or ''} for r in rows]
        finally:
            db.close()


def record_event(event_type, text):
    """Best-effort event recording - never raises into the caller's request/hook."""
    try:
        EventLogManager.get_instance().record(event_type, text)
    except Exception as e:  # pragma: no cover - defensive
        log.warning(f'[EventLog] failed to record {event_type} event: {e}')
