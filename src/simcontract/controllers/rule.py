"""``rule`` condition: delegate to the domain's default policy (tag ``rule``)."""
from __future__ import annotations

from simcontract.contracts import ControllerResult, StepContext


class RuleController:
    condition = "rule"

    def __init__(self, provider, persona: str | None):
        self._provider = provider
        self._persona = persona

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        action = self._provider.action_for(view, slot, self._persona, ctx)
        return ControllerResult(action=action)
