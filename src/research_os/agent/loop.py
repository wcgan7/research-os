"""LLM tool-use conversation loop for the literature review agent."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel

from research_os.agent.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from research_os.config import Config
from research_os.providers.base import Provider
from research_os.types import ToolResult

console = Console()


SYSTEM_PROMPT_TEMPLATE = """\
You are a research assistant conducting a literature review.

**Topic:** {topic}
**Objective:** {objective}

## Your task

Search for relevant academic papers across multiple sources (Semantic Scholar, arXiv, OpenAlex). \
Assess each paper's relevance. Track what you've covered, identify gaps, and \
produce a state-of-the-art summary. Record everything using the provided tools.

## How to work

You decide the strategy: what to search, which sources to use, when to go deeper on \
references, when to step back and assess coverage, and when you're done.

Start by searching for key terms related to the topic. Branch out as you discover subtopics \
and related work. Use expand_references on highly relevant papers to find related work, and \
expand_citations to find newer papers that build on them. Periodically assess coverage to identify gaps.

**Triage ALL discovered papers** — don't leave them in "discovered" status. Use batch_triage to \
quickly process papers in bulk. For the most important papers, use save_assessment for detailed notes.

**Track resources**: When assessing papers, note any useful resources — code repos, datasets, \
benchmarks, demos, blog posts. Use update_paper_resources to record these.

**Produce a review report** — but don't stop there. Use save_review_report to write a structured \
literature review covering the landscape, methods comparison, SOTA results, available resources, \
gaps, trends, and conclusions. Then critically evaluate it: which sections are thin? What claims \
rest on only one paper? What gaps did you mention but never search for? Run save_coverage AFTER \
writing the report — it will be more honest. If actionable gaps remain, go back to targeted \
discovery, triage/assess the new papers, and rewrite the report. Stop only when searching for \
remaining gaps yields nothing new.

Use save_note to record open questions, contradictions, assumptions, observations, or strategy \
decisions as you work.

## Tips

- Search multiple sources for the same concept — they index different papers
- Use your native WebSearch tool for specific paper names or to find papers that academic APIs miss
- Never guess arXiv IDs from memory — they are frequently wrong. Use URLs from search results or search by title
- When a paper looks highly relevant, expand its references and call fetch_paper_text to read its full content
- Call fetch_paper_text on ALL essential and relevant papers — abstracts are not enough for a good review
- Use batch_triage to quickly process many papers instead of individual assessments
- Track resources (code, datasets, demos, blogs) — these are critical for downstream work
- Keep notes as you go — especially contradictions and surprising findings
{extra_context}"""


REFRESH_CONTEXT_TEMPLATE = """
## Previous work on this review

Previous searches:
{searches}

Latest coverage assessment:
{coverage}

Notes from previous sessions:
{notes}

Your task now: search for new work published since the last review, re-evaluate any gaps, \
and update coverage. Build on the previous work — don't repeat searches that already returned results.
"""


def _build_system_prompt(
    topic: str,
    objective: str,
    extra_context: str = "",
) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        topic=topic,
        objective=objective,
        extra_context=extra_context,
    )


def _dispatch_tool(
    name: str,
    params: dict[str, Any],
    ctx: dict[str, Any],
) -> ToolResult:
    """Call a tool function by name."""
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return ToolResult(ok=False, error=f"Unknown tool: {name}")

    try:
        return fn(ctx, **params)
    except Exception as e:
        return ToolResult(ok=False, error=f"Tool error ({name}): {e}")


def run_agent(
    config: Config,
    topic: str,
    objective: str,
    store: Any,
    review_id: str,
    sources: dict[str, Any],
    extra_context: str = "",
    provider: Provider | None = None,
) -> list[dict]:
    """Run the tool-use agent loop.

    Uses the provider from config (or an explicit override) to talk to the LLM.
    Returns the full message history.
    """
    if provider is None:
        provider = config.make_provider()

    system_prompt = _build_system_prompt(topic, objective, extra_context)
    ctx = {"store": store, "review_id": review_id, "sources": sources}

    messages: list[dict] = [
        {"role": "user", "content": f"Please conduct a literature review on: {topic}\n\nObjective: {objective}"}
    ]

    for turn in range(config.max_agent_turns):
        try:
            response = provider.complete(system_prompt, messages, TOOL_DEFINITIONS)
        except Exception as e:
            console.print(f"[red]Provider error: {e}[/red]")
            return messages

        # Print any text from the model
        if response.text:
            console.print(Panel(response.text, title=f"Agent (turn {turn + 1})", border_style="blue"))

        # Build assistant message for conversation history
        assistant_content = []
        if response.text:
            assistant_content.append({"type": "text", "text": response.text})
        for tc in response.tool_calls:
            assistant_content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input,
            })

        messages.append({"role": "assistant", "content": assistant_content})

        # If no tool calls and stop reason is end_turn, we're done
        if not response.tool_calls and response.stop_reason == "end_turn":
            console.print("[green]Agent finished.[/green]")
            break

        # Dispatch tool calls
        tool_results = []
        for tc in response.tool_calls:
            console.print(f"  [dim]→ {tc.name}({_summarize_params(tc.input)})[/dim]")
            result = _dispatch_tool(tc.name, tc.input, ctx)
            status = "[green]ok[/green]" if result.ok else "[red]error[/red]"
            console.print(f"  [dim]  {status}[/dim]")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "name": tc.name,
                "content": result.to_agent_string(),
            })

        messages.append({"role": "user", "content": tool_results})
    else:
        console.print(f"[yellow]Agent reached max turns ({config.max_agent_turns}).[/yellow]")

    return messages


def _summarize_params(params: dict) -> str:
    """Create a short string summary of tool parameters for logging."""
    parts = []
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 40:
            v = v[:37] + "..."
        elif isinstance(v, list) and len(v) > 3:
            v = f"[{len(v)} items]"
        parts.append(f"{k}={v!r}")
    return ", ".join(parts)
