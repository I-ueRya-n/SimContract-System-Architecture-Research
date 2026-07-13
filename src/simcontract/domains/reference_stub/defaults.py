"""Stub default policy: hold (delta 0)."""
from __future__ import annotations

from simcontract.contracts import Action, StepContext


class StubDefaults:
    def action_for(self, state, role_slot: str, persona, ctx: StepContext) -> Action:
        return Action(role="agent", slot=role_slot, fields={"delta": 0})
