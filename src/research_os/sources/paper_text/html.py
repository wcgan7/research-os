"""HTML text extraction for arXiv and generic pages."""

from __future__ import annotations

import re
from typing import Any

from research_os.sources.paper_text.cleaning import clean_full_text, compact_spaces

_ARXIV_HTML_FRONTMATTER_RE = re.compile(
    r"(?i)\b("
    r"department|university|institute|center|centre|observatory|school|laboratory|"
    r"correspondence|preprint|fellow|@"
    r")\b"
)


def _trim_html_frontmatter_to_abstract(text: str) -> str:
    lines = text.splitlines()
    abstract_idx = -1
    for i, ln in enumerate(lines[:260]):
        if ln.strip().lower() == "abstract":
            abstract_idx = i
            break
    if abstract_idx <= 2:
        return text

    prefix = lines[:abstract_idx]
    nonblank_prefix = [ln.strip() for ln in prefix if ln.strip()]
    if not nonblank_prefix:
        return text

    frontmatter_hits = 0
    for ln in nonblank_prefix:
        if _ARXIV_HTML_FRONTMATTER_RE.search(ln):
            frontmatter_hits += 1
            continue
        if re.match(r"^\[?\d+\]?\s", ln):
            frontmatter_hits += 1
            continue
    if frontmatter_hits < max(4, int(len(nonblank_prefix) * 0.35)):
        return text

    title_candidate = ""
    for ln in nonblank_prefix:
        t = ln.strip()
        if len(t.split()) < 4:
            continue
        if len(t) > 180:
            continue
        if _ARXIV_HTML_FRONTMATTER_RE.search(t):
            continue
        if re.match(r"^\[?\d+\]?\s", t):
            continue
        title_candidate = t
        break

    kept: list[str] = []
    if title_candidate:
        kept.extend([title_candidate, ""])
    kept.extend(lines[abstract_idx:])
    return "\n".join(kept).strip()


def extract_html_body_text(raw_html: str) -> str | None:
    """Generic HTML body extraction with fallback to regex."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
            tag.decompose()
        for selector in ("nav", "header", "footer", "aside", ".ltx_page_footer", ".ltx_page_header"):
            for node in soup.select(selector):
                node.decompose()
        for img in soup.find_all("img"):
            img.decompose()
        text = soup.get_text("\n")
    except Exception:
        text = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)
    return clean_full_text(text)


def extract_arxiv_html_body_text(raw_html: str) -> str | None:
    """ArXiv-specific HTML extraction with LaTeXML handling."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "canvas", "template"]):
            tag.decompose()
        for selector in (
            "nav", "header", "footer", "aside", "button", ".sr-only",
            ".ltx_keywords", ".ltx_page_footer", ".ltx_page_header",
            ".ltx_note_mark", ".ltx_ERROR",
        ):
            for node in soup.select(selector):
                node.decompose()

        # Handle math elements
        for m in soup.find_all("math"):
            tex = None
            ann = m.find("annotation", attrs={"encoding": "application/x-tex"})
            if ann is not None:
                candidate = ann.get_text(" ", strip=True)
                if candidate:
                    tex = candidate
            if not tex:
                alt = m.get("alttext") or m.get("aria-label")
                if isinstance(alt, str) and alt.strip():
                    tex = alt.strip()
            replacement = f" {tex} " if tex else " [MATH] "
            m.replace_with(soup.new_string(replacement))

        # Serialize tables to markdown
        def _cell_text(cell: Any) -> str:
            return compact_spaces(cell.get_text(" ", strip=True))

        def _serialize_table(table_node: Any, caption_text: str | None = None) -> str:
            rows = table_node.find_all("tr")
            parsed_rows: list[list[str]] = []
            for tr in rows:
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                row = [_cell_text(c) for c in cells]
                if any(x for x in row):
                    parsed_rows.append(row)
            if not parsed_rows:
                return compact_spaces(caption_text or "")

            max_cols = max(len(r) for r in parsed_rows)
            normalized_rows = [r + [""] * (max_cols - len(r)) for r in parsed_rows]
            header = normalized_rows[0]
            body_rows = normalized_rows[1:] if len(normalized_rows) > 1 else []

            lines: list[str] = []
            if caption_text:
                lines.append(caption_text)
            lines.append(" | ".join(header))
            if body_rows:
                lines.append(" | ".join(["---"] * max_cols))
                lines.extend(" | ".join(r) for r in body_rows)
            return "\n".join(lines)

        for fig in soup.select("figure.ltx_table"):
            caption = fig.find("figcaption")
            caption_text = compact_spaces(caption.get_text(" ", strip=True)) if caption else None
            table = fig.find("table")
            if table is None:
                if caption_text:
                    p = soup.new_tag("p")
                    p.string = caption_text
                    fig.replace_with(p)
                else:
                    fig.decompose()
                continue
            serialized = _serialize_table(table, caption_text)
            pre = soup.new_tag("pre")
            pre["data-cn-table"] = "1"
            pre.string = serialized
            fig.replace_with(pre)

        for table in soup.select("table.ltx_tabular"):
            if table.find_parent("figure", class_="ltx_table"):
                continue
            serialized = _serialize_table(table, None)
            pre = soup.new_tag("pre")
            pre["data-cn-table"] = "1"
            pre.string = serialized
            table.replace_with(pre)

        # Extract text from block elements
        root = soup.find("main") or soup.find("article") or soup.body or soup
        block_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd", "figcaption", "blockquote", "pre"}
        blocks: list[str] = []
        seen_blocks: set[str] = set()
        for node in root.find_all(block_tags):
            if node.find_parent(["script", "style"]):
                continue
            if node.name == "pre" and node.get("data-cn-table") == "1":
                raw = node.get_text("\n", strip=True)
                lines = [compact_spaces(ln) for ln in raw.splitlines() if compact_spaces(ln)]
                text = "\n".join(lines)
            else:
                text = compact_spaces(node.get_text(" ", strip=True))
            if len(text) < 2:
                continue
            key = text.lower()
            if len(key) >= 30 and key in seen_blocks:
                continue
            seen_blocks.add(key)
            blocks.append(text)

        # Pick up loose text nodes
        for text_node in root.find_all(string=True):
            parent = getattr(text_node, "parent", None)
            parent_name = getattr(parent, "name", "")
            if parent_name in block_tags or parent_name in {"script", "style"}:
                continue
            if parent and parent.find_parent(["figure", "table", "math"]):
                continue
            if parent_name not in {"main", "article", "section", "div"}:
                continue
            text = compact_spaces(str(text_node))
            if len(text) < 20:
                continue
            blocks.append(text)

        if blocks:
            text = "\n\n".join(blocks)
        else:
            text = root.get_text("\n")
    except Exception:
        return extract_html_body_text(raw_html)
    text = _trim_html_frontmatter_to_abstract(text)
    return clean_full_text(text)
