"""``top_score`` condition: deterministic argmax of the persona-weighted ranking.

The scripted-competence ceiling: isolates what an LLM adds beyond the
ranking it is shown.
"""
from __future__ import annotations

from simcontract.contracts import ControllerResult, StepContext

from ._scoring import persona_score


class TopScoreController:
    condition = "top_score"

    def __init__(self, weights: dict[str, float]):
        self._weights = weights

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        if not candidates:
            return ControllerResult(action=None, fallback_reason="no_candidates")
        scores = [persona_score(p, self._weights) for p in previews]
        best = max(range(len(candidates)), key=lambda i: scores[i])
        return ControllerResult(action=candidates[best], scores=scores)
