"""Persona weight profiles for preview scoring (spec 7.1)."""

PERSONA_WEIGHTS: dict[str, dict[str, dict[str, float]]] = {
    "regulator": {
        "decarb_first":    {"total_emissions": -1.0, "clearing_price": -0.2},
        "price_stability": {"clearing_price": -1.0, "unserved_energy": -0.8},
    },
    "generator": {
        "profit_max":       {"generator_profit_total": 1.0},
        "green_transition": {"generator_profit_total": 0.6, "total_emissions": -0.4},
    },
    "retailer": {
        "cost_min":          {"consumer_cost": -1.0},
        "reliability_first": {"unserved_energy": -1.0, "consumer_cost": -0.2},
    },
}

DEFAULT_PERSONA = {
    "regulator": "price_stability",
    "generator": "profit_max",
    "retailer": "cost_min",
}


def weights_for(role: str, persona: str | None) -> dict[str, float]:
    table = PERSONA_WEIGHTS[role]
    return table[persona or DEFAULT_PERSONA[role]]
