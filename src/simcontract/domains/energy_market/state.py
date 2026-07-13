"""State construction and scenario loading for the energy-market domain."""
from __future__ import annotations

from pathlib import Path

import yaml

from .model import GENERATOR_PARAMS

_SCENARIOS = Path(__file__).parent / "scenarios"


def load_scenario(scenario_id: str) -> dict:
    path = _SCENARIOS / f"{scenario_id}.yaml"
    if not path.exists():
        known = sorted(p.stem for p in _SCENARIOS.glob("*.yaml"))
        raise KeyError(f"unknown scenario {scenario_id!r}; known: {known}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def initial_state(scenario_id: str) -> dict:
    scenario = load_scenario(scenario_id)
    return {
        "round": 0,
        "scenario_id": scenario_id,
        "policy": dict(scenario["initial_policy"]),
        "market": {"last_clearing_price": 0.0, "last_demand": 0.0, "eps": 0.0},
        "generators": {s: dict(p) for s, p in GENERATOR_PARAMS.items()},
        "exogenous_params": dict(scenario["exogenous"]),
    }
