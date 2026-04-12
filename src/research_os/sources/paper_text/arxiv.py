"""ArXiv-specific full text fetching: HTML, PDF, e-print, abstract.

Tries all three full-text sources and picks the best by quality score.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

from research_os.sources.paper_text.cleaning import clean_text
from research_os.sources.paper_text.html import extract_arxiv_html_body_text
from research_os.sources.paper_text.http import http_get
from research_os.sources.paper_text.latex import fetch_arxiv_eprint_full_text
from research_os.sources.paper_text.pdf import fetch_pdf_text
from research_os.sources.paper_text.scoring import (
    is_fulltext_quality_sufficient,
    score_fulltext_quality,
)

_SOURCE_QUALITY_BONUS: dict[str, float] = {
    "arxiv_html": 0.18,
    "arxiv_pdf": 0.12,
    "arxiv_eprint": 0.08,
}


def fetch_arxiv_abstract(arxiv_id: str) -> str | None:
    """Fetch abstract from arXiv API."""
    url = f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}"
    resp = http_get(url)
    if resp.status_code != 200:
        return None
    try:
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None
        summary = entry.find("atom:summary", ns)
        text = summary.text if summary is not None else None
        return clean_text(text)
    except ET.ParseError:
        return None


def fetch_arxiv_html_full_text(arxiv_id: str) -> str | None:
    """Fetch full text from arXiv HTML rendering."""
    html_url = f"https://arxiv.org/html/{quote(arxiv_id)}"
    resp = http_get(html_url, timeout_s=20.0)
    if resp.status_code != 200:
        return None
    content_type = (resp.headers.get("content-type") or "").lower()
    if "html" not in content_type:
        return None
    text = extract_arxiv_html_body_text(resp.text)
    if not text or not is_fulltext_quality_sufficient(text):
        return None
    return text


def fetch_arxiv_pdf_full_text(arxiv_id: str) -> str | None:
    """Fetch full text from arXiv PDF."""
    pdf_url = f"https://arxiv.org/pdf/{quote(arxiv_id)}.pdf"
    return fetch_pdf_text(pdf_url, http_get=lambda u: http_get(u, timeout_s=20.0))


def select_best_arxiv_full_text(arxiv_id: str) -> tuple[str | None, str | None]:
    """Try HTML, PDF, and e-print; return best by quality score.

    Returns (text, source_name) or (None, None).
    """
    candidates: list[tuple[str, str]] = []
    html_text = fetch_arxiv_html_full_text(arxiv_id)
    if html_text:
        candidates.append(("arxiv_html", html_text))
    pdf_text = fetch_arxiv_pdf_full_text(arxiv_id)
    if pdf_text:
        candidates.append(("arxiv_pdf", pdf_text))
    eprint_text = fetch_arxiv_eprint_full_text(arxiv_id)
    if eprint_text:
        candidates.append(("arxiv_eprint", eprint_text))
    if not candidates:
        return None, None

    best_source: str | None = None
    best_text: str | None = None
    best_score = -1.0
    for source, text in candidates:
        score = score_fulltext_quality(text) + _SOURCE_QUALITY_BONUS.get(source, 0.0)
        if score > best_score:
            best_score = score
            best_source = source
            best_text = text
    return best_text, best_source
