"""Persona archetypes (preview-scoring weights) for the region-manager role."""
from __future__ import annotations

WEIGHTS: dict[str, dict[str, float]] = {
    "equity_first":     {"equity_gap": -1.0, "vaccination_coverage": 0.5},
    "efficiency_first": {"new_infections": -1.0, "overflow_days": -0.5},
}

DEFAULT = "efficiency_first"
