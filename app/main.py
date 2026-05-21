from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text

from core.db import Base, engine, SessionLocal
from core.scheduler import scheduler, schedule_playlist_job
from core.security import hash_password
from core.config import settings
from models.user import User
from models.tv_settings import TVSettings, DeliveryType
from routes import admin, redirect


def _run_migrations():
    insp = inspect(engine)
    if "tv_settings" not in insp.get_table_names():
        return
    existing = {col["name"] for col in insp.get_columns("tv_settings")}
    migrations = {
        "delivery_type": "ALTER TABLE tv_settings ADD COLUMN delivery_type VARCHAR DEFAULT 'redirect'",
        "update_interval_hours": "ALTER TABLE tv_settings ADD COLUMN update_interval_hours INTEGER DEFAULT 6",
        "cached_filename": "ALTER TABLE tv_settings ADD COLUMN cached_filename VARCHAR DEFAULT 'playlist.m3u'",
        "last_cached_at": "ALTER TABLE tv_settings ADD COLUMN last_cached_at DATETIME",
        "xxx_link": "ALTER TABLE tv_settings ADD COLUMN xxx_link VARCHAR",
        "cached_xxx_filename": "ALTER TABLE tv_settings ADD COLUMN cached_xxx_filename VARCHAR DEFAULT 'playlist-xxx.m3u'",
    }
    with engine.connect() as conn:
        for col, sql in migrations.items():
            if col not in existing:
                conn.execute(text(sql))
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()

    with SessionLocal() as db:
        if not db.query(User).first():
            db.add(User(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
            ))
            db.commit()

        if not db.query(TVSettings).first():
            db.add(TVSettings(tv_link="", delivery_type=DeliveryType.REDIRECT, update_interval_hours=6))
            db.commit()

    scheduler.start()

    with SessionLocal() as db:
        tv = db.query(TVSettings).first()
        if tv and tv.delivery_type == DeliveryType.CACHED and tv.tv_link:
            schedule_playlist_job(tv.update_interval_hours or 6)

    yield

    scheduler.shutdown()


app = FastAPI(title="TV Redirector", lifespan=lifespan)
app.include_router(admin.router)
app.include_router(redirect.router)
