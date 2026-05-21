from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from core.db import get_db
from core.scheduler import PLAYLIST_DIR
from models.tv_settings import TVSettings

router = APIRouter()


@router.get("/tv")
async def redirect_to_tv(db: Session = Depends(get_db)):
    tv = db.query(TVSettings).first()
    if not tv or not tv.tv_link:
        return {"error": "TV link not set"}

    if tv.delivery_type == "cached":
        filepath: Path = PLAYLIST_DIR / (tv.cached_filename or "playlist.m3u")
        if not filepath.exists():
            return {"error": "Плейлист ещё не загружен, попробуйте позже"}
        return FileResponse(filepath, media_type="application/x-mpegurl", filename=filepath.name)

    return RedirectResponse(tv.tv_link)
