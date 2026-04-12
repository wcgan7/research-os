"""LaTeX-to-text conversion and arXiv e-print tarball extraction."""

from __future__ import annotations

import io
import re
import tarfile

from research_os.sources.paper_text.cleaning import clean_full_text
from research_os.sources.paper_text.http import http_get
from research_os.sources.paper_text.scoring import is_fulltext_quality_sufficient


def latex_to_text(tex: str) -> str | None:
    """Convert LaTeX source to plain text.

    Primary: pylatexenc. Fallback: regex-based stripping.
    """
    try:
        from pylatexenc.latex2text import LatexNodes2Text

        converter = LatexNodes2Text(math_mode="with-delimiters")
        converted = converter.latex_to_text(tex)
        return str(converted)
    except Exception:
        cleaned = re.sub(r"(?m)(?<!\\)%.*$", "", tex)
        cleaned = re.sub(
            r"\\begin\{equation\*?\}[\s\S]*?\\end\{equation\*?\}",
            "\n[MATH]\n",
            cleaned,
        )
        cleaned = re.sub(r"\\begin\{align\*?\}[\s\S]*?\\end\{align\*?\}", "\n[MATH]\n", cleaned)
        cleaned = re.sub(
            r"\\begin\{figure\*?\}[\s\S]*?\\end\{figure\*?\}",
            "\n[FIGURE]\n",
            cleaned,
        )
        cleaned = re.sub(r"\\begin\{table\*?\}[\s\S]*?\\end\{table\*?\}", "\n[TABLE]\n", cleaned)
        cleaned = re.sub(r"\$[^$]+\$", " [MATH] ", cleaned)
        cleaned = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", cleaned)
        cleaned = cleaned.replace("{", " ").replace("}", " ")
        return cleaned


def fetch_arxiv_eprint_full_text(arxiv_id: str) -> str | None:
    """Fetch arXiv e-print tarball, extract .tex files, convert to text."""
    from urllib.parse import quote

    url = f"https://arxiv.org/e-print/{quote(arxiv_id)}"
    resp = http_get(url, timeout_s=20.0)
    if resp.status_code != 200 or not resp.content:
        return None

    try:
        with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:*") as tf:
            tex_chunks: list[str] = []
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                if not member.name.lower().endswith(".tex"):
                    continue
                if member.size <= 0 or member.size > 2_000_000:
                    continue
                f = tf.extractfile(member)
                if f is None:
                    continue
                raw = f.read()
                if not raw:
                    continue
                try:
                    decoded = raw.decode("utf-8", errors="ignore")
                except Exception:
                    decoded = raw.decode("latin-1", errors="ignore")
                tex_chunks.append(decoded)
                if len(tex_chunks) >= 12:
                    break
    except tarfile.TarError:
        return None

    if not tex_chunks:
        return None

    plain_chunks: list[str] = []
    for tex in tex_chunks:
        plain = latex_to_text(tex)
        if plain and plain.strip():
            plain_chunks.append(plain)
    if not plain_chunks:
        return None

    text = clean_full_text("\n\n".join(plain_chunks))
    if not text or not is_fulltext_quality_sufficient(text):
        return None
    return text
