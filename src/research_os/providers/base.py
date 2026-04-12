"""Provider abstraction for LLM backends."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    input: dict

    @staticmethod
    def make_id() -> str:
        return f"tc_{uuid.uuid4().hex[:12]}"


@dataclass
class ProviderResponse:
    """Unified response from any provider."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn" | "tool_use" | "max_tokens"


class Provider(ABC):
    """Interface for LLM providers that support tool use."""

    @abstractmethod
    def complete(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        """Send a conversation to the model and get a response.

        Args:
            system: System prompt text.
            messages: Conversation history in Anthropic message format:
                [{"role": "user"|"assistant", "content": ...}, ...]
            tools: Tool definitions in Anthropic tool format:
                [{"name": ..., "description": ..., "input_schema": ...}, ...]

        Returns:
            ProviderResponse with text, tool_calls, and stop_reason.
        """
        ...
