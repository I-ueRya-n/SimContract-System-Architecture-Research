"""Persona weight profiles for preview scoring (spec 7.2).

Per-role archetypes live in ``roles/<role>/archetypes.py``. This module
assembles them and keeps the domain-level ``weights_for`` contract stable.
"""
from __future__ import annotations

from .roles.health_authority import archetypes as _authority
from .roles.region_manager import archetypes as _manager

PERSONA_WEIGHTS: dict[str, dict[str, dict[str, float]]] = {
    "health_authority": _authority.WEIGHTS,
    "region_manager": _manager.WEIGHTS,
}

DEFAULT_PERSONA = {
    "health_authority": _authority.DEFAULT,
    "region_manager": _manager.DEFAULT,
}


def weights_for(role: str, persona: str | None) -> dict[str, float]:
    return PERSONA_WEIGHTS[role][persona or DEFAULT_PERSONA[role]]
