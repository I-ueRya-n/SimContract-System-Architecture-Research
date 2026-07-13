"""``human_script`` condition: scripted human decisions, reproducible.

A script maps round number to action fields for the controlled slot. Missing
rounds degrade observably (``script_exhausted``) and the domain default
completes the slot (SC-I2/I3) — scripted humans go absent like real ones.
"""
from __future__ import annotations

from typing import Any

from simcontract.contracts import Action, ControllerResult, StepContext


class ScriptedHumanController:
    condition = "human_script"

    def __init__(self, script: dict[int, dict[str, Any]], role: str):
        self._script = dict(script)
        self._role = role

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        fields = self._script.get(ctx.round_no)
        if fields is None:
            return ControllerResult(action=None, fallback_reason="script_exhausted")
        return ControllerResult(action=Action(role=self._role, slot=slot, fields=dict(fields)))
