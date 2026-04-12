"""Launch a literature review agent via claude -p.

This module builds a prompt and invokes `claude -p` as a subprocess.
The claude agent uses Bash to call `research-os tool call <review_id> <tool> '<json>'`
for each tool operation, making it a true autonomous agent.

Logs (stdout/stderr) are captured to timestamped files.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from research_os.config import Config
from research_os.store.db import get_connection, init_schema
from research_os.store.models import LiteratureReview
from research_os.store.store import Store


SYSTEM_PROMPT = """\
You are a research agent conducting a thorough literature review. Your goal is to produce a \
comprehensive, well-organized understanding of the field that could serve as the foundation \
for further research.

## How to use tools

Call tools using bash:

```bash
research-os tool call {review_id} <tool_name> '<json_args>'
```

For large JSON args (e.g., big SOTA summaries), pipe via stdin:
```bash
cat /tmp/args.json | research-os tool call {review_id} <tool_name> -
```

Returns JSON: `{{"ok": true, "data": ...}}` or `{{"ok": false, "error": ...}}`.

Quick commands:
```bash
research-os tool summary {review_id}
research-os tool call {review_id} query_store '{{"record_type": "papers", "filters": {{"status": "relevant"}}}}'
```

## Available tools

- **search_papers**: Search academic APIs. Args: `{{"query": "...", "source": "semantic_scholar|arxiv|openalex", "limit": 20}}`
- **get_paper_details**: Full metadata. Args: `{{"paper_id": "..."}}`
- **expand_references**: Cited-by expansion. Args: `{{"paper_id": "...", "limit": 30}}`
- **save_assessment**: Deep paper assessment. Args: `{{"paper_id": "...", "relevance": "essential|relevant|tangential|not_relevant", "rationale": "...", "key_claims": [...], "methodology_notes": "...", "connections": [...]}}`
- **batch_triage**: Rapid bulk triage. Args: `{{"decisions": [{{"paper_id": "...", "relevance": "relevant|not_relevant|uncertain|deferred", "reason": "...", "key_claims": [...]}}]}}`
- **update_paper_status**: Change status. Args: `{{"paper_id": "...", "status": "discovered|seed|reviewed|relevant|not_relevant|uncertain|deferred"}}`
- **update_paper_resources**: Attach resources (code, datasets, demos, blogs, etc.). Args: `{{"paper_id": "...", "resources": [{{"type": "code|dataset|demo|blog|benchmark|other", "url": "...", "description": "..."}}]}}`
- **save_coverage**: Coverage check. Args: `{{"areas_covered": [...], "gaps": [...], "confidence": 0.0-1.0, "next_actions": [...], "summary": "..."}}`
- **save_review_report**: The final deliverable — a structured literature review report with sections: landscape, methods, sota, resources, gaps, trends, conclusions. Each section is prose markdown.
- **save_note**: Research note. Args: `{{"kind": "question|gap|contradiction|baseline_candidate|tool_wish|strategy_note|observation|assumption|next_step", "content": "..."}}`
- **seed_paper**: Add paper by URL/ID. Args: `{{"url_or_id": "..."}}`
- **query_store**: Read records. Args: `{{"record_type": "papers|assessments|searches|coverage|notes|report", "filters": {{}}}}`
- **export_bibtex**: Export citations. Args: `{{"paper_ids": [...]}}`
- **execute_code**: Run code. Args: `{{"code": "...", "language": "python|bash"}}`

## Web Search (USE THIS — it's critical for completeness)

You have a native **WebSearch** tool — use it directly (not through search_papers) to:
- Find very recent papers that academic APIs haven't indexed yet (this is essential!)
- Search for specific paper names or authors
- Find blog posts, code repos, benchmarks, and other resources
- Verify claims or find additional context

**You MUST use WebSearch at least 2-3 times during a review**, especially for:
- "latest [topic] papers 2025 2026" queries to catch very recent work
- Specific paper names you've heard about but haven't found in academic APIs

When web search reveals a paper, use **seed_paper** to add it by arXiv URL/ID or DOI.

## Research Strategy

### Phase 1: Broad Discovery
- **Start with WebSearch** to get the lay of the land — search for recent surveys, blog posts, \
and "awesome" lists about the topic. This gives you the latest landscape faster than academic APIs.
- Then search academic sources (semantic_scholar, arxiv, openalex) for systematic coverage
- Use WebSearch again for specific recent papers or papers with unusual names that APIs miss
- When WebSearch reveals papers, use seed_paper to add them by arXiv URL/ID or DOI
- Seed any landmark papers you know by arXiv ID

### Phase 2: Triage Everything (do this EARLY)
- Use batch_triage to process ALL discovered papers — leave nothing in "discovered" status
- Process papers in batches of 10-15 at a time
- For essential/highly relevant papers, follow up with save_assessment for detailed notes

### Phase 3: Deep Exploration
- expand_references on essential papers to find related work
- WebSearch for specific papers mentioned in key works but not yet in the database
- Look for code repos, datasets, and benchmarks — use update_paper_resources

### Phase 4: Gap Filling
- save_coverage to assess what's missing
- Targeted searches to fill specific gaps
- **Do a dedicated "latest breakthroughs" WebSearch**: search for "latest [topic] papers ICLR ICML \
NeurIPS 2025 2026 breakthrough" and similar queries. New high-impact papers often appear on \
Twitter/X, blog posts, and conference pages before academic APIs index them.
- Triage any new discoveries immediately

### Phase 5: Synthesis (CRITICAL — don't skip this)
- **save_review_report**: the most important deliverable. Write a real literature review with:
  - **landscape**: Taxonomy and overview of the field — what categories of approaches exist
  - **methods**: Detailed comparison of major methods with tradeoffs and results
  - **sota**: Current state-of-the-art — what works best, on which benchmarks, under what conditions
  - **resources**: Available code (with URLs), datasets, benchmarks, tools
  - **gaps**: Open problems, limitations, under-explored areas
  - **trends**: Where the field is heading, recent shifts, emerging directions
  - **conclusions**: What a researcher starting in this area should know
- Final save_coverage assessment
- save_note for any remaining questions or observations

Write each section as prose markdown, not bullet lists. A good report reads like a survey paper.

### Key Principles
- **Balance discovery and assessment**: Don't spend all your turns searching. Triage early and often.
- **Track resources diligently**: Code repos, datasets, demos — these are what researchers actually need
- **Note contradictions**: When papers disagree, record it
- **Don't repeat searches**: Use query_store to check past searches before searching again
- **Always produce a SOTA summary**: Even if you run low on turns, synthesize what you have
"""


USER_PROMPT_TEMPLATE = """\
Conduct a literature review on: **{topic}**

Objective: {objective}

{seed_instructions}

Start by querying the store to check if there's any existing work on this review, \
then begin searching and assessing papers. Work autonomously until you have good coverage.
"""


def _make_log_dir(review_id: str) -> Path:
    """Create a timestamped log directory for this run."""
    log_root = Path.home() / ".research-os" / "logs" / review_id[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_dir = log_root / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def launch_review(
    topic: str,
    objective: str,
    seed_urls: list[str] | None = None,
    review_id: str | None = None,
    model: str | None = None,
    max_turns: int | None = None,
) -> dict:
    """Launch a literature review using claude -p.

    Returns dict with review_id, log_dir, and process info.
    """
    cfg = Config()
    conn = get_connection(cfg.db_path)
    init_schema(conn)
    store = Store(conn)

    # Create or find review
    if review_id:
        review = store.get(LiteratureReview, review_id)
        if not review:
            reviews = store.query(LiteratureReview)
            matches = [r for r in reviews if r.id.startswith(review_id)]
            if len(matches) == 1:
                review = matches[0]
            else:
                raise ValueError(f"Review not found: {review_id}")
    else:
        review = LiteratureReview(topic=topic, objective=objective, status="active")
        store.save(review)

    # Seed papers if provided
    seed_instructions = ""
    if seed_urls:
        from research_os.agent.tools import seed_paper
        import httpx
        from research_os.sources.cache import Cache
        from research_os.sources.arxiv import ArxivClient
        from research_os.sources.semantic_scholar import SemanticScholarClient
        from research_os.sources.openalex import OpenAlexClient
        http = httpx.Client(timeout=30.0, follow_redirects=True)
        cache = Cache(cfg.cache_dir)
        sources = {
            "semantic_scholar": SemanticScholarClient(http, cache, api_key=cfg.s2_api_key),
            "arxiv": ArxivClient(http, cache),
            "openalex": OpenAlexClient(http, cache),
        }
        ctx = {"store": store, "review_id": review.id, "sources": sources}
        seeded = []
        for url in seed_urls:
            result = seed_paper(ctx, url)
            if result.ok:
                seeded.append(result.data.get("title", url))
        if seeded:
            seed_instructions = f"Seed papers have already been added: {', '.join(seeded)}\nStart by expanding their references."

    # Build prompts
    system = SYSTEM_PROMPT.format(review_id=review.id)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        topic=topic,
        objective=objective,
        seed_instructions=seed_instructions,
    )

    # Set up logging
    log_dir = _make_log_dir(review.id)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    meta_path = log_dir / "meta.json"

    # Save metadata
    meta = {
        "review_id": review.id,
        "topic": topic,
        "objective": objective,
        "model": model or "default",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "seed_urls": seed_urls or [],
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    # Write system prompt to file for --append-system-prompt-file
    system_file = log_dir / "system_prompt.md"
    system_file.write_text(system)

    # Build claude -p command
    cmd = [
        "claude", "-p",
        "--dangerously-skip-permissions",
        "--append-system-prompt-file", str(system_file),
        "--output-format", "stream-json",
        "--verbose",
        "--allowed-tools", "Bash", "Read", "Grep", "Glob", "WebSearch",
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(["--max-turns", str(max_turns or 50)])
    cmd.extend(["--max-budget-usd", "10.0"])

    # Ensure research-os is available in PATH
    venv_bin = Path(sys.executable).parent
    env = os.environ.copy()
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

    print(f"Review ID: {review.id}")
    print(f"Log dir: {log_dir}")
    print(f"Launching claude -p ...")

    # Launch as subprocess with log capture
    with open(stdout_path, "w") as stdout_f, open(stderr_path, "w") as stderr_f:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=stdout_f,
            stderr=stderr_f,
            text=True,
            cwd=str(Path.home() / "Documents" / "research-os"),
            env=env,
        )
        proc.communicate(input=user_prompt)

    # Update review status
    review.status = "completed"
    store.save(review)

    # Save completion metadata
    meta["completed_at"] = datetime.now(timezone.utc).isoformat()
    meta["exit_code"] = proc.returncode
    meta_path.write_text(json.dumps(meta, indent=2))

    print(f"\nCompleted with exit code {proc.returncode}")
    print(f"Logs: {log_dir}")

    return {
        "review_id": review.id,
        "log_dir": str(log_dir),
        "exit_code": proc.returncode,
    }
