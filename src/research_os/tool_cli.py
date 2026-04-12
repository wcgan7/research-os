"""CLI tool interface for the mastermind agent.

Each tool is exposed as `research-os tool <name> <json-args>` so that
claude -p can invoke them via Bash.  Output is always JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import httpx

from research_os.config import Config
from research_os.sources.arxiv import ArxivClient
from research_os.sources.cache import Cache
from research_os.sources.openalex import OpenAlexClient
from research_os.sources.semantic_scholar import SemanticScholarClient
from research_os.store.db import get_connection, init_schema
from research_os.store.store import Store


def _setup(review_id: str) -> tuple[dict, str]:
    """Return (ctx, review_id) for tool dispatch."""
    cfg = Config()
    conn = get_connection(cfg.db_path)
    init_schema(conn)
    store = Store(conn)

    http = httpx.Client(timeout=30.0, follow_redirects=True)
    cache = Cache(cfg.cache_dir)
    sources = {
        "semantic_scholar": SemanticScholarClient(http, cache, api_key=cfg.s2_api_key),
        "arxiv": ArxivClient(http, cache),
        "openalex": OpenAlexClient(http, cache),
    }
    ctx = {"store": store, "review_id": review_id, "sources": sources}
    return ctx, review_id


@click.group("tool")
def tool_group():
    """Run a research tool and return JSON output."""
    pass


@tool_group.command("call")
@click.argument("review_id")
@click.argument("tool_name")
@click.argument("args_json", default="{}")
def tool_call(review_id: str, tool_name: str, args_json: str):
    """Call a tool by name with JSON arguments.

    Usage: research-os tool call <review_id> <tool_name> '<json_args>'

    For large JSON, pipe via stdin: echo '<json>' | research-os tool call <id> <tool> -
    """
    from research_os.agent.tools import TOOL_FUNCTIONS

    fn = TOOL_FUNCTIONS.get(tool_name)
    if not fn:
        json.dump({"ok": False, "error": f"Unknown tool: {tool_name}"}, sys.stdout)
        sys.exit(1)

    # Support reading from stdin with "-" argument
    if args_json == "-":
        args_json = sys.stdin.read().strip()

    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as e:
        json.dump({"ok": False, "error": f"Invalid JSON args: {e}"}, sys.stdout)
        sys.exit(1)

    ctx, _ = _setup(review_id)

    try:
        result = fn(ctx, **args)
        output = {"ok": result.ok}
        if result.ok:
            output["data"] = result.data
        else:
            output["error"] = result.error
            output["retryable"] = result.retryable
        json.dump(output, sys.stdout, default=str)
    except Exception as e:
        json.dump({"ok": False, "error": str(e)}, sys.stdout)
        sys.exit(1)


@tool_group.command("list-tools")
def list_tools():
    """List available tools and their descriptions."""
    from research_os.agent.tools import TOOL_DEFINITIONS

    tools = []
    for t in TOOL_DEFINITIONS:
        tools.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("input_schema", {}),
        })
    json.dump(tools, sys.stdout, indent=2)


@tool_group.command("summary")
@click.argument("review_id")
def review_summary(review_id: str):
    """Get a summary of the current review state."""
    ctx, _ = _setup(review_id)
    store: Store = ctx["store"]

    from research_os.store.models import (
        Assessment,
        CoverageAssessment,
        Paper,
        ReviewNote,
        SearchRecord,
        LiteratureReview,
        SotaSummary,
    )

    review = store.get(LiteratureReview, review_id)
    if not review:
        # Try prefix match
        reviews = store.query(LiteratureReview)
        matches = [r for r in reviews if r.id.startswith(review_id)]
        if len(matches) == 1:
            review = matches[0]
            review_id = review.id
        else:
            json.dump({"ok": False, "error": f"Review not found: {review_id}"}, sys.stdout)
            return

    papers = store.query(Paper, review_id=review_id)
    assessments = store.query(Assessment, review_id=review_id)
    searches = store.query(SearchRecord, review_id=review_id)
    notes = store.query(ReviewNote, review_id=review_id)
    coverages = store.query(CoverageAssessment, review_id=review_id)
    sotas = store.query(SotaSummary, review_id=review_id)

    status_counts: dict[str, int] = {}
    for p in papers:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1

    papers_with_resources = sum(1 for p in papers if p.resources)

    summary = {
        "ok": True,
        "data": {
            "review_id": review_id,
            "topic": review.topic,
            "objective": review.objective,
            "status": review.status,
            "paper_counts": status_counts,
            "total_papers": len(papers),
            "total_assessments": len(assessments),
            "total_searches": len(searches),
            "total_notes": len(notes),
            "papers_with_resources": papers_with_resources,
            "recent_searches": [
                {"query": s.query, "source": s.source, "result_count": s.result_count}
                for s in searches[:10]
            ],
            "latest_coverage": {
                "confidence": coverages[0].confidence,
                "summary": coverages[0].summary,
                "gaps": coverages[0].gaps,
                "areas_covered": coverages[0].areas_covered,
            } if coverages else None,
            "has_sota_summary": len(sotas) > 0,
            "recent_notes": [
                {"kind": n.kind, "content": n.content[:200]}
                for n in notes[:10]
            ],
        },
    }
    json.dump(summary, sys.stdout, default=str)
