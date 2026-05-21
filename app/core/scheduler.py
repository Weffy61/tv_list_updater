import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()
PLAYLIST_DIR = Path(__file__).resolve().parent.parent / "playlists"


async def download_playlist(url: str, filename: str = "playlist.m3u"):
    PLAYLIST_DIR.mkdir(exist_ok=True)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
        (PLAYLIST_DIR / filename).write_bytes(response.content)

        from core.db import SessionLocal
        from models.tv_settings import TVSettings
        with SessionLocal() as db:
            s = db.query(TVSettings).first()
            if s:
                s.last_cached_at = datetime.now(timezone.utc)
                db.commit()
        logging.info("Playlist updated from %s", url)
    except Exception as e:
        logging.error("Failed to download playlist: %s", e)


def schedule_playlist_job(url: str, interval_hours: int, filename: str = "playlist.m3u"):
    scheduler.add_job(
        download_playlist,
        trigger=IntervalTrigger(hours=interval_hours),
        id="playlist_download",
        args=[url, filename],
        replace_existing=True,
    )


def cancel_playlist_job():
    if scheduler.get_job("playlist_download"):
        scheduler.remove_job("playlist_download")
