"""Domain default policy (SC-I2, tag ``domain_default``; delegated to by
``rule``, tag ``rule``).

Level-1's baseline policy is a fixed static phase (phase 0), not "leave
whatever program the network file loads with running unmanaged" -- see
protocol Sec. 4a/6: this makes the default/applied comparison symmetric
(both are "force phase X for the round"), which is what the authoritative
vs. applied branch computation in ``adapter.step`` needs.
"""
from __future__ import annotations

from simcontract.contracts import Action, StepContext

DEFAULT_PHASE = 0


class SumoDefaults:
    def action_for(self, state, role_slot: str, persona: str | None,
                   ctx: StepContext) -> Action:
        return Action(role="traffic_authority", slot=role_slot,
                      fields={"phase": DEFAULT_PHASE})
