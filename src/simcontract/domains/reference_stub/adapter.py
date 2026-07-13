"""Minimal deterministic domain for contract/engine/evidence/replay testing.

Spec 7.0: one role, integer state, transition ``value += delta + drift``.
Expected outputs are small enough to assert literally in tests. This domain is
never presented as a research model.
"""
from __future__ import annotations

import random

from simcontract.contracts import (
    CONTRACT_VERSION,
    Action,
    ActionSchema,
    MetricCatalog,
    ObservationPolicy,
    Outcome,
    Preview,
    RejectionInfo,
    ResolutionReport,
    RoleSpec,
    StepContext,
)
from simcontract.contracts.domain_manifest import DomainManifest

DOMAIN_ID = "reference_stub"
ADAPTER_VERSION = "0.1.0"
ROLES = [RoleSpec("agent", 1, stage=1)]
BOUND = 100

_SCHEMA = {"agent": {"delta": {"type": "int", "min": -5, "max": 5}}}
_CATALOG = [{"key": "value_abs", "unit": "unit", "direction": "min"},
            {"key": "value", "unit": "unit", "direction": "min"}]
_OBSERVATION = {"agent": ["value", "round"]}

_MANIFEST = DomainManifest(
    domain_id=DOMAIN_ID,
    domain_version=ADAPTER_VERSION,
    contract_version=CONTRACT_VERSION,
    origin="self_implemented",
    roles=tuple(ROLES),
    stage_order=(1,),
    action_schema_ids={"agent": "stub_delta_v1"},
    metric_catalog_id="stub_metrics_v1",
    observation_policy_id="stub_observation_v1",
    scenario_ids=("default",),
)


def schema() -> ActionSchema:
    return ActionSchema(_SCHEMA)


def catalog() -> MetricCatalog:
    return MetricCatalog(list(_CATALOG))


def observation() -> ObservationPolicy:
    return ObservationPolicy(dict(_OBSERVATION))


class _StubDefaults:
    def action_for(self, state, role_slot: str, persona, ctx: StepContext) -> Action:
        return Action(role="agent", slot=role_slot, fields={"delta": 0})


class ReferenceStubAdapter:
    domain_id = DOMAIN_ID
    contract_version = CONTRACT_VERSION
    adapter_version = ADAPTER_VERSION
    roles = ROLES

    def __init__(self) -> None:
        self._defaults = _StubDefaults()
        self._schema = schema()

    @property
    def manifest(self) -> DomainManifest:
        return _MANIFEST

    def initial_state(self, scenario_id: str, seed: int) -> dict:
        if scenario_id != "default":
            raise KeyError(f"unknown scenario {scenario_id!r}")
        return {"round": 0, "value": 0, "scenario_id": scenario_id}

    def sample_exogenous(self, state: dict, rng: random.Random) -> dict:
        return {"drift": rng.randint(-1, 1)}

    def action_space(self, state, role_slot, rng: random.Random, n: int):
        return self._schema.sample_candidates("agent", role_slot, rng, n)

    def preview(self, state, action: Action, ctx: StepContext) -> Preview:
        value = state["value"] + int(action.fields["delta"]) + int(ctx.exogenous["drift"])
        return Preview(projected_metrics={"value": float(value), "value_abs": float(abs(value))})

    def validate_semantic(self, state, action: Action) -> RejectionInfo | None:
        nxt = state["value"] + int(action.fields["delta"])
        if abs(nxt) > BOUND:
            return RejectionInfo("adapter_semantic", "bound_exceeded",
                                 f"value would reach {nxt}, bound is +/-{BOUND}")
        return None

    def step(self, state, actions: dict[str, Action], ctx: StepContext) -> Outcome:
        intake = ctx.config.get("intake", {"submitted": {}, "rejected": {}, "sources": {}})
        slot = "agent_1"
        default = self._defaults.action_for(state, slot, None, ctx)

        completed, reasons, sources = {}, {}, {}
        if slot in actions:
            applied_action = actions[slot]
            sources[slot] = intake["sources"].get(slot, "human")
        else:
            applied_action = default
            completed[slot] = default.digest()
            sources[slot] = "domain_default"
            reasons[slot] = ("rejected_upstream" if slot in intake["rejected"]
                             else "no_accepted_action")

        drift = int(ctx.exogenous["drift"])
        applied_value = state["value"] + int(applied_action.fields["delta"]) + drift
        auth_value = state["value"] + int(default.fields["delta"]) + drift  # same drift (SC-I1)

        applied = {"value": float(applied_value), "value_abs": float(abs(applied_value))}
        authoritative = {"value": float(auth_value), "value_abs": float(abs(auth_value))}

        report = ResolutionReport(
            submitted=dict(intake["submitted"]),
            accepted={s: a.digest() for s, a in actions.items()},
            completed=completed,
            rejected=dict(intake["rejected"]),
            sources=sources,
            completion_reasons=reasons,
        )
        return Outcome(
            role_outcomes={slot: {"action": applied_action.fields}},
            system_metrics=applied,
            state_next={"round": state["round"] + 1, "value": applied_value,
                        "scenario_id": state["scenario_id"]},
            branches={"authoritative": authoritative, "applied": applied},
            resolution=report,
            meta={"adapter_version": ADAPTER_VERSION, "approximations": [],
                  "provenance": {"scenario_id": state["scenario_id"]},
                  "resolved_actions": {slot: applied_action}},
        )

    @property
    def default_action_provider(self):
        return self._defaults
