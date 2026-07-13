"""Persona-weighted preview scoring shared by ranked and LLM conditions."""
from __future__ import annotations

from simcontract.contracts import Preview


def persona_score(preview: Preview, weights: dict[str, float]) -> float:
    return sum(w * float(preview.projected_metrics.get(k, 0.0)) for k, w in weights.items())
