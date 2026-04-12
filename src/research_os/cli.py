"""CLI for Research OS literature review system."""

from __future__ import annotations

import sys

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from research_os.agent.loop import REFRESH_CONTEXT_TEMPLATE, run_agent
from research_os.config import Config
from research_os.sources.arxiv import ArxivClient
from research_os.sources.cache import Cache
from research_os.sources.openalex import OpenAlexClient
from research_os.sources.semantic_scholar import SemanticScholarClient
from research_os.sources.web_search import WebSearchClient
from research_os.store.db import get_connection, init_schema
from research_os.store.models import (
    Assessment,
    CoverageAssessment,
    LiteratureReview,
    Paper,
    ReviewNote,
    SearchRecord,
    SotaSummary,
)
from research_os.store.store import Store

console = Console()


def _setup(config: Config | None = None) -> tuple[Config, Store]:
    """Initialize config, db, and store."""
    cfg = config or Config()
    conn = get_connection(cfg.db_path)
    init_schema(conn)
    return cfg, Store(conn)


def _make_sources(config: Config) -> dict:
    """Create source clients."""
    http = httpx.Client(timeout=30.0, follow_redirects=True)
    cache = Cache(config.cache_dir)
    return {
        "semantic_scholar": SemanticScholarClient(http, cache, api_key=config.s2_api_key),
        "arxiv": ArxivClient(http, cache),
        "openalex": OpenAlexClient(http, cache),
        "web_search": WebSearchClient(),
    }


def _short_id(full_id: str) -> str:
    """First 8 chars of a UUID for display."""
    return full_id[:8]


@click.group()
def cli():
    """Research OS — agent-driven research tools."""
    pass


# Register tool CLI subcommand
from research_os.tool_cli import tool_group
cli.add_command(tool_group, "tool")


@cli.group()
def lit():
    """Literature review commands."""
    pass


@lit.command("new")
@click.argument("topic")
@click.option("--objective", "-o", required=True, help="What you want to learn")
@click.option("--seed", "-s", multiple=True, help="Seed paper URL or ID (can repeat)")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--max-turns", default=None, type=int, help="Max agent turns")
def lit_new(topic: str, objective: str, seed: tuple[str, ...], model: str | None, max_turns: int | None):
    """Start a new literature review using claude -p."""
    from research_os.launcher import launch_review

    result = launch_review(
        topic=topic,
        objective=objective,
        seed_urls=list(seed) if seed else None,
        model=model,
        max_turns=max_turns,
    )

    console.print(f"\n[green]Review {_short_id(result['review_id'])} completed.[/green]")
    console.print(f"Logs: {result['log_dir']}")


@lit.command("list")
def lit_list():
    """List all literature reviews."""
    _, store = _setup()
    reviews = store.query(LiteratureReview)

    if not reviews:
        console.print("No reviews yet. Use [bold]research-os lit new[/bold] to start one.")
        return

    table = Table(title="Literature Reviews")
    table.add_column("ID", style="cyan")
    table.add_column("Topic")
    table.add_column("Status")
    table.add_column("Papers")
    table.add_column("Created")

    for r in reviews:
        count = store.count(Paper, review_id=r.id)
        table.add_row(
            _short_id(r.id),
            r.topic[:60],
            r.status,
            str(count),
            r.created_at[:10],
        )

    console.print(table)


@lit.command("status")
@click.argument("review_id")
def lit_status(review_id: str):
    """Show status of a literature review."""
    _, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    papers = store.query(Paper, review_id=review.id)
    assessments = store.query(Assessment, review_id=review.id)
    searches = store.query(SearchRecord, review_id=review.id)
    notes = store.query(ReviewNote, review_id=review.id)
    coverages = store.query(CoverageAssessment, review_id=review.id)
    sotas = store.query(SotaSummary, review_id=review.id)

    # Count papers by status
    status_counts: dict[str, int] = {}
    for p in papers:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1

    papers_with_code = sum(1 for p in papers if p.code_url)
    papers_with_datasets = sum(1 for p in papers if p.datasets)

    panel_text = f"[bold]{review.topic}[/bold]\n"
    panel_text += f"Objective: {review.objective}\n"
    panel_text += f"Status: {review.status}\n\n"
    panel_text += f"Papers: {len(papers)} total\n"
    for s, c in sorted(status_counts.items()):
        panel_text += f"  {s}: {c}\n"
    panel_text += f"\nAssessments: {len(assessments)}\n"
    panel_text += f"Searches: {len(searches)}\n"
    panel_text += f"Notes: {len(notes)}\n"
    if papers_with_code or papers_with_datasets:
        panel_text += f"Code tracked: {papers_with_code} papers\n"
        panel_text += f"Datasets tracked: {papers_with_datasets} papers\n"
    panel_text += f"SOTA summary: {'Yes' if sotas else 'No'}\n"

    if coverages:
        latest = coverages[0]
        panel_text += f"\nLatest coverage (confidence: {latest.confidence:.2f}):\n"
        panel_text += f"  {latest.summary[:200]}\n"
        if latest.gaps:
            panel_text += f"  Gaps: {', '.join(latest.gaps[:5])}\n"

    console.print(Panel(panel_text, title=f"Review {_short_id(review.id)}"))


@lit.command("refresh")
@click.argument("review_id")
@click.option(
    "--provider", "-p", default=None,
    type=click.Choice(["anthropic_api", "claude_cli"]),
    help="LLM provider override",
)
@click.option("--model", "-m", default=None, help="Model override")
def lit_refresh(review_id: str, provider: str | None, model: str | None):
    """Refresh a review — search for new work and update coverage."""
    config, store = _setup()
    if provider:
        config.provider = provider
    if model:
        config.model = model

    if config.provider == "anthropic_api" and not config.anthropic_api_key:
        console.print("[red]ANTHROPIC_API_KEY not set. Use --provider claude_cli for CLI mode.[/red]")
        sys.exit(1)

    review = _find_review(store, review_id)
    if not review:
        return

    sources = _make_sources(config)

    # Build context from previous work
    searches = store.query(SearchRecord, review_id=review.id)
    search_summary = "\n".join(
        f"- [{s.source}] \"{s.query}\" → {s.result_count} results"
        for s in searches[:20]
    ) or "No previous searches."

    coverages = store.query(CoverageAssessment, review_id=review.id)
    coverage_summary = coverages[0].summary if coverages else "No previous coverage assessment."

    notes = store.query(ReviewNote, review_id=review.id)
    notes_summary = "\n".join(
        f"- [{n.kind}] {n.content[:100]}" for n in notes[:10]
    ) or "No previous notes."

    extra = REFRESH_CONTEXT_TEMPLATE.format(
        searches=search_summary,
        coverage=coverage_summary,
        notes=notes_summary,
    )

    review.status = "active"
    store.save(review)

    console.print(f"\n[bold]Refreshing review {_short_id(review.id)}...[/bold]\n")
    run_agent(
        config=config,
        topic=review.topic,
        objective=review.objective,
        store=store,
        review_id=review.id,
        sources=sources,
        extra_context=extra,
    )

    review.status = "completed"
    store.save(review)
    console.print(f"\n[green]Refresh of {_short_id(review.id)} completed.[/green]")


@lit.command("papers")
@click.argument("review_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def lit_papers(review_id: str, status: str | None):
    """List papers in a review."""
    _, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    filters = {"review_id": review.id}
    if status:
        filters["status"] = status
    papers = store.query(Paper, **filters)

    if not papers:
        console.print("No papers found.")
        return

    table = Table(title=f"Papers — {review.topic}")
    table.add_column("ID", style="cyan")
    table.add_column("Title", max_width=50)
    table.add_column("Year")
    table.add_column("Status")
    table.add_column("Citations")
    table.add_column("Source")

    for p in papers:
        table.add_row(
            _short_id(p.id),
            p.title[:50],
            str(p.year or "—"),
            p.status,
            str(p.citation_count or "—"),
            p.source,
        )

    console.print(table)


@lit.command("gaps")
@click.argument("review_id")
def lit_gaps(review_id: str):
    """Show latest coverage assessment and gaps."""
    _, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    coverages = store.query(CoverageAssessment, review_id=review.id)
    if not coverages:
        console.print("No coverage assessment yet.")
        return

    latest = coverages[0]
    text = f"[bold]Coverage Assessment[/bold] (confidence: {latest.confidence:.2f})\n\n"
    text += f"{latest.summary}\n\n"
    text += "[bold]Areas covered:[/bold]\n"
    for area in latest.areas_covered:
        text += f"  • {area}\n"
    text += "\n[bold]Gaps:[/bold]\n"
    for gap in latest.gaps:
        text += f"  • {gap}\n"
    if latest.next_actions:
        text += "\n[bold]Suggested next actions:[/bold]\n"
        for action in latest.next_actions:
            text += f"  • {action}\n"

    console.print(Panel(text, title=f"Gaps — {_short_id(review.id)}"))


@lit.command("notes")
@click.argument("review_id")
@click.option("--kind", "-k", default=None, help="Filter by note kind")
def lit_notes(review_id: str, kind: str | None):
    """Show research notes from a review."""
    _, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    filters = {"review_id": review.id}
    if kind:
        filters["kind"] = kind
    notes = store.query(ReviewNote, **filters)

    if not notes:
        console.print("No notes found.")
        return

    table = Table(title=f"Notes — {review.topic}")
    table.add_column("Kind", style="cyan")
    table.add_column("Content", max_width=70)
    table.add_column("Priority")
    table.add_column("Created")

    for n in notes:
        table.add_row(
            n.kind,
            n.content[:70],
            str(n.priority) if n.priority is not None else "—",
            n.created_at[:10],
        )

    console.print(table)


@lit.command("bibtex")
@click.argument("review_id")
@click.option("--output", "-o", default=None, help="Output file path")
def lit_bibtex(review_id: str, output: str | None):
    """Export BibTeX for relevant papers."""
    _, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    from research_os.agent.tools import export_bibtex

    sources = _make_sources(Config())
    ctx = {"store": store, "review_id": review.id, "sources": sources}
    result = export_bibtex(ctx)

    if not result.ok:
        console.print(f"[red]Error: {result.error}[/red]")
        return

    bibtex = result.data["bibtex"]
    count = result.data["count"]

    if output:
        with open(output, "w") as f:
            f.write(bibtex)
        console.print(f"Wrote {count} entries to {output}")
    else:
        console.print(bibtex)
        console.print(f"\n[dim]{count} entries[/dim]")


@lit.command("sota")
@click.argument("review_id")
def lit_sota(review_id: str):
    """Show state-of-the-art summary from a review."""
    _, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    summaries = store.query(SotaSummary, review_id=review.id)
    if not summaries:
        console.print("No SOTA summary yet. Run a review with save_sota_summary to generate one.")
        return

    latest = summaries[0]
    text = f"[bold]State of the Art — {review.topic}[/bold]\n\n"
    text += f"{latest.summary}\n\n"

    text += "[bold]Best Methods:[/bold]\n"
    for m in latest.best_methods:
        text += f"  - {m}\n"

    text += "\n[bold]Key Benchmarks:[/bold]\n"
    for b in latest.key_benchmarks:
        text += f"  - {b}\n"

    text += "\n[bold]Open-Source Implementations:[/bold]\n"
    for impl in latest.open_source_implementations:
        text += f"  - {impl}\n"

    text += "\n[bold]Open Problems:[/bold]\n"
    for p in latest.open_problems:
        text += f"  - {p}\n"

    text += "\n[bold]Trends:[/bold]\n"
    for t in latest.trends:
        text += f"  - {t}\n"

    console.print(Panel(text, title=f"SOTA — {_short_id(review.id)}"))


@lit.command("seed")
@click.argument("review_id")
@click.argument("url")
def lit_seed(review_id: str, url: str):
    """Add a seed paper to a review (no agent run)."""
    config, store = _setup()
    review = _find_review(store, review_id)
    if not review:
        return

    sources = _make_sources(config)
    from research_os.agent.tools import seed_paper

    ctx = {"store": store, "review_id": review.id, "sources": sources}
    result = seed_paper(ctx, url)

    if result.ok:
        console.print(f"Seeded: [bold]{result.data.get('title', url)}[/bold]")
    else:
        console.print(f"[red]Failed: {result.error}[/red]")


# ── Helpers ──────────────────────────────────────────────────────────


def _find_review(store: Store, review_id: str) -> LiteratureReview | None:
    """Find a review by full or prefix ID."""
    # Try exact match first
    review = store.get(LiteratureReview, review_id)
    if review:
        return review

    # Try prefix match
    reviews = store.query(LiteratureReview)
    matches = [r for r in reviews if r.id.startswith(review_id)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        console.print(f"[red]Ambiguous ID prefix '{review_id}' — matches {len(matches)} reviews.[/red]")
        return None
    else:
        console.print(f"[red]Review not found: {review_id}[/red]")
        return None
