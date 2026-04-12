"""arXiv API client."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

import httpx

from research_os.sources.cache import Cache
from research_os.types import ToolResult

BASE_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


class ArxivClient:
    def __init__(self, http: httpx.Client, cache: Cache) -> None:
        self.http = http
        self.cache = cache
        self._last_request: float = 0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)

    def _request(self, url: str, **params) -> httpx.Response:
        self._rate_limit()
        self._last_request = time.time()
        return self.http.get(url, params=params)

    @staticmethod
    def _parse_entry(entry: ET.Element) -> dict:
        """Parse a single Atom entry into a normalized dict."""
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ")
        abstract = (entry.findtext(f"{ATOM_NS}summary") or "").strip()
        authors = [
            (a.findtext(f"{ATOM_NS}name") or "").strip()
            for a in entry.findall(f"{ATOM_NS}author")
        ]
        published = entry.findtext(f"{ATOM_NS}published") or ""
        year = int(published[:4]) if len(published) >= 4 else None

        # Extract arXiv ID from the entry id URL
        entry_id = entry.findtext(f"{ATOM_NS}id") or ""
        arxiv_id = ""
        match = re.search(r"abs/(.+?)(?:v\d+)?$", entry_id)
        if match:
            arxiv_id = match.group(1)

        # Look for DOI in links
        doi = None
        for link in entry.findall(f"{ATOM_NS}link"):
            href = link.get("href", "")
            if "doi.org" in href:
                doi = href.replace("http://dx.doi.org/", "").replace(
                    "https://doi.org/", ""
                )
                break

        url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else entry_id

        return {
            "source": "arxiv",
            "external_id": arxiv_id,
            "title": title,
            "authors": authors,
            "year": year,
            "abstract": abstract,
            "url": url,
            "doi": doi,
            "citation_count": None,
        }

    def search(self, query: str, max_results: int = 20) -> ToolResult:
        cached = self.cache.get("arxiv", query, max_results)
        if cached is not None:
            return ToolResult(ok=True, data=cached)

        resp = self._request(
            BASE_URL,
            search_query=f"all:{query}",
            start=0,
            max_results=max_results,
            sortBy="relevance",
            sortOrder="descending",
        )
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"arXiv search failed ({resp.status_code}): {resp.text[:200]}",
                retryable=True,
            )

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            return ToolResult(ok=False, error=f"arXiv XML parse error: {e}")

        entries = root.findall(f"{ATOM_NS}entry")
        results = [self._parse_entry(e) for e in entries]
        # Filter out empty entries (arXiv sometimes returns placeholder entries)
        results = [r for r in results if r["title"]]
        self.cache.put("arxiv", query, max_results, results)
        return ToolResult(ok=True, data=results)

    def get_paper(self, arxiv_id: str) -> ToolResult:
        """Fetch metadata for a single paper by arXiv ID."""
        # Strip version suffix for the query
        clean_id = re.sub(r"v\d+$", "", arxiv_id)
        resp = self._request(BASE_URL, id_list=clean_id, max_results=1)
        if resp.status_code != 200:
            return ToolResult(
                ok=False,
                error=f"arXiv get_paper failed ({resp.status_code})",
                retryable=True,
            )
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            return ToolResult(ok=False, error=f"arXiv XML parse error: {e}")

        entries = root.findall(f"{ATOM_NS}entry")
        if not entries:
            return ToolResult(ok=False, error=f"No paper found for arXiv ID {arxiv_id}")
        return ToolResult(ok=True, data=self._parse_entry(entries[0]))
