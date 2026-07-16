"""Domain default policies (DefaultActionProvider) — persona-parameterised.

Role policies live in ``roles/<role>/defaults.py``. This module dispatches to
them and keeps the adapter-facing ``EnergyDefaults`` contract stable.
"""
from __future__ import annotations

from simcontract.contracts import Action, StepContext

from .roles.generator import defaults as _generator
from .roles.regulator import defaults as _regulator
from .roles.retailer import defaults as _retailer

# Re-exported for backward compatibility with callers that read the tables.
REGULATOR_DEFAULTS = _regulator.REGULATOR_DEFAULTS
GENERATOR_MARGIN = _generator.GENERATOR_MARGIN
RETAILER_DEFAULTS = _retailer.RETAILER_DEFAULTS

_ROLE_POLICIES = {
    "regulator": _regulator,
    "generator": _generator,
    "retailer": _retailer,
}


class EnergyDefaults:
    """Rule policies for every role slot; used for SC-I2 completion and the
    ``rule`` controller condition."""

    def action_for(self, state, role_slot: str, persona: str | None,
                   ctx: StepContext) -> Action:
        role = role_slot.rsplit("_", 1)[0]
        policy = _ROLE_POLICIES.get(role)
        if policy is None:  # pragma: no cover
            raise KeyError(f"unknown role slot {role_slot!r}")
        fields = policy.action_fields(state, role_slot, persona, ctx)
        return Action(role=role, slot=role_slot, fields=fields)
