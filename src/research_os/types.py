"""Shared types used across the project."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Structured result returned by all tool functions and source clients."""

    ok: bool
    data: Any = None
    error: str | None = None
    retryable: bool = False

    def to_agent_string(self) -> str:
        """Serialize for inclusion in a Claude tool_result message."""
        if self.ok:
            return json.dumps(self.data, default=str)
        return json.dumps({"error": self.error, "retryable": self.retryable})
