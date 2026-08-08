"""Tiny in-memory rate limiter (fixed window per IP + bucket).

No dependency, no Redis — fine for a single-instance FastAPI service. Protects
the endpoints an attacker would hammer: login (brute force) and signup /
assessment (which spend LLM/embedding budget). If the service is ever scaled to
multiple workers, swap the backing store for Redis; the call sites don't change.
"""
from __future__ import annotations

import threading
import time

_WINDOWS: dict[tuple[str, str], list] = {}   # (bucket, ip) -> [count, window_start]
_LOCK = threading.Lock()
_last_prune = 0.0


def client_ip(request) -> str:
    """Real client IP behind Render's proxy (first X-Forwarded-For hop)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def allow(bucket: str, ip: str, limit: int, window: float) -> bool:
    """True if this (bucket, ip) is under `limit` requests in the current window."""
    now = time.time()
    with _LOCK:
        _prune(now)
        key = (bucket, ip)
        entry = _WINDOWS.get(key)
        if entry is None or now - entry[1] >= window:
            _WINDOWS[key] = [1, now]
            return True
        if entry[0] >= limit:
            return False
        entry[0] += 1
        return True


def _prune(now: float) -> None:
    """Drop windows older than an hour so the dict can't grow unbounded."""
    global _last_prune
    if now - _last_prune < 300:
        return
    _last_prune = now
    stale = [k for k, v in _WINDOWS.items() if now - v[1] > 3600]
    for k in stale:
        _WINDOWS.pop(k, None)


def reset() -> None:
    """Clear all state (tests)."""
    with _LOCK:
        _WINDOWS.clear()
