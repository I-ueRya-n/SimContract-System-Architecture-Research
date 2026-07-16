"""Persona archetypes (preview-scoring weights) for the health-authority role."""
from __future__ import annotations

WEIGHTS: dict[str, dict[str, float]] = {
    "health_first":     {"new_infections": -1.0, "cumulative_deaths": -2.0,
                         "overflow_days": -0.5},
    "economy_balanced": {"econ_cost": -1.0, "cumulative_deaths": -0.8},
}

DEFAULT = "health_first"
