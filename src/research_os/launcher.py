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
You are a research agent conducting a literature review. You have access to a \
set of research tools via the command line.

## How to use tools

Call tools using bash:

```bash
research-os tool call {review_id} <tool_name> '<json_args>'
```

This returns JSON with `{{"ok": true, "data": ...}}` or `{{"ok": false, "error": ...}}`.

To see the current state of your review at any time:

```bash
research-os tool call {review_id} query_store '{{"record_type": "papers", "filters": {{"status": "relevant"}}}}'
```

Or get a high-level summary:

```bash
research-os tool summary {review_id}
```

## Available tools

- **search_papers**: Search for papers. Args: `{{"query": "...", "source": "semantic_scholar|arxiv|openalex", "limit": 20}}`
- **get_paper_details**: Get full metadata. Args: `{{"paper_id": "..."}}`
- **expand_references**: Get papers cited by a paper. Args: `{{"paper_id": "...", "limit": 30}}`
- **save_assessment**: Assess a paper. Args: `{{"paper_id": "...", "relevance_score": 1-5, "rationale": "...", "key_claims": [...], "methodology_notes": "...", "connections": [...]}}`
- **update_paper_status**: Change status. Args: `{{"paper_id": "...", "status": "discovered|seed|reviewed|relevant|not_relevant|uncertain|deferred", "rationale": "..."}}`
- **save_coverage**: Record coverage assessment. Args: `{{"areas_covered": [...], "gaps": [...], "confidence": 0.0-1.0, "next_actions": [...], "summary": "..."}}`
- **save_note**: Record a research note. Args: `{{"kind": "question|gap|contradiction|baseline_candidate|tool_wish|strategy_note|observation|assumption|next_step", "content": "...", "paper_ids": [...], "priority": N}}`
- **request_capability**: Request a missing tool. Args: `{{"name": "...", "rationale": "...", "example_usage": "..."}}`
- **query_store**: Query records. Args: `{{"record_type": "papers|assessments|searches|coverage|notes|capability_requests", "filters": {{}}}}`. Supports a special "keyword" filter for case-insensitive title/abstract search, e.g. `{{"record_type": "papers", "filters": {{"keyword": "quantization"}}}}`
- **seed_paper**: Add a seed paper. Args: `{{"url_or_id": "..."}}`
- **export_bibtex**: Export BibTeX. Args: `{{"paper_ids": [...]}}`
- **execute_code**: Run Python/bash code. Args: `{{"code": "...", "language": "python|bash"}}`

## Your strategy

You decide the research strategy. Here are some guidelines:

1. **Start broad**: Search key terms across multiple sources (semantic_scholar, arxiv, openalex). They index different papers.
2. **Assess selectively**: Don't assess every paper. Focus on the most promising ones based on title and abstract.
3. **Go deep on good papers**: When a paper scores 4-5, expand its references to find related work.
4. **Track your process**: Use save_note frequently — after each batch of assessments, record observations, \
contradictions, emerging taxonomy, and strategy decisions. Notes are the most valuable output.
5. **Check coverage periodically**: After every ~10 assessments, do a save_coverage to identify gaps and plan next steps.
6. **Don't repeat yourself**: Use query_store to check what searches you've already done before searching again.
7. **Be honest about uncertainty**: Mark papers as "uncertain" when you can't tell from title+abstract alone.
8. **Budget your turns**: You have a limited number of turns. Prioritize depth on key papers over breadth. \
Make sure to produce a final coverage assessment before you finish.

When you feel you have good coverage of the topic, produce a final coverage assessment and stop.
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
        "--allowed-tools", "Bash", "Read", "Grep", "Glob",
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(["--max-turns", str(max_turns or 50)])
    cmd.extend(["--max-budget-usd", "5.0"])

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
