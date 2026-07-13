"""Interactive ``human`` condition (CLI play; kept beside ``human_script``, ADR 0003)."""
from __future__ import annotations

from typing import Any

from simcontract.contracts import Action, ControllerResult, StepContext


class HumanController:
    """``input_fn(slot, schema_fields, view, candidates) -> fields | None``."""

    condition = "human"

    def __init__(self, input_fn, schema_fields: dict[str, dict[str, Any]], role: str):
        self._input = input_fn
        self._fields = schema_fields
        self._role = role

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        fields = self._input(slot, self._fields, view, candidates)
        if fields is None:
            return ControllerResult(action=None, fallback_reason="human_absent")
        return ControllerResult(action=Action(role=self._role, slot=slot, fields=fields))
