"""Persona weight profiles for preview scoring (spec 7.2)."""

PERSONA_WEIGHTS: dict[str, dict[str, dict[str, float]]] = {
    "health_authority": {
        "health_first":     {"new_infections": -1.0, "cumulative_deaths": -2.0,
                             "overflow_days": -0.5},
        "economy_balanced": {"econ_cost": -1.0, "cumulative_deaths": -0.8},
    },
    "region_manager": {
        "equity_first":     {"equity_gap": -1.0, "vaccination_coverage": 0.5},
        "efficiency_first": {"new_infections": -1.0, "overflow_days": -0.5},
    },
}

DEFAULT_PERSONA = {
    "health_authority": "health_first",
    "region_manager": "efficiency_first",
}


def weights_for(role: str, persona: str | None) -> dict[str, float]:
    return PERSONA_WEIGHTS[role][persona or DEFAULT_PERSONA[role]]
