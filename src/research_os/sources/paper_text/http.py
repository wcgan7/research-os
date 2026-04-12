"""Retry-aware HTTP client and domain throttling."""

from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

_DOMAIN_LAST_FETCH: dict[str, float] = {}


def http_get(url: str, *, timeout_s: float = 12.0) -> httpx.Response:
    """GET with retries and exponential backoff."""
    headers = {"User-Agent": "research-os/0.1 (+paper-text)"}
    timeout = httpx.Timeout(timeout_s, connect=5.0)
    backoff_s = 1.0
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(follow_redirects=True, headers=headers, timeout=timeout) as client:
                return client.get(url)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(backoff_s)
            backoff_s *= 2
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unreachable")


def throttle_domain(url: str, min_interval_s: float = 1.0) -> None:
    """Sleep if we fetched from the same domain too recently."""
    domain = urlparse(url).netloc.lower()
    now = time.monotonic()
    last = _DOMAIN_LAST_FETCH.get(domain)
    if last is not None:
        wait = min_interval_s - (now - last)
        if wait > 0:
            time.sleep(wait)
    _DOMAIN_LAST_FETCH[domain] = time.monotonic()
