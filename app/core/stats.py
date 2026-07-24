import time
from collections import defaultdict

import httpx
from fastapi import Request

_DAY = 86400
_WEEK = 7 * _DAY
_MONTH = 30 * _DAY

# (ip, timestamp) — для уникальных пользователей за день/неделю/месяц
_visits: list[tuple[str, float]] = []

# (ip, channel_name, timestamp) — все обращения к прокси, храним 30 дней
_events: list[tuple[str, str, float]] = []

_url_to_channel: dict[str, str] = {}   # kizug_url → channel_name
_ip_country: dict[str, str] = {}       # ip → country (кэш)


def real_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def record_ip(ip: str) -> None:
    now = time.time()
    _visits.append((ip, now))
    cutoff = now - _MONTH
    while _visits and _visits[0][1] < cutoff:
        _visits.pop(0)


def record_channel(original_url: str, ip: str) -> None:
    name = _url_to_channel.get(original_url)
    if not name:
        return
    now = time.time()
    _events.append((ip, name, now))
    cutoff = now - _MONTH
    while _events and _events[0][2] < cutoff:
        _events.pop(0)


def set_url_channel_map(mapping: dict[str, str]) -> None:
    _url_to_channel.clear()
    _url_to_channel.update(mapping)


def _count_unique(since: float) -> int:
    return len({ip for ip, ts in _visits if ts >= since})


def stats() -> dict[str, int]:
    now = time.time()
    return {
        "day": _count_unique(now - _DAY),
        "week": _count_unique(now - _WEEK),
        "month": _count_unique(now - _MONTH),
    }


def top_channels(n: int = 50) -> list[tuple[str, int]]:
    # 1 IP + 1 канал + 1 день = 1 открытие
    channel_unique: dict[str, set] = defaultdict(set)
    for ip, channel, ts in _events:
        day = int(ts // _DAY)
        channel_unique[channel].add((ip, day))
    result = [(ch, len(s)) for ch, s in channel_unique.items()]
    return sorted(result, key=lambda x: x[1], reverse=True)[:n]


def top_ips(n: int = 50) -> list[dict]:
    ip_counts: dict[str, int] = defaultdict(int)
    for ip, _, _ in _events:
        ip_counts[ip] += 1
    sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:n]
    _fetch_countries([ip for ip, _ in sorted_ips])
    return [
        {"ip": ip, "count": count, "country": _ip_country.get(ip, "—")}
        for ip, count in sorted_ips
    ]


def _fetch_countries(ips: list[str]) -> None:
    unknown = [ip for ip in ips if ip not in _ip_country]
    if not unknown:
        return
    try:
        resp = httpx.post(
            "http://ip-api.com/batch",
            json=[{"query": ip, "fields": "country"} for ip in unknown[:100]],
            timeout=5,
        )
        for ip, result in zip(unknown, resp.json()):
            _ip_country[ip] = result.get("country") or "—"
    except Exception:
        for ip in unknown:
            _ip_country[ip] = "—"
