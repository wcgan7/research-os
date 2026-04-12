"""OpenAlex API client."""

from __future__ import annotations

import time

import httpx

from research_os.sources.cache import Cache
from research_os.types import ToolResult

BASE_URL = "https://api.openalex.org"


class OpenAlexClient:
    def __init__(self, http: httpx.Client, cache: Cache) -> None:
        self.http = http
        self.cache = cache
        self._last_request: float = 0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)

    def _request(self, url: str, **params) -> httpx.Response:
        self._rate_limit()
        self._last_request = time.time()
        params["mailto"] = "research-os@example.com"
        return self.http.get(url, params=params)

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return None
        # {word: [pos1, pos2, ...]} → ordered list of words
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in word_positions)

    @staticmethod
    def _normalize(work: dict) -> dict:
        """Normalize an OpenAlex work dict to our standard shape."""
        authorships = work.get("authorships") or []
        authors = []
        for a in authorships:
            author = a.get("author") or {}
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        doi_url = work.get("doi") or ""
        doi = doi_url.replace("https://doi.org/", "") if doi_url else None

        abstract = OpenAlexClient._reconstruct_abstract(
            work.get("abstract_inverted_index")
        )

        return {
            "source": "openalex",
            "external_id": work.get("id", ""),
            "title": work.get("title") or "",
            "authors": authors,
            "year": work.get("publication_year"),
            "abstract": abstract,
            "url": work.get("primary_location", {}).get("landing_page_url")
            or work.get("id", ""),
            "doi": doi,
            "citation_count": work.get("cited_by_count"),
        }

    def search(self, query: str, limit: int = 20) -> ToolResult:
        cached = self.cache.get("openalex", query, limit)
        if cached is not None:
            return ToolResult(ok=True, data=cached)

        resp = self._request(
            f"{BASE_URL}/works",
            search=query,
            per_page=limit,
        )
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"OpenAlex search failed ({resp.status_code}): {resp.text[:200]}",
                retryable=resp.status_code in (429, 500, 502, 503),
            )
        works = resp.json().get("results") or []
        results = [self._normalize(w) for w in works]
        self.cache.put("openalex", query, limit, results)
        return ToolResult(ok=True, data=results)

    def get_paper(self, openalex_id: str) -> ToolResult:
        """Fetch a single work by OpenAlex ID."""
        url = openalex_id if openalex_id.startswith("http") else f"{BASE_URL}/works/{openalex_id}"
        resp = self._request(url)
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"OpenAlex get_paper failed ({resp.status_code}): {resp.text[:200]}",
                retryable=resp.status_code in (429, 500, 502, 503),
            )
        return ToolResult(ok=True, data=self._normalize(resp.json()))
