"""ActivitySample ORM model - single source of truth for both hub process and service."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base

ActivityBase = declarative_base()


class ActivitySample(ActivityBase):
    """Database model for storing user activity samples."""
    __tablename__ = 'activity_samples'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, nullable=True)
    active = Column(Boolean, default=False)

    __table_args__ = (
        Index('ix_activity_user_time', 'username', 'timestamp'),
    )
