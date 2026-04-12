"""Anthropic API provider — native tool_use via the SDK."""

from __future__ import annotations

import time

import anthropic
from rich.console import Console

from research_os.providers.base import Provider, ProviderResponse, ToolCall

console = Console()


class AnthropicAPIProvider(Provider):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        for attempt in range(4):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    system=system,
                    messages=messages,
                    tools=tools,
                    max_tokens=4096,
                )
                return self._parse_response(response)
            except anthropic.RateLimitError:
                if attempt < 3:
                    wait = 2 ** (attempt + 1)
                    console.print(f"[yellow]Rate limited, waiting {wait}s...[/yellow]")
                    time.sleep(wait)
                else:
                    raise

    @staticmethod
    def _parse_response(response) -> ProviderResponse:
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, input=block.input)
                )

        return ProviderResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
        )
