"""Claude CLI provider — uses `claude -p` subprocess with prompt-based tool use."""

from __future__ import annotations

import json
import re
import subprocess
import shutil

from rich.console import Console

from research_os.providers.base import Provider, ProviderResponse, ToolCall

console = Console()

# Instructions appended to the system prompt so the model outputs tool calls
# in a parseable format.
TOOL_USE_INSTRUCTIONS = """

## Tool calling format

When you want to call a tool, output a JSON block wrapped in <tool_call> tags:

<tool_call>
{"name": "tool_name", "input": {"param1": "value1", "param2": "value2"}}
</tool_call>

You can make multiple tool calls in a single response. Each must be in its own <tool_call> block.

When you are done and have no more tool calls to make, do NOT output any <tool_call> blocks.

## Available tools

{tool_descriptions}
"""

# Format for feeding tool results back into the conversation
TOOL_RESULT_FORMAT = """<tool_result name="{name}">
{result}
</tool_result>"""


class ClaudeCLIProvider(Provider):
    """Provider that invokes `claude -p` as a subprocess.

    Tool use is handled via prompt engineering: tool schemas are embedded in the
    system prompt, and the model outputs <tool_call> XML blocks which we parse.
    """

    def __init__(
        self,
        model: str | None = None,
        command: str = "claude",
    ) -> None:
        self.model = model
        self.command = command
        self._verify_cli()

    def _verify_cli(self) -> None:
        if not shutil.which(self.command):
            raise RuntimeError(
                f"'{self.command}' not found in PATH. Install Claude Code CLI first."
            )

    def complete(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        # Build the full prompt from system + messages + tool schemas
        full_system = system + self._format_tool_instructions(tools) if tools else system
        prompt_text = self._build_prompt(full_system, messages)

        # Run claude -p
        cmd = [self.command, "-p", "--output-format", "json"]
        if self.model:
            cmd.extend(["--model", self.model])
        cmd.extend(["--system-prompt", full_system, "--dangerously-skip-permissions"])

        try:
            result = subprocess.run(
                cmd,
                input=prompt_text,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return ProviderResponse(
                text="", tool_calls=[], stop_reason="error"
            )

        if result.returncode != 0:
            console.print(f"[red]claude -p failed: {result.stderr[:200]}[/red]")
            return ProviderResponse(
                text=f"CLI error: {result.stderr[:200]}",
                tool_calls=[],
                stop_reason="error",
            )

        # Parse response
        raw_text = self._extract_text(result.stdout)
        tool_calls = self._parse_tool_calls(raw_text)
        clean_text = self._strip_tool_calls(raw_text)

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ProviderResponse(
            text=clean_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _format_tool_instructions(tools: list[dict]) -> str:
        parts = []
        for t in tools:
            schema_str = json.dumps(t.get("input_schema", {}), indent=2)
            parts.append(
                f"### {t['name']}\n{t.get('description', '')}\n\nParameters:\n```json\n{schema_str}\n```"
            )
        tool_descriptions = "\n\n".join(parts)
        return TOOL_USE_INSTRUCTIONS.format(tool_descriptions=tool_descriptions)

    @staticmethod
    def _build_prompt(system: str, messages: list[dict]) -> str:
        """Build a flat text prompt from the message history.

        The system prompt is passed via --system-prompt flag, so we only
        serialize the conversation turns here.
        """
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                # Handle structured content (tool results, etc.)
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block["text"])
                        elif block.get("type") == "tool_result":
                            name = block.get("name", "tool")
                            parts.append(
                                TOOL_RESULT_FORMAT.format(
                                    name=name, result=block.get("content", "")
                                )
                            )
                    elif isinstance(block, str):
                        parts.append(block)

        return "\n\n".join(parts)

    @staticmethod
    def _extract_text(stdout: str) -> str:
        """Extract text from claude -p output.

        With --output-format json, the output is a JSON object with a 'result' field.
        Falls back to raw stdout if parsing fails.
        """
        try:
            data = json.loads(stdout)
            # --output-format json returns {"type":"result","subtype":"success","result":"..."}
            if isinstance(data, dict):
                return data.get("result", stdout)
        except json.JSONDecodeError:
            pass
        return stdout

    @staticmethod
    def _parse_tool_calls(text: str) -> list[ToolCall]:
        """Extract <tool_call> blocks from text."""
        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)
        calls = []
        for match in matches:
            try:
                data = json.loads(match)
                calls.append(
                    ToolCall(
                        id=ToolCall.make_id(),
                        name=data["name"],
                        input=data.get("input", {}),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return calls

    @staticmethod
    def _strip_tool_calls(text: str) -> str:
        """Remove <tool_call> blocks from text, leaving just prose."""
        return re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL).strip()
