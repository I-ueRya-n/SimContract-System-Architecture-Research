"""Adapter protocols (spec sections 5.2/5.3)."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .core import Action, Outcome, Preview, RejectionInfo, RoleSpec, StepContext
from .domain_manifest import DomainManifest


@runtime_checkable
class DefaultActionProvider(Protocol):
    """The domain's rule policy, persona-parameterised.

    Used by the adapter for missing-action completion (SC-I2, tag
    ``domain_default``) and delegated to by the ``rule`` controller condition
    (tag ``rule``).
    """

    def action_for(
        self, state: Any, role_slot: str, persona: str | None, ctx: StepContext
    ) -> Action: ...


@runtime_checkable
class SimulationAdapter(Protocol):
    domain_id: str
    contract_version: str
    roles: list[RoleSpec]

    @property
    def manifest(self) -> DomainManifest: ...

    def initial_state(self, scenario_id: str, seed: int) -> Any: ...

    def sample_exogenous(self, state: Any, rng: Any) -> dict[str, Any]: ...

    def action_space(self, state: Any, role_slot: str, rng: Any, n: int) -> list[Action]: ...

    def preview(self, state: Any, action: Action, ctx: StepContext) -> Preview: ...

    def validate_semantic(self, state: Any, action: Action) -> RejectionInfo | None: ...

    def step(self, state: Any, actions: dict[str, Action], ctx: StepContext) -> Outcome: ...

    @property
    def default_action_provider(self) -> DefaultActionProvider: ...
