"""Web search source using DuckDuckGo.

Finds papers that academic APIs miss by searching the open web.
Results are normalized to the same format as other sources.
"""

from __future__ import annotations

import re
import time
from typing import Any

from research_os.types import ToolResult


class WebSearchClient:
    """Search the web for academic papers using DuckDuckGo."""

    def __init__(self) -> None:
        self._last_request = 0.0
        self._min_delay = 3.0  # seconds between requests (DuckDuckGo rate limits)

    def _wait(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self._min_delay:
            time.sleep(self._min_delay - elapsed)
        self._last_request = time.time()

    def search(self, query: str, max_results: int = 20) -> ToolResult:
        """Search the web for papers matching the query.

        The query is used as-is — the agent is responsible for crafting
        good queries. This allows both targeted (paper name) and broad searches.
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return ToolResult(
                ok=False,
                error="duckduckgo_search not installed. Run: pip install duckduckgo_search",
                retryable=False,
            )

        self._wait()

        try:
            import warnings
            warnings.filterwarnings("ignore", message=".*renamed.*")
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    paper = self._parse_result(r)
                    if paper:
                        results.append(paper)

            return ToolResult(ok=True, data=results)
        except Exception as e:
            return ToolResult(ok=False, error=f"Web search error: {e}", retryable=True)

    def _parse_result(self, result: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a DuckDuckGo result into our paper format."""
        title = result.get("title", "")
        url = result.get("href", "")
        body = result.get("body", "")

        if not title:
            return None

        # Try to extract arXiv ID from URL
        external_id = ""
        arxiv_match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", url)
        if arxiv_match:
            external_id = arxiv_match.group(1)

        # Try to extract DOI from URL
        doi = None
        doi_match = re.search(r"doi\.org/(10\.\d{4,}/[^\s]+)", url)
        if doi_match:
            doi = doi_match.group(1)

        # Try to extract year from title or body
        year = None
        year_match = re.search(r"\b(20[12]\d)\b", title + " " + body)
        if year_match:
            year = int(year_match.group(1))

        return {
            "title": _clean_title(title),
            "authors": [],  # Not reliably available from web search
            "year": year,
            "abstract": body[:500] if body else None,
            "url": url,
            "doi": doi,
            "external_id": external_id,
            "source": "web_search",
            "citation_count": None,
        }


def _clean_title(title: str) -> str:
    """Remove common suffixes from web search titles."""
    # Remove site names appended after | or -
    for sep in [" | ", " - arXiv", " - Semantic Scholar", " :: ", " - OpenReview"]:
        if sep in title:
            title = title[:title.index(sep)]
    return title.strip()
