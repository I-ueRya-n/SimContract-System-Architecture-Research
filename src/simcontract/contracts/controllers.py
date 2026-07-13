"""Controller contract (spec 4/6.3): the engine sees only this protocol.

Concrete conditions live in ``simcontract.controllers``; the engine invokes
them exclusively through ``RoleController`` and treats a ``None`` action as
"slot unfilled" (fallback event SC-I3, then domain completion SC-I2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .core import Action, Preview, StepContext


@dataclass
class ControllerResult:
    action: Action | None
    rationale: str | None = None
    scores: list[float] = field(default_factory=list)
    fallback_reason: str | None = None
    llm_record: dict[str, Any] | None = None


@runtime_checkable
class RoleController(Protocol):
    condition: str

    def act(self, view: Any, slot: str, candidates: list[Action],
            previews: list[Preview], ctx: StepContext) -> ControllerResult: ...
