"""Deterministic default policy for the regulator role."""
from __future__ import annotations

REGULATOR_DEFAULTS = {
    "decarb_first":    {"carbon_price": 60.0, "price_cap": 300.0, "renewable_subsidy": 20.0},
    "price_stability": {"carbon_price": 20.0, "price_cap": 160.0, "renewable_subsidy": 5.0},
    None:              {"carbon_price": 30.0, "price_cap": 250.0, "renewable_subsidy": 10.0},
}


def action_fields(state, role_slot: str, persona: str | None, ctx) -> dict:
    return dict(REGULATOR_DEFAULTS.get(persona, REGULATOR_DEFAULTS[None]))
