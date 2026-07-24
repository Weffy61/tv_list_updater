import time

_DAY = 86400
_WEEK = 7 * _DAY
_MONTH = 30 * _DAY

_visits: list[tuple[str, float]] = []  # (ip, timestamp)


def record_ip(ip: str) -> None:
    now = time.time()
    _visits.append((ip, now))
    cutoff = now - _MONTH
    while _visits and _visits[0][1] < cutoff:
        _visits.pop(0)


def _count_unique(since: float) -> int:
    return len({ip for ip, ts in _visits if ts >= since})


def stats() -> dict[str, int]:
    now = time.time()
    return {
        "day": _count_unique(now - _DAY),
        "week": _count_unique(now - _WEEK),
        "month": _count_unique(now - _MONTH),
    }
