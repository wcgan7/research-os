"""Paper full-text extraction for research-os.

Ported from curious-now's extractors. Supports arXiv (HTML, PDF, e-print)
and DOI-based open-access lookup (CrossRef, OpenAlex, Unpaywall).

Public API:
    fetch_paper_text(*, arxiv_id=None, doi=None, url=None, config=None)
        -> (text, source_name) or (None, None)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from research_os.sources.paper_text.arxiv import (
    fetch_arxiv_abstract,
    select_best_arxiv_full_text,
)
from research_os.sources.paper_text.doi import (
    fetch_crossref_abstract,
    fetch_crossref_oa_candidates,
    fetch_openalex_abstract,
    fetch_openalex_oa_candidates,
    fetch_unpaywall_candidates,
    try_oa_candidates,
)


@dataclass
class PaperTextConfig:
    unpaywall_email: str | None = None
    http_timeout_s: float = 12.0
    max_full_text_chars: int = 120_000
    min_fulltext_chars: int = 2_500
    min_fulltext_words: int = 400


def fetch_paper_text(
    *,
    arxiv_id: str | None = None,
    doi: str | None = None,
    url: str | None = None,
    config: PaperTextConfig | None = None,
) -> tuple[str | None, str | None]:
    """Fetch the best available full text for a paper.

    Tries in order:
      1. arXiv (HTML → PDF → e-print), if arxiv_id given
      2. DOI-based OA lookup (Unpaywall → OpenAlex → CrossRef), if doi given
      3. Returns (None, None) for URL-only — agent should use WebFetch

    Returns (text, source_name) or (None, None).
    """
    cfg = config or PaperTextConfig()

    # 1. arXiv full text
    if arxiv_id:
        aid = arxiv_id.strip()
        text, source = select_best_arxiv_full_text(aid)
        if text:
            return text, source

    # 2. DOI-based OA lookup
    if doi:
        d = doi.strip()

        # Unpaywall
        if cfg.unpaywall_email:
            candidates = fetch_unpaywall_candidates(d, email=cfg.unpaywall_email)
            text, source, _ = try_oa_candidates(candidates)
            if text:
                return text, source

        # OpenAlex
        candidates = fetch_openalex_oa_candidates(d)
        text, source, _ = try_oa_candidates(candidates)
        if text:
            return text, source

        # CrossRef
        candidates = fetch_crossref_oa_candidates(d)
        text, source, _ = try_oa_candidates(candidates)
        if text:
            return text, source

    return None, None
