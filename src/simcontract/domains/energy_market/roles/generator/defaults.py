"""Deterministic default policy for the generator role."""
from __future__ import annotations

from ...model import GENERATOR_PARAMS

GENERATOR_MARGIN = {"profit_max": 18.0, "green_transition": 8.0, None: 12.0}


def action_fields(state, role_slot: str, persona: str | None, ctx) -> dict:
    p = GENERATOR_PARAMS[role_slot]
    margin = GENERATOR_MARGIN.get(persona, GENERATOR_MARGIN[None])
    return {
        "price_bid": round(p["cost"] + margin, 4),
        "capacity_offered": p["cap"],
        "maintenance": False,
    }
