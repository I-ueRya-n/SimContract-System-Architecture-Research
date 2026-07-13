"""LLM port: what controllers may assume about a language-model client.

Provider adapters (``openai_compatible``) implement this; controllers depend
on the port, never on a provider.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmPort(Protocol):
    def complete(self, prompt: str, *, temperature: float, round_no: int,
                 slot: str, prompt_version: str) -> tuple[str, dict[str, Any]]:
        """Return (response_text, invocation_record_fields); raise on failure."""
        ...
