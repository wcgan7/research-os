"""Flat tool definitions — functions + JSON schemas for the literature review agent."""

from __future__ import annotations

import json
import re
from typing import Any

from research_os.store.models import (
    Assessment,
    CapabilityRequest,
    CoverageAssessment,
    Paper,
    ReviewNote,
    SearchRecord,
)
from research_os.store.store import Store
from research_os.types import ToolResult

# ── Type alias for the context bag passed to every tool ──────────────

ToolContext = dict[str, Any]
# Expected keys: "store", "review_id", "sources" (dict of source clients)


# ── Tool implementations ─────────────────────────────────────────────


def search_papers(ctx: ToolContext, query: str, source: str = "semantic_scholar", limit: int = 20) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]
    sources = ctx["sources"]

    client = sources.get(source)
    if not client:
        return ToolResult(ok=False, error=f"Unknown source: {source}. Available: {list(sources.keys())}")

    result = client.search(query, limit=limit) if source != "arxiv" else client.search(query, max_results=limit)
    if not result.ok:
        return result

    new_papers = []
    skipped = 0
    paper_ids = []

    for item in result.data:
        dup = store.find_duplicate(
            review_id,
            doi=item.get("doi"),
            external_id=item.get("external_id"),
            title=item.get("title"),
        )
        if dup:
            paper_ids.append(dup.id)
            skipped += 1
            continue

        paper = Paper(
            review_id=review_id,
            source=item.get("source", source),
            external_id=item.get("external_id", ""),
            title=item.get("title", ""),
            authors=item.get("authors", []),
            year=item.get("year"),
            abstract=item.get("abstract"),
            url=item.get("url"),
            doi=item.get("doi"),
            citation_count=item.get("citation_count"),
            status="discovered",
        )
        store.save(paper)
        paper_ids.append(paper.id)
        new_papers.append(paper.title)

    record = SearchRecord(
        review_id=review_id,
        query=query,
        source=source,
        rationale="",
        result_count=len(result.data),
        paper_ids=paper_ids,
    )
    store.save(record)

    return ToolResult(ok=True, data={
        "total_results": len(result.data),
        "new_papers": len(new_papers),
        "already_known": skipped,
        "new_titles": new_papers[:10],
        "search_record_id": record.id,
    })


def get_paper_details(ctx: ToolContext, paper_id: str) -> ToolResult:
    store: Store = ctx["store"]
    sources = ctx["sources"]

    paper = store.get(Paper, paper_id)
    if not paper:
        return ToolResult(ok=False, error=f"Paper not found: {paper_id}")

    client = sources.get(paper.source)
    if not client:
        return ToolResult(ok=True, data={
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "abstract": paper.abstract,
            "url": paper.url,
            "doi": paper.doi,
            "citation_count": paper.citation_count,
            "source": paper.source,
            "status": paper.status,
        })

    if paper.source == "arxiv":
        result = client.get_paper(paper.external_id)
    else:
        result = client.get_paper(paper.external_id)

    if result.ok:
        data = result.data
        if data.get("abstract") and not paper.abstract:
            paper.abstract = data["abstract"]
        if data.get("citation_count") is not None:
            paper.citation_count = data["citation_count"]
        if data.get("doi") and not paper.doi:
            paper.doi = data["doi"]
        store.save(paper)

    return ToolResult(ok=True, data={
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "abstract": paper.abstract,
        "url": paper.url,
        "doi": paper.doi,
        "citation_count": paper.citation_count,
        "source": paper.source,
        "status": paper.status,
    })


def expand_references(ctx: ToolContext, paper_id: str, limit: int = 30) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]
    sources = ctx["sources"]

    paper = store.get(Paper, paper_id)
    if not paper:
        return ToolResult(ok=False, error=f"Paper not found: {paper_id}")

    # Only S2 supports reference expansion
    s2 = sources.get("semantic_scholar")
    if not s2:
        return ToolResult(ok=False, error="Semantic Scholar client not available for reference expansion")

    # Use the paper's S2 ID if available, otherwise try DOI
    lookup_id = paper.external_id if paper.source == "semantic_scholar" else (paper.doi or paper.external_id)
    result = s2.get_references(lookup_id, limit=limit)
    if not result.ok:
        return result

    new_papers = []
    skipped = 0
    for ref in result.data:
        dup = store.find_duplicate(
            review_id,
            doi=ref.get("doi"),
            external_id=ref.get("external_id"),
            title=ref.get("title"),
        )
        if dup:
            skipped += 1
            continue

        p = Paper(
            review_id=review_id,
            source=ref.get("source", "semantic_scholar"),
            external_id=ref.get("external_id", ""),
            title=ref.get("title", ""),
            authors=ref.get("authors", []),
            year=ref.get("year"),
            abstract=ref.get("abstract"),
            url=ref.get("url"),
            doi=ref.get("doi"),
            citation_count=ref.get("citation_count"),
            status="discovered",
        )
        store.save(p)
        new_papers.append({"id": p.id, "title": p.title})

    return ToolResult(ok=True, data={
        "source_paper": paper.title,
        "references_found": len(result.data),
        "new_papers": len(new_papers),
        "already_known": skipped,
        "new_references": new_papers[:15],
    })


def save_assessment(
    ctx: ToolContext,
    paper_id: str,
    relevance_score: int,
    rationale: str,
    key_claims: list[str] | None = None,
    methodology_notes: str | None = None,
    connections: list[str] | None = None,
) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]

    paper = store.get(Paper, paper_id)
    if not paper:
        return ToolResult(ok=False, error=f"Paper not found: {paper_id}")

    assessment = Assessment(
        review_id=review_id,
        paper_id=paper_id,
        relevance_score=relevance_score,
        rationale=rationale,
        key_claims=key_claims or [],
        methodology_notes=methodology_notes,
        connections=connections or [],
    )
    store.save(assessment)

    # Update paper status based on score
    if relevance_score >= 4:
        paper.status = "relevant"
    elif relevance_score >= 3:
        paper.status = "reviewed"
    else:
        paper.status = "not_relevant"
    store.save(paper)

    return ToolResult(ok=True, data={
        "assessment_id": assessment.id,
        "paper_title": paper.title,
        "new_status": paper.status,
    })


def update_paper_status(
    ctx: ToolContext,
    paper_id: str,
    status: str,
    rationale: str | None = None,
) -> ToolResult:
    store: Store = ctx["store"]

    valid = {"discovered", "seed", "reviewed", "relevant", "not_relevant", "uncertain", "deferred"}
    if status not in valid:
        return ToolResult(ok=False, error=f"Invalid status: {status}. Valid: {valid}")

    paper = store.get(Paper, paper_id)
    if not paper:
        return ToolResult(ok=False, error=f"Paper not found: {paper_id}")

    old_status = paper.status
    paper.status = status
    store.save(paper)

    return ToolResult(ok=True, data={
        "paper_id": paper_id,
        "title": paper.title,
        "old_status": old_status,
        "new_status": status,
        "rationale": rationale,
    })


def save_coverage(
    ctx: ToolContext,
    areas_covered: list[str],
    gaps: list[str],
    confidence: float,
    next_actions: list[str],
    summary: str,
) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]

    ca = CoverageAssessment(
        review_id=review_id,
        areas_covered=areas_covered,
        gaps=gaps,
        confidence=confidence,
        next_actions=next_actions,
        summary=summary,
    )
    store.save(ca)
    return ToolResult(ok=True, data={"coverage_id": ca.id, "confidence": confidence})


def save_note(
    ctx: ToolContext,
    kind: str,
    content: str,
    paper_ids: list[str] | None = None,
    priority: int | None = None,
) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]

    valid_kinds = {
        "question", "gap", "contradiction", "baseline_candidate",
        "tool_wish", "strategy_note", "observation", "assumption", "next_step",
    }
    if kind not in valid_kinds:
        return ToolResult(ok=False, error=f"Invalid kind: {kind}. Valid: {valid_kinds}")

    note = ReviewNote(
        review_id=review_id,
        kind=kind,
        content=content,
        paper_ids=paper_ids or [],
        priority=priority,
    )
    store.save(note)
    return ToolResult(ok=True, data={"note_id": note.id, "kind": kind})


def request_capability(
    ctx: ToolContext,
    name: str,
    rationale: str,
    example_usage: str,
) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]

    req = CapabilityRequest(
        review_id=review_id,
        name=name,
        rationale=rationale,
        example_usage=example_usage,
    )
    store.save(req)
    return ToolResult(ok=True, data={"request_id": req.id, "name": name})


def query_store(ctx: ToolContext, record_type: str, filters: dict | None = None) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]

    type_map = {
        "papers": Paper,
        "assessments": Assessment,
        "searches": SearchRecord,
        "coverage": CoverageAssessment,
        "notes": ReviewNote,
        "capability_requests": CapabilityRequest,
    }

    cls = type_map.get(record_type)
    if not cls:
        return ToolResult(ok=False, error=f"Unknown record type: {record_type}. Valid: {list(type_map.keys())}")

    query_filters = {"review_id": review_id}
    # Extract special filters before passing to store
    keyword = None
    if filters:
        keyword = filters.pop("keyword", None)
        query_filters.update(filters)

    import dataclasses
    records = store.query(cls, **query_filters)

    # Apply keyword filter (case-insensitive title/content search)
    if keyword and records:
        kw = keyword.lower()
        filtered = []
        for r in records:
            searchable = ""
            if hasattr(r, "title"):
                searchable += (r.title or "").lower()
            if hasattr(r, "abstract"):
                searchable += " " + (r.abstract or "").lower()
            if hasattr(r, "content"):
                searchable += " " + (r.content or "").lower()
            if kw in searchable:
                filtered.append(r)
        records = filtered

    data = [dataclasses.asdict(r) for r in records]
    return ToolResult(ok=True, data={"count": len(data), "records": data})


def seed_paper(ctx: ToolContext, url_or_id: str) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]
    sources = ctx["sources"]

    # Detect source from URL/ID pattern
    source_name = None
    lookup_id = url_or_id

    # arXiv patterns
    arxiv_match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", url_or_id)
    if arxiv_match:
        source_name = "arxiv"
        lookup_id = arxiv_match.group(1)
    elif re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", url_or_id):
        source_name = "arxiv"
        lookup_id = re.sub(r"v\d+$", "", url_or_id)

    # DOI patterns
    elif url_or_id.startswith("10.") or "doi.org/" in url_or_id:
        source_name = "semantic_scholar"
        lookup_id = re.sub(r"^https?://doi\.org/", "", url_or_id)

    # Semantic Scholar patterns
    elif "semanticscholar.org" in url_or_id:
        source_name = "semantic_scholar"
        match = re.search(r"/paper/(?:.+?/)?([a-f0-9]{40})", url_or_id)
        if match:
            lookup_id = match.group(1)

    # OpenAlex patterns
    elif url_or_id.startswith("W") or "openalex.org" in url_or_id:
        source_name = "openalex"
        match = re.search(r"(W\d+)", url_or_id)
        if match:
            lookup_id = match.group(1)

    if not source_name:
        return ToolResult(ok=False, error=f"Could not detect source from: {url_or_id}")

    client = sources.get(source_name)
    if not client:
        return ToolResult(ok=False, error=f"Source client not available: {source_name}")

    result = client.get_paper(lookup_id)
    if not result.ok:
        return result

    data = result.data

    # Check for duplicate
    dup = store.find_duplicate(
        review_id,
        doi=data.get("doi"),
        external_id=data.get("external_id"),
        title=data.get("title"),
    )
    if dup:
        dup.status = "seed"
        store.save(dup)
        return ToolResult(ok=True, data={
            "paper_id": dup.id,
            "title": dup.title,
            "status": "seed",
            "note": "Paper already existed, updated status to seed",
        })

    paper = Paper(
        review_id=review_id,
        source=data.get("source", source_name),
        external_id=data.get("external_id", ""),
        title=data.get("title", ""),
        authors=data.get("authors", []),
        year=data.get("year"),
        abstract=data.get("abstract"),
        url=data.get("url"),
        doi=data.get("doi"),
        citation_count=data.get("citation_count"),
        status="seed",
    )
    store.save(paper)

    return ToolResult(ok=True, data={
        "paper_id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "status": "seed",
    })


def export_bibtex(ctx: ToolContext, paper_ids: list[str] | None = None) -> ToolResult:
    store: Store = ctx["store"]
    review_id: str = ctx["review_id"]

    if paper_ids:
        papers = [store.get(Paper, pid) for pid in paper_ids]
        papers = [p for p in papers if p is not None]
    else:
        papers = [
            p for p in store.query(Paper, review_id=review_id)
            if p.status in ("relevant", "seed", "reviewed")
        ]

    if not papers:
        return ToolResult(ok=True, data={"bibtex": "", "count": 0})

    entries = []
    for paper in papers:
        # Generate cite key: lastname + year + first keyword from title
        first_author = paper.authors[0].split()[-1].lower() if paper.authors else "unknown"
        year = str(paper.year) if paper.year else "nd"
        title_word = re.sub(r"[^a-z]", "", (paper.title.split() or [""])[0].lower())
        cite_key = f"{first_author}{year}{title_word}"

        # Build fields
        fields = []
        fields.append(f"  title = {{{paper.title}}}")
        if paper.authors:
            fields.append(f"  author = {{{' and '.join(paper.authors)}}}")
        if paper.year:
            fields.append(f"  year = {{{paper.year}}}")
        if paper.doi:
            fields.append(f"  doi = {{{paper.doi}}}")
        if paper.url:
            fields.append(f"  url = {{{paper.url}}}")
        if paper.external_id and paper.source == "arxiv":
            fields.append(f"  eprint = {{{paper.external_id}}}")
            fields.append("  archivePrefix = {arXiv}")

        entry_type = "@article"
        entry = f"{entry_type}{{{cite_key},\n" + ",\n".join(fields) + "\n}"
        entries.append(entry)

    bibtex = "\n\n".join(entries)
    return ToolResult(ok=True, data={"bibtex": bibtex, "count": len(entries)})


def execute_code(ctx: ToolContext, code: str, language: str = "python") -> ToolResult:
    """Execute code in a subprocess and return stdout/stderr."""
    import subprocess
    import tempfile
    import os

    timeout = 120  # seconds

    if language == "python":
        cmd = ["python3", "-c", code]
    elif language == "bash":
        cmd = ["bash", "-c", code]
    else:
        return ToolResult(ok=False, error=f"Unsupported language: {language}. Use 'python' or 'bash'.")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser("~"),
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        # Truncate very long output
        if len(output) > 10000:
            output = output[:10000] + f"\n... (truncated, {len(output)} chars total)"

        return ToolResult(
            ok=result.returncode == 0,
            data={"stdout": result.stdout[:10000], "stderr": result.stderr[:5000], "returncode": result.returncode},
            error=f"Process exited with code {result.returncode}" if result.returncode != 0 else None,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, error=f"Execution timed out after {timeout}s", retryable=False)
    except Exception as e:
        return ToolResult(ok=False, error=f"Execution error: {e}")


# ── Tool schemas for Claude tool_use ─────────────────────────────────

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "search_papers",
        "description": "Search for academic papers across different sources. Records all results and deduplicates automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "source": {
                    "type": "string",
                    "enum": ["semantic_scholar", "arxiv", "openalex"],
                    "description": "Which source to search. Default: semantic_scholar",
                },
                "limit": {"type": "integer", "description": "Max results to return. Default: 20"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_paper_details",
        "description": "Fetch full metadata for a paper by its internal ID. Updates the paper record with any new information from the source API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Internal paper record ID"},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "expand_references",
        "description": "Fetch references cited by a paper and create records for new ones. Uses Semantic Scholar for reference data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Internal paper record ID"},
                "limit": {"type": "integer", "description": "Max references to fetch. Default: 30"},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "save_assessment",
        "description": "Record your assessment of a paper's relevance to the review. Also updates the paper's status based on the score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Internal paper record ID"},
                "relevance_score": {"type": "integer", "minimum": 1, "maximum": 5, "description": "1=irrelevant, 5=essential"},
                "rationale": {"type": "string", "description": "Why this paper is or isn't relevant"},
                "key_claims": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main claims or contributions of the paper",
                },
                "methodology_notes": {"type": "string", "description": "Notes on methodology, if notable"},
                "connections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Connections to other papers or ideas in this review",
                },
            },
            "required": ["paper_id", "relevance_score", "rationale"],
        },
    },
    {
        "name": "update_paper_status",
        "description": "Explicitly change a paper's status. Use when revising your view, deferring a paper, or marking something uncertain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Internal paper record ID"},
                "status": {
                    "type": "string",
                    "enum": ["discovered", "seed", "reviewed", "relevant", "not_relevant", "uncertain", "deferred"],
                },
                "rationale": {"type": "string", "description": "Why you're changing the status"},
            },
            "required": ["paper_id", "status"],
        },
    },
    {
        "name": "save_coverage",
        "description": "Record your assessment of how well the review covers the topic. Confidence is a rough internal signal, not a calibrated probability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "areas_covered": {"type": "array", "items": {"type": "string"}},
                "gaps": {"type": "array", "items": {"type": "string"}, "description": "Areas not yet well covered"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Rough confidence in coverage (0-1)"},
                "next_actions": {"type": "array", "items": {"type": "string"}, "description": "What to do next to improve coverage"},
                "summary": {"type": "string"},
            },
            "required": ["areas_covered", "gaps", "confidence", "next_actions", "summary"],
        },
    },
    {
        "name": "save_note",
        "description": "Record a research process note — open questions, contradictions, observations, strategy decisions, assumptions, or anything else worth tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": [
                        "question", "gap", "contradiction", "baseline_candidate",
                        "tool_wish", "strategy_note", "observation", "assumption", "next_step",
                    ],
                },
                "content": {"type": "string"},
                "paper_ids": {"type": "array", "items": {"type": "string"}, "description": "Related paper IDs, if any"},
                "priority": {"type": "integer", "description": "Optional priority (higher = more important)"},
            },
            "required": ["kind", "content"],
        },
    },
    {
        "name": "request_capability",
        "description": "Record a wish for a tool or capability that doesn't exist yet. This will be reviewed by a human or higher-level agent later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short name for the capability"},
                "rationale": {"type": "string", "description": "Why this would be useful"},
                "example_usage": {"type": "string", "description": "Example of how you would use it"},
            },
            "required": ["name", "rationale", "example_usage"],
        },
    },
    {
        "name": "query_store",
        "description": "Read records from the store. Use to check current state — papers found, assessments made, searches done, notes, coverage, capability requests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_type": {
                    "type": "string",
                    "enum": ["papers", "assessments", "searches", "coverage", "notes", "capability_requests"],
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters. Exact-match fields (e.g., {\"status\": \"relevant\"}), plus special \"keyword\" filter for case-insensitive title/abstract search (e.g., {\"keyword\": \"quantization\"})",
                },
            },
            "required": ["record_type"],
        },
    },
    {
        "name": "seed_paper",
        "description": "Add a paper as a seed by URL or ID. Supports arXiv URLs/IDs, DOIs, Semantic Scholar URLs, and OpenAlex IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url_or_id": {"type": "string", "description": "Paper URL, DOI, arXiv ID, or OpenAlex ID"},
            },
            "required": ["url_or_id"],
        },
    },
    {
        "name": "export_bibtex",
        "description": "Generate BibTeX entries for papers. Defaults to all relevant/seed/reviewed papers if no IDs given.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific paper IDs to export. If empty, exports all relevant papers.",
                },
            },
        },
    },
    {
        "name": "execute_code",
        "description": "Execute Python or bash code. Use this for anything the other tools don't cover: fetching a specific URL, parsing data, running custom analysis, downloading files, processing text, or any ad-hoc task. The code runs in a subprocess with a 120s timeout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code to execute"},
                "language": {
                    "type": "string",
                    "enum": ["python", "bash"],
                    "description": "Language to execute. Default: python",
                },
            },
            "required": ["code"],
        },
    },
]


# ── Dispatch table ────────────────────────────────────────────────────

TOOL_FUNCTIONS: dict[str, callable] = {
    "search_papers": search_papers,
    "get_paper_details": get_paper_details,
    "expand_references": expand_references,
    "save_assessment": save_assessment,
    "update_paper_status": update_paper_status,
    "save_coverage": save_coverage,
    "save_note": save_note,
    "request_capability": request_capability,
    "query_store": query_store,
    "seed_paper": seed_paper,
    "export_bibtex": export_bibtex,
    "execute_code": execute_code,
}
