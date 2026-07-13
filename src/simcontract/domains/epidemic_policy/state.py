"""State construction and scenario loading for the epidemic-policy domain."""
from __future__ import annotations

from pathlib import Path

import yaml

from .model import initial_regions

_SCENARIOS = Path(__file__).parent / "scenarios"


def load_scenario(scenario_id: str) -> dict:
    path = _SCENARIOS / f"{scenario_id}.yaml"
    if not path.exists():
        known = sorted(p.stem for p in _SCENARIOS.glob("*.yaml"))
        raise KeyError(f"unknown scenario {scenario_id!r}; known: {known}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def initial_state(scenario_id: str, summarise) -> dict:
    scenario = load_scenario(scenario_id)
    regions = initial_regions(
        infection_rates=scenario["initial_infection_rates"],
        prior_immunity=float(scenario.get("prior_immunity", 0.0)),
    )
    return {
        "round": 0,
        "scenario_id": scenario_id,
        "policy": dict(scenario["initial_policy"]),
        "regions": regions,
        "summary": summarise(regions),
        "exogenous_params": dict(scenario["exogenous"]),
    }
