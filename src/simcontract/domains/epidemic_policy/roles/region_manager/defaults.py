"""Deterministic default policy for the region-manager role."""
from __future__ import annotations

MANAGER_DEFAULTS = {
    "equity_first":     {"share_testing": 0.2, "share_vaccination": 0.5, "share_capacity": 0.3},
    "efficiency_first": {"share_testing": 0.3, "share_vaccination": 0.4, "share_capacity": 0.3},
    None:               {"share_testing": 0.25, "share_vaccination": 0.45, "share_capacity": 0.3},
}


def action_fields(state, role_slot: str, persona: str | None, ctx) -> dict:
    return dict(MANAGER_DEFAULTS.get(persona, MANAGER_DEFAULTS[None]))
