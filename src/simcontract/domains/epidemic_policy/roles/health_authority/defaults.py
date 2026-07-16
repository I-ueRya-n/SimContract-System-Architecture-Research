"""Deterministic default policy for the health-authority role."""
from __future__ import annotations

AUTHORITY_DEFAULTS = {
    "health_first":     {"restriction": 2, "mask_level": 2, "vaccine_budget": 800.0},
    "economy_balanced": {"restriction": 1, "mask_level": 1, "vaccine_budget": 400.0},
    None:               {"restriction": 1, "mask_level": 1, "vaccine_budget": 600.0},
}


def action_fields(state, role_slot: str, persona: str | None, ctx) -> dict:
    return dict(AUTHORITY_DEFAULTS.get(persona, AUTHORITY_DEFAULTS[None]))
