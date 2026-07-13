"""Candidate and preview requests (spec 6.2): the engine asks, domains answer."""
from __future__ import annotations

from typing import Any

from simcontract.contracts import Action, Preview, SimulationAdapter, StepContext


def candidates_and_previews(adapter: SimulationAdapter, state: Any, slot: str,
                            rng: Any, n: int,
                            ctx: StepContext) -> tuple[list[Action], list[Preview]]:
    """Schema-derived, domain-filtered candidates plus non-mutating previews."""
    candidates = adapter.action_space(state, slot, rng, n)
    previews = [adapter.preview(state, a, ctx) for a in candidates]
    return candidates, previews
