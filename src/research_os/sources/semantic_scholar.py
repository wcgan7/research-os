"""Semantic Scholar API client."""

from __future__ import annotations

import fcntl
import time
from pathlib import Path

import httpx

from research_os.sources.cache import Cache
from research_os.types import ToolResult

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,authors,year,abstract,url,citationCount,externalIds"

# Cross-process rate limiting via file lock + timestamp
_LOCK_PATH = Path.home() / ".research-os" / ".s2_rate_lock"
_TS_PATH = Path.home() / ".research-os" / ".s2_last_request"


def _cross_process_rate_limit(delay: float) -> None:
    """Ensure minimum delay between S2 requests across all processes."""
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOCK_PATH, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            last = float(_TS_PATH.read_text().strip()) if _TS_PATH.exists() else 0
        except (ValueError, OSError):
            last = 0
        elapsed = time.time() - last
        if elapsed < delay:
            time.sleep(delay - elapsed)
        _TS_PATH.write_text(str(time.time()))


class SemanticScholarClient:
    def __init__(
        self,
        http: httpx.Client,
        cache: Cache,
        api_key: str | None = None,
    ) -> None:
        self.http = http
        self.cache = cache
        self.api_key = api_key

    def _headers(self) -> dict:
        if self.api_key:
            return {"x-api-key": self.api_key}
        return {}

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a request with cross-process rate limiting and retry on 429."""
        delay = 0.1 if self.api_key else 1.0
        _cross_process_rate_limit(delay)
        for attempt in range(5):
            resp = self.http.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code == 429 and attempt < 4:
                wait = 3 * (2 ** attempt)  # 3, 6, 12, 24 seconds
                time.sleep(wait)
                _cross_process_rate_limit(delay)
                continue
            return resp
        return resp  # type: ignore[possibly-undefined]

    def _normalize(self, raw: dict) -> dict:
        """Normalize an S2 paper dict to our standard shape."""
        authors = [a.get("name", "") for a in (raw.get("authors") or [])]
        ext_ids = raw.get("externalIds") or {}
        # Prefer arXiv URL if available (helps fetch_paper_text)
        url = raw.get("url")
        arxiv_id = ext_ids.get("ArXiv")
        if arxiv_id and not (url and "arxiv.org" in url):
            url = f"https://arxiv.org/abs/{arxiv_id}"
        return {
            "source": "semantic_scholar",
            "external_id": raw.get("paperId", ""),
            "title": raw.get("title", ""),
            "authors": authors,
            "year": raw.get("year"),
            "abstract": raw.get("abstract"),
            "url": url,
            "doi": ext_ids.get("DOI"),
            "citation_count": raw.get("citationCount"),
        }

    def search(self, query: str, limit: int = 20) -> ToolResult:
        cached = self.cache.get("semantic_scholar", query, limit)
        if cached is not None:
            return ToolResult(ok=True, data=cached)

        resp = self._request(
            "GET",
            f"{BASE_URL}/paper/search",
            params={"query": query, "limit": limit, "fields": FIELDS},
        )
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"S2 search failed ({resp.status_code}): {resp.text[:200]}",
                retryable=resp.status_code in (429, 500, 502, 503),
            )
        data = resp.json().get("data") or []
        results = [self._normalize(p) for p in data]
        self.cache.put("semantic_scholar", query, limit, results)
        return ToolResult(ok=True, data=results)

    def get_paper(self, paper_id: str) -> ToolResult:
        resp = self._request(
            "GET",
            f"{BASE_URL}/paper/{paper_id}",
            params={"fields": FIELDS},
        )
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"S2 get_paper failed ({resp.status_code}): {resp.text[:200]}",
                retryable=resp.status_code in (429, 500, 502, 503),
            )
        return ToolResult(ok=True, data=self._normalize(resp.json()))

    def get_citations(self, paper_id: str, limit: int = 50) -> ToolResult:
        """Get papers that cite this paper (forward citations)."""
        resp = self._request(
            "GET",
            f"{BASE_URL}/paper/{paper_id}/citations",
            params={"limit": limit, "fields": FIELDS},
        )
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"S2 get_citations failed ({resp.status_code}): {resp.text[:200]}",
                retryable=resp.status_code in (429, 500, 502, 503),
            )
        raw_cits = resp.json().get("data") or []
        results = []
        for cit in raw_cits:
            citing = cit.get("citingPaper")
            if citing and citing.get("title"):
                results.append(self._normalize(citing))
        return ToolResult(ok=True, data=results)

    def get_references(self, paper_id: str, limit: int = 50) -> ToolResult:
        resp = self._request(
            "GET",
            f"{BASE_URL}/paper/{paper_id}/references",
            params={"limit": limit, "fields": FIELDS},
        )
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"S2 get_references failed ({resp.status_code}): {resp.text[:200]}",
                retryable=resp.status_code in (429, 500, 502, 503),
            )
        raw_refs = resp.json().get("data") or []
        results = []
        for ref in raw_refs:
            cited = ref.get("citedPaper")
            if cited and cited.get("title"):
                results.append(self._normalize(cited))
        return ToolResult(ok=True, data=results)
