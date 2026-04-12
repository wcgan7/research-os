"""File-based API response cache with source-specific TTLs."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

TTLS: dict[str, int] = {
    "arxiv": 86400,          # 24 hours
    "semantic_scholar": 259200,  # 3 days
    "openalex": 259200,      # 3 days
}


class Cache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, source: str, query: str, limit: int) -> str:
        raw = f"{source}:{query}:{limit}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, source: str, query: str, limit: int) -> list[dict] | None:
        key = self._key(source, query, limit)
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        ttl = TTLS.get(source, 86400)
        if time.time() - data.get("timestamp", 0) > ttl:
            path.unlink(missing_ok=True)
            return None
        return data.get("results")

    def put(self, source: str, query: str, limit: int, results: list[dict]) -> None:
        key = self._key(source, query, limit)
        path = self._path(key)
        path.write_text(
            json.dumps({"timestamp": time.time(), "source": source, "results": results})
        )

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)
