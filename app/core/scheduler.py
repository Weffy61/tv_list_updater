import logging
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.db import SessionLocal
from core.paths import PLAYLIST_DIR, MAIN_PLAYLIST, XXX_PLAYLIST
from models.tv_settings import TVSettings

scheduler = AsyncIOScheduler()
_JOB_ID = "playlist_download"


def _merge_m3u(main: bytes, extra: bytes) -> bytes:
    main_lines = main.decode("utf-8", errors="replace").splitlines()
    extra_lines = extra.decode("utf-8", errors="replace").splitlines()

    result = []
    if main_lines and main_lines[0].startswith("#EXTM3U"):
        result.extend(main_lines)
    else:
        result.append("#EXTM3U")
        result.extend(main_lines)

    result.extend(
        extra_lines[1:] if extra_lines and extra_lines[0].startswith("#EXTM3U") else extra_lines
    )
    return "\n".join(result).encode("utf-8")


async def download_playlist():
    with SessionLocal() as db:
        tv = db.query(TVSettings).first()
        if not tv or not tv.tv_link:
            return
        tv_id, url, xxx_url = tv.id, tv.tv_link, tv.xxx_link or ""

    PLAYLIST_DIR.mkdir(exist_ok=True)
    try:
        headers = {"User-Agent": "VLC/3.0.20 LibVLC/3.0.20"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            (PLAYLIST_DIR / MAIN_PLAYLIST).write_bytes(resp.content)

            if xxx_url:
                xxx_resp = await client.get(xxx_url)
                xxx_resp.raise_for_status()
                (PLAYLIST_DIR / XXX_PLAYLIST).write_bytes(_merge_m3u(resp.content, xxx_resp.content))

        with SessionLocal() as db:
            db.query(TVSettings).filter(TVSettings.id == tv_id).update(
                {"last_cached_at": datetime.now(timezone.utc)}
            )
            db.commit()
        logging.info("Playlist(s) updated from %s", url)
    except Exception as e:
        logging.error("Failed to download playlist: %s", e)


def schedule_playlist_job(interval_hours: int):
    scheduler.add_job(
        download_playlist,
        trigger=IntervalTrigger(hours=interval_hours),
        id=_JOB_ID,
        replace_existing=True,
    )


def cancel_playlist_job():
    if scheduler.get_job(_JOB_ID):
        scheduler.remove_job(_JOB_ID)
