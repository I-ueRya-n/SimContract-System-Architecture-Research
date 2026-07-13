"""Domain default policies for the epidemic domain."""
from __future__ import annotations

from simcontract.contracts import Action, StepContext

AUTHORITY_DEFAULTS = {
    "health_first":     {"restriction": 2, "mask_level": 2, "vaccine_budget": 800.0},
    "economy_balanced": {"restriction": 1, "mask_level": 1, "vaccine_budget": 400.0},
    None:               {"restriction": 1, "mask_level": 1, "vaccine_budget": 600.0},
}

MANAGER_DEFAULTS = {
    "equity_first":     {"share_testing": 0.2, "share_vaccination": 0.5, "share_capacity": 0.3},
    "efficiency_first": {"share_testing": 0.3, "share_vaccination": 0.4, "share_capacity": 0.3},
    None:               {"share_testing": 0.25, "share_vaccination": 0.45, "share_capacity": 0.3},
}


class EpidemicDefaults:
    def action_for(self, state, role_slot: str, persona: str | None,
                   ctx: StepContext) -> Action:
        role = role_slot.rsplit("_", 1)[0]
        if role == "health":
            role = "health_authority"           # slot prefix healed below
        if role_slot.startswith("health_authority"):
            fields = dict(AUTHORITY_DEFAULTS.get(persona, AUTHORITY_DEFAULTS[None]))
            return Action(role="health_authority", slot=role_slot, fields=fields)
        if role_slot.startswith("region_manager"):
            fields = dict(MANAGER_DEFAULTS.get(persona, MANAGER_DEFAULTS[None]))
            return Action(role="region_manager", slot=role_slot, fields=fields)
        raise KeyError(f"unknown role slot {role_slot!r}")
