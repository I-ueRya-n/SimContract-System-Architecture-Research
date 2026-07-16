"""Persona archetypes (preview-scoring weights) for the retailer role."""
from __future__ import annotations

WEIGHTS: dict[str, dict[str, float]] = {
    "cost_min":          {"consumer_cost": -1.0},
    "reliability_first": {"unserved_energy": -1.0, "consumer_cost": -0.2},
}

DEFAULT = "cost_min"
