"""``random_valid`` condition: seeded uniform choice over validated candidates.

The floor condition: what validity alone is worth, with no intelligence.
"""
from __future__ import annotations

from simcontract.contracts import ControllerResult, StepContext
from simcontract.contracts.seeding import rng_for


class RandomValidController:
    condition = "random_valid"

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        if not candidates:
            return ControllerResult(action=None, fallback_reason="no_candidates")
        rng = rng_for(ctx.round_seed, slot, "random_valid")
        return ControllerResult(action=rng.choice(candidates))
