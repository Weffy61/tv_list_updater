from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from core.db import get_db
from core.paths import PLAYLIST_DIR, MAIN_PLAYLIST, XXX_PLAYLIST
from models.tv_settings import TVSettings, DeliveryType

router = APIRouter()


def _serve_cached(filename: str) -> FileResponse:
    filepath = PLAYLIST_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=503, detail="Плейлист ещё не загружен, попробуйте позже")
    return FileResponse(filepath, media_type="application/x-mpegurl", filename=filename)


@router.get("/tv")
async def redirect_to_tv(db: Session = Depends(get_db)):
    tv = db.query(TVSettings).first()
    if not tv or not tv.tv_link:
        raise HTTPException(status_code=404, detail="TV link not set")

    if tv.delivery_type == DeliveryType.CACHED:
        return _serve_cached(MAIN_PLAYLIST)

    return RedirectResponse(tv.tv_link)


@router.get("/tv-xxx")
async def redirect_to_tv_xxx(db: Session = Depends(get_db)):
    tv = db.query(TVSettings).first()
    if not tv or not tv.tv_link:
        raise HTTPException(status_code=404, detail="TV link not set")

    if tv.delivery_type != DeliveryType.CACHED:
        raise HTTPException(status_code=400, detail="Режим загрузки на сервер не активен")

    if not tv.xxx_link:
        raise HTTPException(status_code=404, detail="Плейлист 18+ не настроен")

    return _serve_cached(XXX_PLAYLIST)
