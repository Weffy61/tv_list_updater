from sqlalchemy import Column, Integer, String
from ..core.db import Base


class TVSettings(Base):
    __tablename__ = "tv_settings"

    id = Column(Integer, primary_key=True, index=True)
    tv_link = Column(String, nullable=False)
