"""Quality scoring and sufficiency checks for extracted paper text."""

from __future__ import annotations

import re

_MIN_FULLTEXT_CHARS = 2_500
_MIN_FULLTEXT_WORDS = 400


def score_fulltext_quality(text: str | None) -> float:
    """Score text quality on a 0.0–1.0 scale."""
    if not text:
        return 0.0
    words = len(text.split())
    chars = len(text)
    lower = text.lower()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    line_count = len(lines)
    section_hits = sum(
        1
        for token in (
            "introduction",
            "background",
            "method",
            "methods",
            "results",
            "discussion",
            "conclusion",
            "references",
        )
        if token in lower
    )
    caption_hits = sum(lower.count(token) for token in ("figure", "fig.", "table"))
    short_noise_lines = sum(1 for ln in lines if len(ln) <= 2)
    long_glued_tokens = len(re.findall(r"\b[A-Za-z]{20,}\b", text))
    control_chars = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\t\r")
    pipe_table_lines = sum(1 for ln in lines if ln.count("|") >= 2)
    table_marker_hits = text.count("Table (PDF p.")

    abstract_idx = -1
    for idx, ln in enumerate(lines[:260]):
        if ln.lower() == "abstract":
            abstract_idx = idx
            break
    pre_abstract_affiliation_hits = 0
    if abstract_idx > 10:
        pre_lines = lines[:abstract_idx]
        for ln in pre_lines:
            if re.search(
                r"\b(department|university|institute|center|centre|observatory|fellow|preprint)\b",
                ln,
                re.IGNORECASE,
            ):
                pre_abstract_affiliation_hits += 1
            elif "@" in ln:
                pre_abstract_affiliation_hits += 1
            elif re.match(r"^\[?\d+\]?\s", ln):
                pre_abstract_affiliation_hits += 1

    score = 0.0
    score += min(chars / 18_000.0, 1.0) * 0.35
    score += min(words / 2_200.0, 1.0) * 0.35
    score += min(section_hits / 5.0, 1.0) * 0.30
    score -= min(caption_hits / 120.0, 0.20)
    score -= min((short_noise_lines / max(1, line_count)) * 1.8, 0.22)
    score -= min((long_glued_tokens / max(1, words)) * 8.0, 0.22)
    score -= min(control_chars / 40.0, 0.18)
    score -= min((pipe_table_lines / max(1, line_count)) * 1.5, 0.15)
    score -= min(table_marker_hits / 20.0, 0.10)
    if pre_abstract_affiliation_hits >= 4:
        score -= 0.12
    return max(0.0, min(1.0, score))


def is_fulltext_quality_sufficient(text: str | None) -> bool:
    """Check if extracted text meets minimum quality thresholds."""
    if not text:
        return False
    if score_fulltext_quality(text) < 0.4:
        return False
    words = len(text.split())
    chars = len(text)
    if chars < _MIN_FULLTEXT_CHARS or words < _MIN_FULLTEXT_WORDS:
        return False
    lower = text.lower()
    section_hits = sum(
        1
        for token in (
            "introduction",
            "method",
            "results",
            "discussion",
            "conclusion",
            "references",
        )
        if token in lower
    )
    return section_hits >= 2
