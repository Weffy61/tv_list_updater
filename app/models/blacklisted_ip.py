from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from core.db import Base


class BlacklistedIP(Base):
    __tablename__ = "blacklisted_ips"

    id = Column(Integer, primary_key=True)
    ip = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
