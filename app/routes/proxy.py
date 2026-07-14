import base64
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter()

_HEADERS = {"User-Agent": "VLC/3.0.20 LibVLC/3.0.20"}
_PLAYLIST_TYPES = {
    "application/x-mpegurl",
    "application/vnd.apple.mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
}


def decode_url(token: str) -> str:
    padding = 4 - len(token) % 4
    return base64.urlsafe_b64decode((token + "=" * padding).encode()).decode()


def _encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def _is_playlist(content_type: str, url: str, body: str = "") -> bool:
    ct = content_type.split(";")[0].strip().lower()
    type_match = ct in _PLAYLIST_TYPES or any(url.lower().endswith(ext) for ext in (".m3u", ".m3u8"))
    if not type_match:
        return False
    return body.lstrip().startswith(("#EXTM3U", "#EXT-X-"))


def _rewrite_playlist(content: str, source_url: str, server_base: str) -> str:
    """Rewrite all URLs in m3u8 manifest to go through /proxy."""
    lines = content.splitlines(keepends=True)
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if stripped.startswith("http"):
                absolute = stripped
            else:
                try:
                    absolute = urljoin(source_url, stripped)
                except ValueError:
                    result.append(line)
                    continue
            result.append(f"{server_base}/proxy?url={_encode_url(absolute)}" + ("\n" if line.endswith("\n") else ""))
        else:
            result.append(line)
    return "".join(result)


@router.get("/proxy")
async def proxy_stream(url: str, request: Request):
    try:
        original_url = decode_url(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL token")

    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers=_HEADERS) as client:
            resp = await client.get(original_url)
    except (httpx.RequestError, httpx.InvalidURL) as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    content_type = resp.headers.get("content-type", "")
    final_url = str(resp.url)
    body = resp.text

    if _is_playlist(content_type, original_url, body) or _is_playlist(content_type, final_url, body):
        server_base = str(request.base_url).rstrip("/")
        rewritten = _rewrite_playlist(body, final_url, server_base)
        return Response(rewritten, media_type="application/x-mpegurl")

    return Response(resp.content, media_type=content_type or "application/octet-stream")
