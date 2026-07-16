"""Persona archetypes (preview-scoring weights) for the regulator role."""
from __future__ import annotations

WEIGHTS: dict[str, dict[str, float]] = {
    "decarb_first":    {"total_emissions": -1.0, "clearing_price": -0.2},
    "price_stability": {"clearing_price": -1.0, "unserved_energy": -0.8},
}

DEFAULT = "price_stability"
