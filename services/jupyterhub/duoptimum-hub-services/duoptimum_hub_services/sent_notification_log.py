"""Platform sent-notification log - the portal "Past Notifications" history.

The broadcast handler records each broadcast it sends (message, type, delivered /
total) into a dedicated SQLite database so the portal Notifications page can show a
sent-history feed; JupyterHub keeps no such record. Same store pattern as
event_log / groups_config / user_profiles.

The store is self-healing: prepare() runs at hub boot and (re)creates the table
when the /data DB was never initialised, was inherited from an older deploy without
this table, or carries a stale schema. It logs whenever it has to create or repair
so the heal is visible in the hub logs; it stays silent when the schema is already
correct, and never raises into boot.

DB path defaults to /data/sent_notification_log.sqlite; override with the
STELLARS_SENT_NOTIFICATION_LOG_DB_PATH env var (tests point it at a temp file).
"""

import logging
import os
import threading
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

log = logging.getLogger('jupyterhub.sent_notification_log')

SentNotificationBase = declarative_base()

# keep the table bounded - prune to the most recent N rows on each record
_MAX_ROWS = 500

_TABLE = 'sent_notifications'
# columns prepare() guarantees; an existing table missing any of these is rebuilt
_EXPECTED_COLUMNS = {'id', 'ts', 'message', 'type', 'delivered', 'total'}


class SentNotification(SentNotificationBase):
    __tablename__ = _TABLE

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(String(40), nullable=False)
    message = Column(Text, nullable=False, default='')
    type = Column(String(40), nullable=False, default='info')
    delivered = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)


class SentNotificationLogManager:
    """Singleton manager for the append-only sent-notification log."""

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
        self._path = None

    def _ensure_engine(self):
        if self._engine is None:
            self._path = os.environ.get('STELLARS_SENT_NOTIFICATION_LOG_DB_PATH', '/data/sent_notification_log.sqlite')
            self._engine = create_engine(f'sqlite:///{self._path}')
            self._session_factory = sessionmaker(bind=self._engine)
        return self._engine

    def prepare(self):
        """Boot-time schema check + self-heal (idempotent, never raises).

        Creates the table when the DB file has none (fresh or inherited /data) and
        rebuilds it when an existing table is missing expected columns (a stale
        schema from an older deploy). Logs every create/repair; silent when the
        schema is already good.
        """
        try:
            engine = self._ensure_engine()
            insp = inspect(engine)
            if not insp.has_table(_TABLE):
                SentNotificationBase.metadata.create_all(engine)
                log.info(f"[SentNotificationLog] table '{_TABLE}' created at {self._path} (was absent - fresh or inherited /data)")
                return
            cols = {c['name'] for c in insp.get_columns(_TABLE)}
            missing = _EXPECTED_COLUMNS - cols
            if missing:
                log.warning(
                    f"[SentNotificationLog] table '{_TABLE}' at {self._path} has a stale schema "
                    f"(missing columns {sorted(missing)}); rebuilding"
                )
                SentNotificationBase.metadata.drop_all(engine)
                SentNotificationBase.metadata.create_all(engine)
                log.info(f"[SentNotificationLog] table '{_TABLE}' rebuilt at {self._path}")
            # schema already correct -> no log, avoid boot noise
        except Exception as e:  # pragma: no cover - defensive, never block boot
            log.warning(f"[SentNotificationLog] schema preparation failed: {e}")

    def _get_db(self):
        self._ensure_engine()
        # idempotent; guards the lazy path if prepare() was never called
        SentNotificationBase.metadata.create_all(self._engine)
        return self._session_factory()

    def record(self, message, notif_type, delivered, total):
        """Append a sent notification (ts stamped here). Prunes to _MAX_ROWS."""
        db = self._get_db()
        try:
            db.add(SentNotification(
                ts=datetime.now(timezone.utc).isoformat(),
                message=str(message),
                type=str(notif_type),
                delivered=int(delivered),
                total=int(total),
            ))
            db.commit()
            cutoff = db.query(SentNotification.id).order_by(SentNotification.id.desc()).offset(_MAX_ROWS).first()
            if cutoff:
                db.query(SentNotification).filter(SentNotification.id <= cutoff[0]).delete()
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def clear(self):
        """Delete every sent notification (the admin "Clear" action). Returns count removed."""
        db = self._get_db()
        try:
            n = db.query(SentNotification).delete()
            db.commit()
            return n
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def recent(self, limit=100):
        """Most recent sent notifications, newest first, in the portal's row shape."""
        db = self._get_db()
        try:
            rows = db.query(SentNotification).order_by(SentNotification.id.desc()).limit(limit).all()
            return [
                {
                    'id': str(r.id),
                    'message': r.message or '',
                    'type': r.type or 'info',
                    'sentISO': r.ts,
                    'delivered': int(r.delivered or 0),
                    'total': int(r.total or 0),
                }
                for r in rows
            ]
        finally:
            db.close()


def prepare_sent_notification_log():
    """Best-effort boot preparation - call once from jupyterhub_config.py."""
    SentNotificationLogManager.get_instance().prepare()


def record_sent_notification(message, notif_type, delivered, total):
    """Best-effort recording - never raises into the broadcast handler."""
    try:
        SentNotificationLogManager.get_instance().record(message, notif_type, delivered, total)
    except Exception as e:  # pragma: no cover - defensive
        log.warning(f'[SentNotificationLog] failed to record sent notification: {e}')
