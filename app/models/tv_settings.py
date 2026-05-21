from sqlalchemy import Column, Integer, String, DateTime
from core.db import Base


class TVSettings(Base):
    __tablename__ = "tv_settings"

    id = Column(Integer, primary_key=True, index=True)
    tv_link = Column(String, nullable=False)
    delivery_type = Column(String, nullable=False, server_default="redirect")
    update_interval_hours = Column(Integer, nullable=False, server_default="6")
    cached_filename = Column(String, nullable=False, server_default="playlist.m3u")
    last_cached_at = Column(DateTime, nullable=True)
