"""Persona weight profiles for preview scoring (spec 7.1).

Per-role archetypes live in ``roles/<role>/archetypes.py``. This module
assembles them and keeps the domain-level ``weights_for`` contract stable.
"""
from __future__ import annotations

from .roles.generator import archetypes as _generator
from .roles.regulator import archetypes as _regulator
from .roles.retailer import archetypes as _retailer

PERSONA_WEIGHTS: dict[str, dict[str, dict[str, float]]] = {
    "regulator": _regulator.WEIGHTS,
    "generator": _generator.WEIGHTS,
    "retailer": _retailer.WEIGHTS,
}

DEFAULT_PERSONA = {
    "regulator": _regulator.DEFAULT,
    "generator": _generator.DEFAULT,
    "retailer": _retailer.DEFAULT,
}


def weights_for(role: str, persona: str | None) -> dict[str, float]:
    table = PERSONA_WEIGHTS[role]
    return table[persona or DEFAULT_PERSONA[role]]
