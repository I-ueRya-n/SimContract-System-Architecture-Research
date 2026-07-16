"""Domain default policies for the epidemic domain.

Role policies live in ``roles/<role>/defaults.py``. This module dispatches to
them and keeps the adapter-facing ``EpidemicDefaults`` contract stable.
"""
from __future__ import annotations

from simcontract.contracts import Action, StepContext

from .roles.health_authority import defaults as _authority
from .roles.region_manager import defaults as _manager

# Re-exported for backward compatibility with callers that read the tables.
AUTHORITY_DEFAULTS = _authority.AUTHORITY_DEFAULTS
MANAGER_DEFAULTS = _manager.MANAGER_DEFAULTS

# Slot prefixes are matched in order; each role owns its own policy module.
_ROLE_POLICIES = (
    ("health_authority", _authority),
    ("region_manager", _manager),
)


class EpidemicDefaults:
    def action_for(self, state, role_slot: str, persona: str | None,
                   ctx: StepContext) -> Action:
        for role, policy in _ROLE_POLICIES:
            if role_slot.startswith(role):
                fields = policy.action_fields(state, role_slot, persona, ctx)
                return Action(role=role, slot=role_slot, fields=fields)
        raise KeyError(f"unknown role slot {role_slot!r}")
