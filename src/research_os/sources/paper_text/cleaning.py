"""Text normalization and cleaning pipeline for extracted paper text.

Ported from curious-now. Applies 9+ sequential transforms to clean up
artifacts from PDF/HTML/LaTeX extraction.
"""

from __future__ import annotations

import html as html_mod
import re
import unicodedata

_MAX_FULL_TEXT_CHARS = 120_000
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_YEAR_RE = re.compile(r"^(19|20)\d{2}[a-z]?$")
_MATH_TOKEN_RE = re.compile(
    r"^[A-Za-z0-9_{}^\\()+\-*=.,|∣∈Σ⊕→≤≥⋅×τσℋℳ𝒩𝒜𝒟\[\]\s]+$"
)


def clean_text(value: str | None) -> str | None:
    """Basic text cleanup: unescape HTML, strip tags, normalize whitespace."""
    if not value:
        return None
    text = html_mod.unescape(value).replace("\x00", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return text[:_MAX_FULL_TEXT_CHARS]


def compact_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_full_text(value: str | None) -> str | None:
    """Comprehensive text cleaning pipeline with normalization."""
    if not value:
        return None
    text = html_mod.unescape(value).replace("\x00", " ").replace("\r", "\n")
    text = re.sub(r"\u00a0", " ", text)
    looks_like_html = bool(
        re.search(
            r"<\s*(html|body|main|article|div|p|span|h[1-6]|table|tr|td|th|script|style)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(r"</\s*[a-zA-Z][^>]*>", text)
    )
    if looks_like_html:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)

    normalized_lines = _normalize_extracted_lines(text.split("\n"))

    out = "\n".join(normalized_lines).strip()
    if not out:
        return None
    return out[:_MAX_FULL_TEXT_CHARS]


# ---------------------------------------------------------------------------
# Line-level transforms
# ---------------------------------------------------------------------------


def _normalize_extracted_lines(lines: list[str]) -> list[str]:
    processed = [unicodedata.normalize("NFKC", _ZERO_WIDTH_RE.sub("", ln)) for ln in lines]
    processed = _drop_early_duplicate_lines(processed)
    processed = _stitch_citation_lines(processed)
    processed = _stitch_math_spill_lines(processed)
    processed = _dedupe_adjacent_latex_unicode(processed)
    processed = _reflow_inline_fragments(processed)
    processed = _merge_section_number_headings(processed)
    processed = _merge_leading_punctuation_lines(processed)
    processed = _dedupe_adjacent_semantic_repeats(processed)
    processed = _drop_visual_legend_artifacts(processed)

    normalized: list[str] = []
    blank_run = 0
    for line in processed:
        c = re.sub(r"[ \t]+", " ", line).strip()
        if not c:
            blank_run += 1
            if blank_run <= 1:
                normalized.append("")
            continue
        blank_run = 0
        c = _normalize_inline_tex_tokens(c)
        normalized.append(c)
    return normalized


def _drop_early_duplicate_lines(lines: list[str], *, max_scan: int = 120) -> list[str]:
    scan_limit = max_scan
    if max_scan == 120:
        scan_limit = min(max(60, len(lines) // 5), 240)
    seen: set[str] = set()
    out: list[str] = []
    for idx, line in enumerate(lines):
        raw = line.strip()
        key = line.strip().lower()
        words = len(key.split())
        header_like = 2 <= words <= 14 and not key.endswith((".", "!", "?"))
        has_upper = bool(re.search(r"[A-Z]", raw))
        if (
            idx < scan_limit
            and key
            and len(key) >= 6
            and header_like
            and has_upper
            and not any(ch in key for ch in "()[]{}\\")
            and not re.search(r"\b(19|20)\d{2}\b", key)
            and key in seen
        ):
            continue
        if key:
            seen.add(key)
        out.append(line)
    return out


def _is_citation_like_token(token: str) -> bool:
    t = token.strip()
    if not t:
        return False
    if t in {"(", ")", ",", ";", ":", ".", "et al.", "et al"}:
        return True
    if _YEAR_RE.match(t):
        return True
    if re.match(r"^[A-Za-z][A-Za-z\-' ]{0,40}$", t):
        return True
    if re.match(r"^\d{1,4}([,-]\d{1,4})*$", t):
        return True
    return False


def _is_citation_like_chunk(chunk: str) -> bool:
    c = chunk.strip()
    if not c:
        return False
    if len(c) > 140 or re.search(r"[!?]", c):
        return False
    parts = [p for p in re.split(r"[;,:()\s]+", c) if p]
    if not parts:
        return False
    for part in parts:
        p = part.strip().strip(".")
        if not p:
            continue
        if _YEAR_RE.match(p):
            continue
        if p.lower() in {"et", "al"}:
            continue
        if re.match(r"^\d{1,4}([,-]\d{1,4})*$", p):
            continue
        if re.match(r"^[A-Za-z][A-Za-z\-'']{0,40}$", p):
            continue
        return False
    return True


def _normalize_citation_body(text: str) -> str:
    body = compact_spaces(text)
    if not body:
        return body
    body = body.replace("et al ,", "et al,")
    body = re.sub(r"\bet\s+al\s*\.\s*\.", "et al.", body, flags=re.IGNORECASE)
    body = re.sub(r"\bet\s+al\s*\.", "et al.", body, flags=re.IGNORECASE)
    body = re.sub(r"\bet\s+al\b", "et al.", body, flags=re.IGNORECASE)
    body = body.replace("et al..", "et al.")
    body = re.sub(r"\s+([,;:)\]])", r"\1", body)
    body = re.sub(r"([(\[])\s+", r"\1", body)
    body = re.sub(r"([,;:])(?=\S)", r"\1 ", body)
    body = re.sub(r"\s{2,}", " ", body).strip(" ;,")
    return body


def _stitch_citation_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "(":
            open_char = "("
            close_char = ")"
        elif line == "[":
            open_char = "["
            close_char = "]"
        elif line.startswith("(") and ")" not in line:
            open_char = "("
            close_char = ")"
        elif line.startswith("[") and "]" not in line:
            open_char = "["
            close_char = "]"
        else:
            out.append(lines[i])
            i += 1
            continue

        chunks: list[str] = []
        if line not in {"(", "["}:
            chunks.append(line[1:].strip())
        j = i + 1
        close_at = None
        close_tail = ""
        while j < len(lines) and (j - i) <= 30:
            t = lines[j].strip()
            if not t:
                j += 1
                continue
            if close_char in t:
                before_close, _sep, tail = t.partition(close_char)
                chunks.append(before_close.strip())
                close_at = j
                close_tail = tail.strip()
                break
            chunks.append(t)
            t_clean = t.rstrip(".,;:()[]")
            token_for_check = t if t in {"(", ")", "[", "]", ",", ";", ":", "."} else t_clean
            if not _is_citation_like_token(token_for_check) and not _is_citation_like_chunk(t):
                break
            j += 1

        if close_at is None:
            out.append(lines[i])
            i += 1
            continue

        body = _normalize_citation_body(" ".join(chunks))
        year_count = len(re.findall(r"\b(19|20)\d{2}[a-z]?\b", body))
        alpha_seen = bool(re.search(r"[A-Za-z]", body))
        token_count = len(body.split())
        numeric_only = bool(re.fullmatch(r"[\d,\-\s]+", body))
        is_author_year = year_count >= 1 and alpha_seen
        is_numeric_bracket = open_char == "[" and numeric_only and token_count <= 30
        if (is_author_year or is_numeric_bracket) and 1 <= token_count <= 60:
            out.append(f"{open_char}{body}{close_char}")
            if close_tail:
                out.append(close_tail)
            i = close_at + 1
            continue

        out.append(lines[i])
        i += 1
    return out


def _looks_math_fragment(line: str) -> bool:
    c = line.strip()
    if not c:
        return False
    if c.count("|") >= 2:
        return False
    if c.startswith("--- |") or c.startswith("| ---"):
        return False
    word_count = len(c.split())
    if word_count > 8 and not c.startswith("\\"):
        return False
    if c in {"(", ")", ",", ".", ":", ";", "+", "-", "=", "{", "}"}:
        return True
    if _YEAR_RE.match(c):
        return False
    if re.match(r"^\(\d+\)$", c):
        return True
    if re.match(r"^[A-Za-z]$", c):
        return True
    if re.match(r"^\d{1,3}$", c):
        return True
    if re.search(r"[\\^_=+\-*/{}\[\]|<>∣∈Σ⊕→≤≥⋅×]", c):
        return True
    if re.search(r"[0-9]", c) and re.search(r"[A-Za-z]", c):
        return True
    if not _MATH_TOKEN_RE.match(c):
        return False
    if re.match(r"^[A-Za-z]{3,}$", c):
        return False
    return len(c) <= 40


def _join_math_tokens(tokens: list[str]) -> str:
    merged = ""
    for tok in tokens:
        t = tok.strip()
        if not t:
            continue
        if t in {")", "]", "}", ",", ";", ":"}:
            merged = merged.rstrip() + t
            continue
        if t in {"(", "[", "{"}:
            if merged and not merged.endswith(" "):
                merged += " "
            merged += t
            continue
        if merged and re.search(r"[A-Za-z0-9]$", merged) and re.match(r"^[A-Za-z0-9]", t):
            merged += " "
        merged += t
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged


def _stitch_math_spill_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not _looks_math_fragment(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        tokens: list[str] = []
        while j < len(lines) and _looks_math_fragment(lines[j]):
            tokens.append(lines[j])
            j += 1
        if len(tokens) >= 6:
            merged = _join_math_tokens(tokens)
            out.append(merged if merged else lines[i])
        else:
            out.extend(tokens)
        i = j
    return out


def _dedupe_adjacent_latex_unicode(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        cur = line.strip()
        if not out:
            out.append(line)
            continue
        prev = out[-1].strip()
        if not cur or not prev:
            out.append(line)
            continue
        prev_norm = re.sub(r"[^A-Za-z0-9]+", "", prev).lower()
        cur_norm = re.sub(r"[^A-Za-z0-9]+", "", cur.replace("\\", "")).lower()
        if "\\" in cur and prev_norm and prev_norm == cur_norm:
            continue
        out.append(line)
    return out


def _reflow_inline_fragments(lines: list[str]) -> list[str]:
    connector_words = {
        "and", "or", "to", "of", "in", "for", "with", "via",
        "by", "from", "as", "on", "at", "where", "which", "that",
        "while", "when", "whose",
    }
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        line_words = line.split()
        starts_like_continuation = bool(line and (line[0].islower() or line[0] in {",", ";", ":"}))
        first_word = line_words[0].lower() if line_words else ""
        if (
            out
            and line
            and len(line_words) <= 3
            and i + 1 < len(lines)
            and len(out[-1].split()) >= 10
            and len(lines[i + 1].strip().split()) >= 6
            and not re.match(r"^\d+(\.\d+)*$", line)
            and not re.match(r"^[A-Z][A-Za-z0-9\- ]{2,50}$", line)
            and (starts_like_continuation or first_word in connector_words)
            and not out[-1].strip().endswith((".", "!", "?"))
        ):
            out[-1] = compact_spaces(out[-1] + " " + line)
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return out


def _merge_section_number_headings(lines: list[str]) -> list[str]:
    def _looks_heading_title(text: str) -> bool:
        t = text.strip()
        if not t or len(t) > 120:
            return False
        if t.lower() in {"figure", "table", "fig.", "tab."}:
            return False
        if t.endswith((".", "!", "?")):
            return False
        words = t.split()
        if len(words) > 12:
            return False
        letter_count = sum(1 for ch in t if unicodedata.category(ch).startswith("L"))
        if letter_count < 2:
            return False
        return True

    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        nxt2 = lines[i + 2].strip() if i + 2 < len(lines) else ""
        if re.match(r"^\d+(\.\d+)*$", cur) and nxt and _looks_heading_title(nxt):
            out.append(f"{cur} {nxt}")
            i += 2
            continue
        if re.match(r"^\d+(\.\d+)*$", cur) and not nxt and nxt2 and _looks_heading_title(nxt2):
            out.append(f"{cur} {nxt2}")
            i += 3
            continue
        out.append(lines[i])
        i += 1
    return out


def _merge_leading_punctuation_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        cur = line.strip()
        if out and cur and cur[0] in {",", ";", ":", ".", ")"}:
            out[-1] = compact_spaces(out[-1].rstrip() + cur)
            continue
        out.append(line)
    return out


def _dedupe_adjacent_semantic_repeats(lines: list[str]) -> list[str]:
    out: list[str] = []

    def _normalize_for_compare(text: str) -> str:
        t = re.sub(r"^[•*·-]\s+", "", text.strip())
        t = re.sub(r"\s+", " ", t)
        t = t.strip(" .;:,")
        return t.lower()

    for line in lines:
        cur = line.strip()
        if not out:
            out.append(line)
            continue
        if not cur:
            out.append(line)
            continue

        prev_idx = -1
        for idx in range(len(out) - 1, -1, -1):
            if out[idx].strip():
                prev_idx = idx
                break
        if prev_idx < 0:
            out.append(line)
            continue

        prev = out[prev_idx].strip()
        prev_norm = _normalize_for_compare(prev)
        cur_norm = _normalize_for_compare(cur)
        blank_gap = sum(1 for x in out[prev_idx + 1:] if not x.strip())
        if prev_norm and prev_norm == cur_norm and len(cur_norm) >= 20 and blank_gap <= 1:
            continue
        out.append(line)
    return out


def _drop_visual_legend_artifacts(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        t = line.strip()
        if not t:
            out.append(line)
            continue
        if re.match(r"^\d+(\.\d+)?\s+\d+(\.\d+)?$", t):
            continue
        if re.match(r"^[a-zA-Z]\)$", t):
            continue
        if re.match(r"^[-−]?\d+\.\d+$", t):
            continue
        if re.match(r"^[A-Za-z]\]$", t):
            continue
        tokens = re.findall(r"\S+", t)
        if len(tokens) >= 8:
            short_tokens = sum(1 for tok in tokens if len(tok) <= 3)
            numeric_tokens = sum(1 for tok in tokens if re.search(r"\d", tok))
            has_panel_marker = bool(re.search(r"[a-zA-Z]\)", t))
            has_plot_symbols = bool(re.search(r"[≈±χλμσΣΔ⊙\[\]{}]", t))
            short_ratio = short_tokens / max(1, len(tokens))
            if (
                numeric_tokens >= 3
                and (has_panel_marker or has_plot_symbols)
                and short_ratio >= 0.20
                and not t.endswith((".", "!", "?"))
            ):
                continue
        if re.match(r"^[A-Za-zα-ωΑ-Ω][A-Za-z0-9_α-ωΑ-Ω]*\s*\[[^\]]{1,24}\](\s*[A-Za-z0-9_/\-]+)?$", t):
            continue
        out.append(line)
    return out


def _normalize_inline_tex_tokens(text: str) -> str:
    out = text
    replacements = {
        r"\\rightarrow": "→",
        r"\\to": "→",
        r"\\leftarrow": "←",
        r"\\leftrightarrow": "↔",
        r"\\leq": "≤",
        r"\\geq": "≥",
        r"\\times": "×",
        r"\\cdot": "·",
        r"\\in": "∈",
        r"\\notin": "∉",
        r"\\pm": "±",
    }
    for src, dst in replacements.items():
        out = re.sub(src + r"\b", dst, out)
    out = re.sub(r"\s*([→←↔≤≥×±·∈∉])\s*", r"\1", out)
    out = re.sub(r"\s+([,;:.!?])", r"\1", out)
    out = re.sub(r"([(\[])\s+", r"\1", out)
    out = re.sub(r"\s+([)\]])", r"\1", out)
    out = re.sub(r"([,;:])(?=\S)", r"\1 ", out)
    out = re.sub(r"\s{2,}", " ", out)
    return out
