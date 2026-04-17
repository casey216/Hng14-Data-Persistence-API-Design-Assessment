from datetime import datetime, timezone

from sqlalchemy import Column, Float, Integer, String, DateTime
from uuid_extensions import uuid7str

from app.db import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True, default=uuid7str)
    name = Column(String, nullable=False)
    gender = Column(String)
    gender_probability = Column(Float)
    sample_size = Column(Integer)
    age = Column(Integer)
    age_group = Column(String)
    country_id = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))