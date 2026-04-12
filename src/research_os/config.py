"""Configuration — all from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    db_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("RESEARCH_OS_DB", "~/.research-os/research.db")
        ).expanduser()
    )
    cache_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("RESEARCH_OS_CACHE", "~/.research-os/cache")
        ).expanduser()
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    model: str = field(
        default_factory=lambda: os.environ.get(
            "RESEARCH_OS_MODEL", "claude-sonnet-4-20250514"
        )
    )
    # Provider: "anthropic_api" (default) or "claude_cli"
    provider: str = field(
        default_factory=lambda: os.environ.get("RESEARCH_OS_PROVIDER", "anthropic_api")
    )
    # Command for CLI providers (e.g., "claude" for claude -p)
    provider_command: str = field(
        default_factory=lambda: os.environ.get("RESEARCH_OS_PROVIDER_CMD", "claude")
    )
    s2_api_key: str | None = field(
        default_factory=lambda: os.environ.get("S2_API_KEY")
    )
    max_agent_turns: int = field(
        default_factory=lambda: int(
            os.environ.get("RESEARCH_OS_MAX_TURNS", "200")
        )
    )

    def make_provider(self):
        """Create the configured LLM provider instance."""
        from research_os.providers.base import Provider

        if self.provider == "anthropic_api":
            from research_os.providers.anthropic_api import AnthropicAPIProvider
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY required for anthropic_api provider")
            return AnthropicAPIProvider(
                api_key=self.anthropic_api_key,
                model=self.model,
            )
        elif self.provider == "claude_cli":
            from research_os.providers.claude_cli import ClaudeCLIProvider
            return ClaudeCLIProvider(
                model=self.model if self.model != "claude-sonnet-4-20250514" else None,
                command=self.provider_command,
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}. Use 'anthropic_api' or 'claude_cli'.")
