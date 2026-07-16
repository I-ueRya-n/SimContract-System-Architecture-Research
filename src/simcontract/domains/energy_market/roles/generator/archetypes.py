"""Persona archetypes (preview-scoring weights) for the generator role."""
from __future__ import annotations

WEIGHTS: dict[str, dict[str, float]] = {
    "profit_max":       {"generator_profit_total": 1.0},
    "green_transition": {"generator_profit_total": 0.6, "total_emissions": -0.4},
}

DEFAULT = "profit_max"
