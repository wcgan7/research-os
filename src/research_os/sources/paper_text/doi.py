"""DOI-based open-access full text lookup via CrossRef, OpenAlex, and Unpaywall."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from research_os.sources.paper_text.cleaning import clean_text
from research_os.sources.paper_text.http import http_get
from research_os.sources.paper_text.pdf import fetch_pdf_text


@dataclass(frozen=True)
class OACandidate:
    url: str
    source: str
    is_pdf: bool
    open_access_ok: bool
    license_name: str | None


# ---------------------------------------------------------------------------
# CrossRef
# ---------------------------------------------------------------------------


def fetch_crossref_abstract(doi: str) -> str | None:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    resp = http_get(url)
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    message = data.get("message", {}) if isinstance(data, dict) else {}
    return clean_text(message.get("abstract"))


def fetch_crossref_oa_candidates(doi: str) -> list[OACandidate]:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    resp = http_get(url)
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    message = data.get("message", {}) if isinstance(data, dict) else {}
    if not isinstance(message, dict):
        return []

    licenses = message.get("license")
    license_name: str | None = None
    open_access_ok = False
    if isinstance(licenses, list) and licenses:
        first = licenses[0]
        if isinstance(first, dict):
            lic_url = first.get("URL")
            if isinstance(lic_url, str) and lic_url.strip():
                license_name = lic_url.strip()
                open_access_ok = True

    candidates: list[OACandidate] = []
    links = message.get("link")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            href = link.get("URL")
            if not isinstance(href, str) or not href.strip():
                continue
            ctype = str(link.get("content-type") or "").lower()
            if "pdf" in ctype or href.lower().endswith(".pdf"):
                candidates.append(
                    OACandidate(
                        url=href.strip(),
                        source="crossref_pdf",
                        is_pdf=True,
                        open_access_ok=open_access_ok,
                        license_name=license_name,
                    )
                )

    landing = message.get("URL")
    if isinstance(landing, str) and landing.strip():
        candidates.append(
            OACandidate(
                url=landing.strip(),
                source="crossref_landing",
                is_pdf=False,
                open_access_ok=open_access_ok,
                license_name=license_name,
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------


def _reconstruct_openalex_abstract(inverted_index: dict[str, list[int]]) -> str | None:
    if not inverted_index:
        return None
    pairs: list[tuple[int, str]] = []
    for token, positions in inverted_index.items():
        for pos in positions:
            pairs.append((int(pos), token))
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[0])
    text = " ".join(token for _, token in pairs)
    return clean_text(text)


def fetch_openalex_abstract(doi: str) -> str | None:
    url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
    resp = http_get(url)
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    inv = data.get("abstract_inverted_index")
    if not isinstance(inv, dict):
        return None
    casted: dict[str, list[int]] = {}
    for k, v in inv.items():
        if isinstance(k, str) and isinstance(v, list):
            casted[k] = [int(x) for x in v if isinstance(x, int)]
    return _reconstruct_openalex_abstract(casted)


def fetch_openalex_oa_candidates(doi: str) -> list[OACandidate]:
    url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
    resp = http_get(url)
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    if not isinstance(data, dict):
        return []

    is_oa = bool(data.get("is_oa"))
    oa = data.get("open_access") if isinstance(data.get("open_access"), dict) else {}
    oa_license = oa.get("license") if isinstance(oa, dict) else None
    license_name = str(oa_license) if isinstance(oa_license, str) and oa_license else None

    locations: list[dict[str, Any]] = []
    for key in ("best_oa_location", "primary_location"):
        loc = data.get(key)
        if isinstance(loc, dict):
            locations.append(loc)
    oa_locations = data.get("locations")
    if isinstance(oa_locations, list):
        for loc in oa_locations:
            if isinstance(loc, dict):
                locations.append(loc)

    candidates: list[OACandidate] = []
    for loc in locations:
        pdf_url = loc.get("pdf_url") or loc.get("url_for_pdf")
        if isinstance(pdf_url, str) and pdf_url.strip():
            candidates.append(
                OACandidate(
                    url=pdf_url.strip(),
                    source="openalex_pdf",
                    is_pdf=True,
                    open_access_ok=is_oa,
                    license_name=license_name,
                )
            )
        landing_url = (
            loc.get("landing_page_url")
            or loc.get("url")
            or loc.get("url_for_landing_page")
        )
        if isinstance(landing_url, str) and landing_url.strip():
            candidates.append(
                OACandidate(
                    url=landing_url.strip(),
                    source="openalex_landing",
                    is_pdf=False,
                    open_access_ok=is_oa,
                    license_name=license_name,
                )
            )
    return candidates


# ---------------------------------------------------------------------------
# Unpaywall
# ---------------------------------------------------------------------------


def fetch_unpaywall_candidates(doi: str, *, email: str) -> list[OACandidate]:
    """Fetch OA candidates from Unpaywall."""
    url = f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email={quote(email)}"
    resp = http_get(url)
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    return _parse_unpaywall_candidates(data)


def _parse_unpaywall_candidates(data: dict[str, Any]) -> list[OACandidate]:
    is_oa = bool(data.get("is_oa"))
    locations: list[dict[str, Any]] = []

    best = data.get("best_oa_location")
    if isinstance(best, dict):
        locations.append(best)

    extras = data.get("oa_locations")
    if isinstance(extras, list):
        for loc in extras:
            if isinstance(loc, dict):
                locations.append(loc)

    candidates: list[OACandidate] = []
    seen: set[tuple[str, str]] = set()
    for loc in locations:
        license_name = str(loc.get("license")) if isinstance(loc.get("license"), str) else None

        pdf_url = loc.get("url_for_pdf")
        if isinstance(pdf_url, str) and pdf_url.strip():
            key = (pdf_url.strip(), "pdf")
            if key not in seen:
                seen.add(key)
                candidates.append(
                    OACandidate(
                        url=pdf_url.strip(),
                        source="unpaywall_pdf",
                        is_pdf=True,
                        open_access_ok=is_oa,
                        license_name=license_name,
                    )
                )

        landing_url = loc.get("url_for_landing_page")
        if isinstance(landing_url, str) and landing_url.strip():
            key = (landing_url.strip(), "landing")
            if key not in seen:
                seen.add(key)
                candidates.append(
                    OACandidate(
                        url=landing_url.strip(),
                        source="unpaywall_landing",
                        is_pdf=False,
                        open_access_ok=is_oa,
                        license_name=license_name,
                    )
                )

    return candidates


# ---------------------------------------------------------------------------
# Try OA candidates
# ---------------------------------------------------------------------------


def try_oa_candidates(candidates: list[OACandidate]) -> tuple[str | None, str | None, str | None]:
    """Try PDF candidates first, then landing pages. Returns (text, source, license)."""
    pdf_candidates = [c for c in candidates if c.is_pdf]
    # Landing pages skipped — agent should use WebFetch for those

    for c in pdf_candidates:
        if not c.open_access_ok:
            continue
        text = fetch_pdf_text(c.url, http_get=lambda u: http_get(u, timeout_s=20.0))
        if text:
            return text, c.source, c.license_name

    return None, None, None
