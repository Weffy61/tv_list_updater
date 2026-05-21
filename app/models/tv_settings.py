from enum import StrEnum

from sqlalchemy import Column, Integer, String, DateTime

from core.db import Base


class DeliveryType(StrEnum):
    REDIRECT = "redirect"
    CACHED = "cached"


class TVSettings(Base):
    __tablename__ = "tv_settings"

    id = Column(Integer, primary_key=True, index=True)
    tv_link = Column(String, nullable=False)
    delivery_type = Column(String, nullable=False, server_default=DeliveryType.REDIRECT.value)
    update_interval_hours = Column(Integer, nullable=False, server_default="6")
    last_cached_at = Column(DateTime, nullable=True)
    xxx_link = Column(String, nullable=True)
