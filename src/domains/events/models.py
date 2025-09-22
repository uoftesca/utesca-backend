"""
Event domain models (database models).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from src.core.database import Base


class Event(Base):
    """Event database model."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    event_date = Column(DateTime, nullable=False)
    location = Column(String(200))
    image_url = Column(String(500))
    registration_url = Column(String(500))
    is_featured = Column(Boolean, default=False)
    max_attendees = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
