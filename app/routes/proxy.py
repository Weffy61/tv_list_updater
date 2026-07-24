import base64
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.db import get_db
from core.stats import record_ip, real_ip
from models.tv_settings import TVSettings

router = APIRouter()

_HEADERS = {"User-Agent": "Televizo (Linux; Android 11)"}
_cache: dict[str, tuple[str, float]] = {}  # url → (final_url, expires_at)


def decode_url(token: str) -> str:
    padding = 4 - len(token) % 4
    return base64.urlsafe_b64decode((token + "=" * padding).encode()).decode()


def _encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def clear_cache() -> None:
    _cache.clear()


@router.get("/proxy")
async def proxy_stream(url: str, request: Request, db: Session = Depends(get_db)):
    record_ip(real_ip(request))
    try:
        original_url = decode_url(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL token")

    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")

    cached = _cache.get(original_url)
    if cached and time.monotonic() < cached[1]:
        return RedirectResponse(url=cached[0], status_code=302)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=_HEADERS) as client:
            async with client.stream("GET", original_url) as resp:
                final_url = str(resp.url)
    except (httpx.RequestError, httpx.InvalidURL) as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    tv = db.query(TVSettings).first()
    ttl_seconds = (tv.update_interval_hours if tv else 6) * 3600
    _cache[original_url] = (final_url, time.monotonic() + ttl_seconds)

    return RedirectResponse(url=final_url, status_code=302)