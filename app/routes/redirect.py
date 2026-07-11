import base64

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from core.db import get_db
from core.paths import PLAYLIST_DIR, MAIN_PLAYLIST, XXX_PLAYLIST
from models.tv_settings import TVSettings, DeliveryType

router = APIRouter()


def _encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def _rewrite_kizug(content: str, server_base: str) -> str:
    lines = content.splitlines(keepends=True)
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "kizug.ru" in stripped:
            result.append(f"{server_base}/proxy?url={_encode_url(stripped)}" + ("\n" if line.endswith("\n") else ""))
        else:
            result.append(line)
    return "".join(result)


def _serve_cached(filename: str, request: Request = None) -> Response:
    filepath = PLAYLIST_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=503, detail="Плейлист ещё не загружен, попробуйте позже")

    content = filepath.read_text(encoding="utf-8", errors="replace")

    if request and "kizug.ru" in content:
        server_base = str(request.base_url).rstrip("/")
        content = _rewrite_kizug(content, server_base)

    return Response(content, media_type="application/x-mpegurl",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/tv")
async def redirect_to_tv(request: Request, db: Session = Depends(get_db)):
    tv = db.query(TVSettings).first()
    if not tv or not tv.tv_link:
        raise HTTPException(status_code=404, detail="TV link not set")

    if tv.delivery_type == DeliveryType.CACHED:
        return _serve_cached(MAIN_PLAYLIST, request)

    return RedirectResponse(tv.tv_link)


@router.get("/tv-xxx")
async def redirect_to_tv_xxx(request: Request, db: Session = Depends(get_db)):
    tv = db.query(TVSettings).first()
    if not tv or not tv.tv_link:
        raise HTTPException(status_code=404, detail="TV link not set")

    if tv.delivery_type != DeliveryType.CACHED:
        raise HTTPException(status_code=400, detail="Режим загрузки на сервер не активен")

    if not tv.xxx_link:
        raise HTTPException(status_code=404, detail="Плейлист 18+ не настроен")

    return _serve_cached(XXX_PLAYLIST, request)
