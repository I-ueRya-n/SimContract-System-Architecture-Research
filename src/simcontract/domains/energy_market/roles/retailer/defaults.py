"""Deterministic default policy for the retailer role."""
from __future__ import annotations

RETAILER_DEFAULTS = {
    "cost_min":          {"demand_bid": 200.0, "max_price": 140.0},
    "reliability_first": {"demand_bid": 220.0, "max_price": 260.0},
    None:                {"demand_bid": 200.0, "max_price": 200.0},
}


def action_fields(state, role_slot: str, persona: str | None, ctx) -> dict:
    return dict(RETAILER_DEFAULTS.get(persona, RETAILER_DEFAULTS[None]))
