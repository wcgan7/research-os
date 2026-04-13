"""All read-only API endpoints for research-os."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from research_os.store.models import (
    Assessment,
    CapabilityRequest,
    CoverageAssessment,
    LiteratureReview,
    Paper,
    ReviewNote,
    ReviewReport,
    SearchRecord,
    SotaSummary,
)

router = APIRouter()

_SAFE_DIR_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _get_store():
    from research_os.api.app import get_store
    return get_store()


def _to_dict(record) -> dict[str, Any]:
    """Convert a dataclass record to a JSON-serializable dict."""
    return dataclasses.asdict(record)


def _paper_brief(paper: Paper) -> dict[str, Any]:
    """Paper dict without full_text for list endpoints."""
    d = dataclasses.asdict(paper)
    d.pop("full_text", None)
    return d


# ── Reviews ─────────────────────────────────────────────────────────


@router.get("/reviews")
def list_reviews():
    store = _get_store()
    reviews = store.query(LiteratureReview)
    result = []
    for r in reviews:
        papers = store.query(Paper, review_id=r.id)
        status_counts: dict[str, int] = {}
        for p in papers:
            status_counts[p.status] = status_counts.get(p.status, 0) + 1

        # Count distinct assessed papers, not total assessment records
        assessed_paper_ids = {a.paper_id for a in store.query(Assessment, review_id=r.id)}

        result.append({
            **_to_dict(r),
            "paper_count": len(papers),
            "assessment_count": len(assessed_paper_ids),
            "has_report": store.count(ReviewReport, review_id=r.id) > 0,
            "paper_status_counts": status_counts,
        })
    return result


@router.get("/reviews/{review_id}")
def get_review(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)
    papers = store.query(Paper, review_id=review.id)
    assessments = store.query(Assessment, review_id=review.id)

    status_counts: dict[str, int] = {}
    relevance_counts: dict[str, int] = {}
    assessed_paper_ids: set[str] = set()
    for p in papers:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1
    for a in assessments:
        # Use latest assessment per paper for relevance counts
        if a.paper_id not in assessed_paper_ids:
            relevance_counts[a.relevance] = relevance_counts.get(a.relevance, 0) + 1
            assessed_paper_ids.add(a.paper_id)

    # Determine if agent is currently running
    is_running = False
    log_root = Path.home() / ".research-os" / "logs" / review.id[:8]
    if log_root.is_dir():
        run_dirs = sorted(log_root.iterdir(), reverse=True)
        for rd in run_dirs:
            if not rd.is_dir():
                continue
            meta_path = rd / "meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    if not meta.get("completed_at"):
                        # Check staleness — if started > 4 hours ago, assume crashed
                        from datetime import datetime, timezone
                        started = meta.get("started_at")
                        if started:
                            try:
                                start_dt = datetime.fromisoformat(started)
                                age_hours = (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600
                                if age_hours < 4:
                                    is_running = True
                            except (ValueError, TypeError):
                                pass
                        else:
                            is_running = True
                except Exception:
                    pass
            break  # only check latest run

    # Get latest coverage confidence
    coverages = store.query(CoverageAssessment, review_id=review.id)
    latest_confidence = coverages[0].confidence if coverages else None

    return {
        **_to_dict(review),
        "is_running": is_running,
        "stats": {
            "paper_count": len(papers),
            "assessment_count": len(assessed_paper_ids),
            "search_count": store.count(SearchRecord, review_id=review.id),
            "note_count": store.count(ReviewNote, review_id=review.id),
            "coverage_count": store.count(CoverageAssessment, review_id=review.id),
            "has_report": store.count(ReviewReport, review_id=review.id) > 0,
            "papers_with_full_text": sum(1 for p in papers if p.full_text),
            "papers_with_resources": sum(1 for p in papers if p.resources),
            "paper_status_counts": status_counts,
            "relevance_counts": relevance_counts,
            "latest_confidence": latest_confidence,
        },
    }


# ── Report ──────────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/report")
def get_report(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)
    reports = store.query(ReviewReport, review_id=review.id)
    sotas = store.query(SotaSummary, review_id=review.id)
    return {
        "report": _to_dict(reports[0]) if reports else None,
        "sota_summary": _to_dict(sotas[0]) if sotas else None,
    }


# ── Papers ──────────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/papers")
def list_papers(
    review_id: str,
    status: str | None = Query(None),
    relevance: str | None = Query(None),
    source: str | None = Query(None),
    has_full_text: bool | None = Query(None),
    keyword: str | None = Query(None),
    sort: str = Query("relevance"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    store = _get_store()
    review = _find_review(store, review_id)

    filters: dict[str, Any] = {"review_id": review.id}
    if status:
        filters["status"] = status
    if source:
        filters["source"] = source
    papers = store.query(Paper, **filters)

    # Build assessment lookup
    assessments = store.query(Assessment, review_id=review.id)
    assessment_by_paper: dict[str, Assessment] = {}
    for a in assessments:
        assessment_by_paper[a.paper_id] = a

    # Filter by relevance (from assessment)
    if relevance:
        papers = [p for p in papers if assessment_by_paper.get(p.id) and assessment_by_paper[p.id].relevance == relevance]

    # Filter by full text
    if has_full_text is True:
        papers = [p for p in papers if p.full_text]
    elif has_full_text is False:
        papers = [p for p in papers if not p.full_text]

    # Filter by keyword
    if keyword:
        kw = keyword.lower()
        papers = [p for p in papers if kw in (p.title or "").lower() or kw in (p.abstract or "").lower()]

    # Sort
    relevance_order = {"essential": 0, "relevant": 1, "tangential": 2, "not_relevant": 3, "": 4}
    if sort == "relevance":
        papers.sort(key=lambda p: relevance_order.get(
            (assessment_by_paper.get(p.id) or Assessment()).relevance, 4
        ))
    elif sort == "year":
        papers.sort(key=lambda p: p.year or 0, reverse=True)
    elif sort == "citations":
        papers.sort(key=lambda p: p.citation_count or 0, reverse=True)
    elif sort == "title":
        papers.sort(key=lambda p: (p.title or "").lower())

    total = len(papers)
    papers = papers[offset:offset + limit]

    result = []
    for p in papers:
        d = _paper_brief(p)
        a = assessment_by_paper.get(p.id)
        d["assessment"] = _to_dict(a) if a else None
        result.append(d)

    return {"total": total, "papers": result}


@router.get("/reviews/{review_id}/papers/{paper_id}")
def get_paper(review_id: str, paper_id: str):
    store = _get_store()
    review = _find_review(store, review_id)

    paper = store.get(Paper, paper_id)
    if not paper or paper.review_id != review.id:
        raise HTTPException(404, "Paper not found")

    # Assessment
    assessments = store.query(Assessment, review_id=review.id, paper_id=paper_id)
    assessment = assessments[0] if assessments else None

    # Notes referencing this paper
    all_notes = store.query(ReviewNote, review_id=review.id)
    paper_notes = [n for n in all_notes if paper_id in (n.paper_ids or [])]

    # Searches that found this paper
    all_searches = store.query(SearchRecord, review_id=review.id)
    paper_searches = [s for s in all_searches if paper_id in (s.paper_ids or [])]

    # Connected papers (from assessment connections)
    connected_papers = []
    if assessment and assessment.connections:
        for conn_id in assessment.connections:
            connected = store.get(Paper, conn_id)
            if connected:
                connected_papers.append({"id": connected.id, "title": connected.title})

    d = _to_dict(paper)
    return {
        **d,
        "assessment": _to_dict(assessment) if assessment else None,
        "notes": [_to_dict(n) for n in paper_notes],
        "searches": [_to_dict(s) for s in paper_searches],
        "connected_papers": connected_papers,
    }


# ── Coverage ────────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/coverage")
def list_coverage(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)
    coverages = store.query(CoverageAssessment, review_id=review.id)
    return [_to_dict(c) for c in coverages]


# ── Notes ───────────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/notes")
def list_notes(review_id: str, kind: str | None = Query(None)):
    store = _get_store()
    review = _find_review(store, review_id)
    filters: dict[str, Any] = {"review_id": review.id}
    if kind:
        filters["kind"] = kind
    notes = store.query(ReviewNote, **filters)
    return [_to_dict(n) for n in notes]


# ── Searches ────────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/searches")
def list_searches(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)
    searches = store.query(SearchRecord, review_id=review.id)
    return [_to_dict(s) for s in searches]


# ── Resources ───────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/resources")
def list_resources(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)
    papers = store.query(Paper, review_id=review.id)

    resources_by_type: dict[str, list[dict]] = {}
    for p in papers:
        if not p.resources:
            continue
        for res_str in p.resources:
            try:
                res = json.loads(res_str) if isinstance(res_str, str) else res_str
            except json.JSONDecodeError:
                res = {"description": res_str, "type": "other", "url": ""}
            if not isinstance(res, dict):
                continue
            res_type = res.get("type", "other")
            entry = {
                **res,
                "paper_id": p.id,
                "paper_title": p.title,
                "paper_year": p.year,
            }
            resources_by_type.setdefault(res_type, []).append(entry)

    return resources_by_type


# ── Activity ────────────────────────────────────────────────────────


@router.get("/reviews/{review_id}/activity")
def get_activity(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)

    events: list[dict[str, Any]] = []

    # Searches
    for s in store.query(SearchRecord, review_id=review.id):
        events.append({
            "type": "search",
            "timestamp": s.created_at,
            "summary": f"Searched {s.source}: \"{s.query}\" \u2192 {s.result_count} results",
            "data": {"search_id": s.id, "source": s.source, "query": s.query},
        })

    # Assessments — build paper title lookup to avoid N+1
    papers = store.query(Paper, review_id=review.id)
    paper_titles = {p.id: p.title for p in papers}
    for a in store.query(Assessment, review_id=review.id):
        title = paper_titles.get(a.paper_id, a.paper_id)[:60]
        events.append({
            "type": "assessment",
            "timestamp": a.created_at,
            "summary": f"Assessed \"{title}\" as {a.relevance}",
            "data": {"paper_id": a.paper_id, "relevance": a.relevance},
        })

    # Coverage
    for c in store.query(CoverageAssessment, review_id=review.id):
        events.append({
            "type": "coverage",
            "timestamp": c.created_at,
            "summary": f"Coverage assessment: {c.confidence:.0%} confidence",
            "data": {"confidence": c.confidence, "gaps_count": len(c.gaps)},
        })

    # Notes
    for n in store.query(ReviewNote, review_id=review.id):
        events.append({
            "type": "note",
            "timestamp": n.created_at,
            "summary": f"Note ({n.kind}): {n.content[:80]}",
            "data": {"note_id": n.id, "kind": n.kind},
        })

    # Reports
    for r in store.query(ReviewReport, review_id=review.id):
        events.append({
            "type": "report",
            "timestamp": r.created_at,
            "summary": "Wrote review report",
            "data": {"report_id": r.id},
        })

    events.sort(key=lambda e: e["timestamp"])
    return events


# ── Capability Requests ─────────────────────────────────────────────


@router.get("/reviews/{review_id}/capability-requests")
def list_capability_requests(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)
    reqs = store.query(CapabilityRequest, review_id=review.id)
    return [_to_dict(r) for r in reqs]


# ── Logs ────────────────────────────────────────────────────────────


def _validate_path_segment(segment: str) -> None:
    """Reject path segments that could traverse the filesystem."""
    if not _SAFE_DIR_RE.match(segment):
        raise HTTPException(400, f"Invalid path segment: {segment}")


@router.get("/reviews/{review_id}/logs")
def get_logs(review_id: str):
    store = _get_store()
    review = _find_review(store, review_id)

    log_root = Path.home() / ".research-os" / "logs" / review.id[:8]
    if not log_root.is_dir():
        return {"runs": []}

    runs = []
    for run_dir in sorted(log_root.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        meta_path = run_dir / "meta.json"
        stdout_path = run_dir / "stdout.log"
        meta = None
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:
                pass
        stdout_size = stdout_path.stat().st_size if stdout_path.exists() else 0
        runs.append({
            "dir": run_dir.name,
            "meta": meta,
            "stdout_size": stdout_size,
        })
    return {"runs": runs}


@router.get("/reviews/{review_id}/logs/{run_dir}/stdout")
def get_log_stdout(review_id: str, run_dir: str, tail: int = Query(500, ge=1, le=5000)):
    """Get the last N lines of a run's stdout log."""
    store = _get_store()
    review = _find_review(store, review_id)
    _validate_path_segment(run_dir)

    log_root = (Path.home() / ".research-os" / "logs" / review.id[:8]).resolve()
    log_path = (log_root / run_dir / "stdout.log").resolve()
    # Ensure resolved path is under the expected root
    if not log_path.is_relative_to(log_root):
        raise HTTPException(403, "Access denied")
    if not log_path.exists():
        raise HTTPException(404, "Log file not found")

    all_lines = log_path.read_text(errors="replace").splitlines()
    total = len(all_lines)
    lines = all_lines[-tail:] if total > tail else all_lines
    return {"lines": lines, "total_lines": total}


@router.get("/reviews/{review_id}/logs/{run_dir}/parsed")
def get_log_parsed(review_id: str, run_dir: str):
    """Parse streaming JSON log into structured events for display."""
    store = _get_store()
    review = _find_review(store, review_id)
    _validate_path_segment(run_dir)

    log_root = (Path.home() / ".research-os" / "logs" / review.id[:8]).resolve()
    log_path = (log_root / run_dir / "stdout.log").resolve()
    if not log_path.is_relative_to(log_root):
        raise HTTPException(403, "Access denied")
    if not log_path.exists():
        raise HTTPException(404, "Log file not found")

    events: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0

    for line in log_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        record_type = obj.get("type")

        if record_type == "system" and obj.get("subtype") == "init":
            events.append({
                "type": "system",
                "content": f"Session started — model: {obj.get('model', '?')}, tools: {len(obj.get('tools', []))}",
            })

        elif record_type == "assistant":
            msg = obj.get("message", {})
            usage = msg.get("usage", {})
            if usage:
                total_input_tokens += usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)

            for content in msg.get("content", []):
                ctype = content.get("type")
                if ctype == "text":
                    text = content.get("text", "").strip()
                    if text:
                        events.append({"type": "text", "content": text})
                elif ctype == "tool_use":
                    tool_name = content.get("name", "?")
                    inp = content.get("input", {})
                    description = inp.get("description", "")
                    command = inp.get("command", "")
                    # For Bash tool calls via research-os CLI, extract the tool name
                    display = description or command[:120] if command else ""
                    if tool_name == "Bash" and "tool call" in command:
                        parts = command.split("tool call")
                        if len(parts) > 1:
                            rest = parts[1].strip().split()
                            if len(rest) >= 2:
                                tool_name = f"Bash → {rest[1]}"
                                # Extract JSON args if present
                                if len(rest) >= 3:
                                    display = description or rest[1]
                    elif tool_name == "Bash" and "tool summary" in command:
                        tool_name = "Bash → summary"
                    elif tool_name == "WebSearch":
                        query = inp.get("query", "")
                        display = query
                    elif tool_name == "WebFetch":
                        url = inp.get("url", "")
                        display = url[:100]

                    events.append({
                        "type": "tool_call",
                        "tool": tool_name,
                        "description": display,
                        "tool_id": content.get("id", ""),
                    })
                # Skip thinking blocks

        elif record_type == "user":
            msg = obj.get("message", {})
            tur = obj.get("tool_use_result") or {}
            if not isinstance(tur, dict):
                tur = {}
            stdout = tur.get("stdout", "")
            stderr = tur.get("stderr", "")
            is_error = False

            for content in msg.get("content", []):
                if content.get("type") == "tool_result" and content.get("is_error"):
                    is_error = True

            if is_error or stderr:
                error_text = stderr or stdout[:200]
                events.append({
                    "type": "tool_error",
                    "content": error_text[:300],
                })
            elif stdout:
                # Summarize tool result
                preview = stdout[:200]
                try:
                    result = json.loads(stdout.split("\n")[0])
                    if isinstance(result, dict):
                        if result.get("ok") and result.get("data"):
                            data = result["data"]
                            if isinstance(data, dict):
                                # Compact summary of the result
                                keys = list(data.keys())[:4]
                                parts = []
                                for k in keys:
                                    v = data[k]
                                    if isinstance(v, (int, float)):
                                        parts.append(f"{k}: {v}")
                                    elif isinstance(v, str) and len(v) < 60:
                                        parts.append(f"{k}: {v}")
                                    elif isinstance(v, list):
                                        parts.append(f"{k}: [{len(v)} items]")
                                preview = ", ".join(parts) if parts else preview
                        elif not result.get("ok"):
                            preview = f"Error: {result.get('error', '?')}"
                except (json.JSONDecodeError, IndexError):
                    pass

                events.append({
                    "type": "tool_result",
                    "content": preview,
                })

        elif record_type == "result":
            events.append({
                "type": "result",
                "content": "Agent finished",
            })

    return {
        "events": events,
        "stats": {
            "total_events": len(events),
            "tool_calls": sum(1 for e in events if e["type"] == "tool_call"),
            "errors": sum(1 for e in events if e["type"] == "tool_error"),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
    }


# ── Actions ─────────────────────────────────────────────────────────


@router.post("/reviews")
def create_review(body: dict[str, Any]):
    """Start a new literature review. Launches agent in background."""
    topic = body.get("topic", "").strip()
    objective = body.get("objective", "").strip()
    seed_urls = body.get("seed_urls") or []

    if not topic:
        raise HTTPException(400, "Topic is required")
    if not objective:
        raise HTTPException(400, "Objective is required")

    import threading
    from research_os.launcher import launch_review

    result_holder: dict[str, Any] = {}

    def run():
        try:
            result = launch_review(
                topic=topic,
                objective=objective,
                seed_urls=seed_urls if seed_urls else None,
            )
            result_holder.update(result)
        except Exception as e:
            result_holder["error"] = str(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    # Wait for review ID to be created (launch_review creates the review record
    # before starting the subprocess, so this should be fast)
    thread.join(timeout=10.0)

    if "error" in result_holder:
        raise HTTPException(500, result_holder["error"])
    if not result_holder.get("review_id"):
        raise HTTPException(500, "Review launch timed out — check server logs")

    return {
        "review_id": result_holder["review_id"],
        "log_dir": result_holder.get("log_dir"),
        "status": "launched",
    }


@router.post("/reviews/{review_id}/continue")
def continue_review(review_id: str, body: dict[str, Any] | None = None):
    """Continue an existing review. Relaunches agent in background."""
    store = _get_store()
    review = _find_review(store, review_id)

    # Prevent duplicate launches (with same staleness check as is_running)
    log_root = Path.home() / ".research-os" / "logs" / review.id[:8]
    if log_root.is_dir():
        from datetime import datetime, timezone
        for rd in sorted(log_root.iterdir(), reverse=True):
            if not rd.is_dir():
                continue
            meta_path = rd / "meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    if not meta.get("completed_at"):
                        started = meta.get("started_at")
                        if started:
                            try:
                                start_dt = datetime.fromisoformat(started)
                                age_hours = (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600
                                if age_hours < 4:
                                    raise HTTPException(409, "Agent is already running for this review")
                            except (ValueError, TypeError):
                                pass
                except json.JSONDecodeError:
                    pass
            break

    import threading
    from research_os.launcher import launch_review

    result_holder: dict[str, Any] = {}

    def run():
        try:
            result = launch_review(
                topic=review.topic,
                objective=review.objective,
                review_id=review.id,
            )
            result_holder.update(result)
        except Exception as e:
            result_holder["error"] = str(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=5.0)

    if "error" in result_holder:
        raise HTTPException(500, result_holder["error"])

    return {
        "review_id": review.id,
        "log_dir": result_holder.get("log_dir"),
        "status": "launched",
    }


@router.post("/reviews/{review_id}/seed")
def seed_paper_endpoint(review_id: str, body: dict[str, Any]):
    """Seed a paper into a review by URL or ID."""
    store = _get_store()
    review = _find_review(store, review_id)
    url_or_id = body.get("url_or_id", "").strip()
    if not url_or_id:
        raise HTTPException(400, "url_or_id is required")

    from research_os.agent.tools import seed_paper
    import httpx
    from research_os.config import Config
    from research_os.sources.cache import Cache
    from research_os.sources.arxiv import ArxivClient
    from research_os.sources.semantic_scholar import SemanticScholarClient
    from research_os.sources.openalex import OpenAlexClient

    cfg = Config()
    with httpx.Client(timeout=30.0, follow_redirects=True) as http:
        cache = Cache(cfg.cache_dir)
        sources = {
            "semantic_scholar": SemanticScholarClient(http, cache, api_key=cfg.s2_api_key),
            "arxiv": ArxivClient(http, cache),
            "openalex": OpenAlexClient(http, cache),
        }
        ctx = {"store": store, "review_id": review.id, "sources": sources}
        result = seed_paper(ctx, url_or_id)

    if not result.ok:
        raise HTTPException(400, result.error)
    return result.data


@router.post("/reviews/{review_id}/papers/{paper_id}/fetch-text")
def fetch_text_endpoint(review_id: str, paper_id: str):
    """Fetch full text for a paper."""
    store = _get_store()
    review = _find_review(store, review_id)

    from research_os.agent.tools import fetch_paper_text
    import httpx
    from research_os.config import Config
    from research_os.sources.cache import Cache
    from research_os.sources.arxiv import ArxivClient
    from research_os.sources.semantic_scholar import SemanticScholarClient
    from research_os.sources.openalex import OpenAlexClient

    cfg = Config()
    with httpx.Client(timeout=30.0, follow_redirects=True) as http:
        cache = Cache(cfg.cache_dir)
        sources = {
            "semantic_scholar": SemanticScholarClient(http, cache, api_key=cfg.s2_api_key),
            "arxiv": ArxivClient(http, cache),
            "openalex": OpenAlexClient(http, cache),
        }
        ctx = {"store": store, "review_id": review.id, "sources": sources}
        result = fetch_paper_text(ctx, paper_id)
    if not result.ok:
        raise HTTPException(400, result.error)
    return result.data


# ── Helpers ─────────────────────────────────────────────────────────


def _find_review(store, review_id: str) -> LiteratureReview:
    review = store.get(LiteratureReview, review_id)
    if review:
        return review
    # Try prefix match (min 6 chars to avoid ambiguity)
    if len(review_id) >= 6:
        reviews = store.query(LiteratureReview)
        matches = [r for r in reviews if r.id.startswith(review_id)]
        if len(matches) == 1:
            return matches[0]
    raise HTTPException(404, f"Review not found: {review_id}")
