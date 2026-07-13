"""Domain default policies (DefaultActionProvider) — persona-parameterised."""
from __future__ import annotations

from simcontract.contracts import Action, StepContext

from .model import GENERATOR_PARAMS

REGULATOR_DEFAULTS = {
    "decarb_first":    {"carbon_price": 60.0, "price_cap": 300.0, "renewable_subsidy": 20.0},
    "price_stability": {"carbon_price": 20.0, "price_cap": 160.0, "renewable_subsidy": 5.0},
    None:              {"carbon_price": 30.0, "price_cap": 250.0, "renewable_subsidy": 10.0},
}

GENERATOR_MARGIN = {"profit_max": 18.0, "green_transition": 8.0, None: 12.0}

RETAILER_DEFAULTS = {
    "cost_min":          {"demand_bid": 200.0, "max_price": 140.0},
    "reliability_first": {"demand_bid": 220.0, "max_price": 260.0},
    None:                {"demand_bid": 200.0, "max_price": 200.0},
}


class EnergyDefaults:
    """Rule policies for every role slot; used for SC-I2 completion and the
    ``rule`` controller condition."""

    def action_for(self, state, role_slot: str, persona: str | None,
                   ctx: StepContext) -> Action:
        role = role_slot.rsplit("_", 1)[0]
        if role == "regulator":
            fields = dict(REGULATOR_DEFAULTS.get(persona, REGULATOR_DEFAULTS[None]))
        elif role == "generator":
            p = GENERATOR_PARAMS[role_slot]
            margin = GENERATOR_MARGIN.get(persona, GENERATOR_MARGIN[None])
            fields = {
                "price_bid": round(p["cost"] + margin, 4),
                "capacity_offered": p["cap"],
                "maintenance": False,
            }
        elif role == "retailer":
            fields = dict(RETAILER_DEFAULTS.get(persona, RETAILER_DEFAULTS[None]))
        else:  # pragma: no cover
            raise KeyError(f"unknown role slot {role_slot!r}")
        return Action(role=role, slot=role_slot, fields=fields)
