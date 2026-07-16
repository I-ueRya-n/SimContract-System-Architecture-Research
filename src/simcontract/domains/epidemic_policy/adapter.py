"""Epidemic-policy adapter: SimulationAdapter for the regional SEIR domain."""
from __future__ import annotations

import random
from pathlib import Path

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
    StepContext,
)
from simcontract.contracts.domain_manifest import DomainManifest

from .actions import RegionalAllocation
from .defaults import EpidemicDefaults
from .manifest import ADAPTER_VERSION, DOMAIN_ID, MANIFEST, ROLES
from .model import REGION_PARAMS, step_week
from .state import initial_state as build_initial_state

_HERE = Path(__file__).parent


def schema() -> ActionSchema:
    return ActionSchema.from_file(_HERE / "contract" / "action_schema.yaml")


def catalog() -> MetricCatalog:
    return MetricCatalog.from_file(_HERE / "contract" / "metric_catalog.yaml")


def observation() -> ObservationPolicy:
    return ObservationPolicy.from_file(_HERE / "contract" / "observation_policy.yaml")


class EpidemicPolicyAdapter:
    domain_id = DOMAIN_ID
    contract_version = CONTRACT_VERSION
    adapter_version = ADAPTER_VERSION
    roles = ROLES

    def __init__(self) -> None:
        self._defaults = EpidemicDefaults()
        self._schema = schema()

    @property
    def manifest(self) -> DomainManifest:
        return MANIFEST

    # ------------------------------------------------------------------
    def initial_state(self, scenario_id: str, seed: int) -> dict:
        return build_initial_state(scenario_id, self._summary)

    def sample_exogenous(self, state: dict, rng: random.Random) -> dict:
        sigma = float(state["exogenous_params"]["shock_sigma"])
        return {f"shock_{slot}": round(rng.lognormvariate(0.0, sigma), 6)
                for slot in REGION_PARAMS}

    # ------------------------------------------------------------------
    def action_space(self, state, role_slot, rng: random.Random, n: int):
        role = ("health_authority" if role_slot.startswith("health_authority")
                else "region_manager")
        default = self._defaults.action_for(state, role_slot, None,
                                            StepContext(0, 0, {}, state["scenario_id"]))
        candidates = [default]
        for cand in self._schema.sample_candidates(role, role_slot, rng, max(0, n - 1)):
            fields = dict(cand.fields)
            if role == "region_manager":
                total = sum(float(fields[k]) for k in
                            ("share_testing", "share_vaccination", "share_capacity"))
                if total <= 0:
                    fields = dict(default.fields)
                else:  # normalise so candidates satisfy the semantic sum rule
                    for k in ("share_testing", "share_vaccination", "share_capacity"):
                        fields[k] = round(float(fields[k]) / total, 4)
                    drift = 1.0 - sum(fields[k] for k in
                                      ("share_testing", "share_vaccination", "share_capacity"))
                    fields["share_capacity"] = round(fields["share_capacity"] + drift, 4)
            candidates.append(Action(role=role, slot=role_slot, fields=fields))
        return candidates

    def preview(self, state, action: Action, ctx: StepContext) -> Preview:
        actions = self._default_actions(state, ctx)
        actions[action.slot] = action
        _, metrics = self._simulate(state, actions, ctx.exogenous)
        return Preview(projected_metrics=metrics)

    def validate_semantic(self, state, action: Action) -> RejectionInfo | None:
        if action.role == "region_manager":
            allocation = RegionalAllocation.from_fields(action.fields)
            if abs(allocation.total - 1.0) > 0.01:
                return RejectionInfo("adapter_semantic", "shares_not_normalised",
                                     f"allocation shares sum to {allocation.total:.4f}, "
                                     "expected 1.0")
        return None

    # ------------------------------------------------------------------
    def step(self, state, actions: dict[str, Action], ctx: StepContext) -> Outcome:
        intake = ctx.config.get("intake", {"submitted": {}, "rejected": {}, "sources": {}})

        defaults = self._default_actions(state, ctx)
        applied = dict(defaults)
        completed, reasons, sources = {}, {}, {}
        for slot in applied:
            if slot in actions:
                applied[slot] = actions[slot]
                sources[slot] = intake["sources"].get(slot, "human")
            else:
                completed[slot] = defaults[slot].digest()
                sources[slot] = "domain_default"
                reasons[slot] = ("rejected_upstream" if slot in intake["rejected"]
                                 else "no_accepted_action")

        regions_applied, applied_metrics = self._simulate(state, applied, ctx.exogenous)
        _, authoritative_metrics = self._simulate(state, defaults, ctx.exogenous)  # SC-I1

        report = ResolutionReport(
            submitted=dict(intake["submitted"]),
            accepted={s: a.digest() for s, a in actions.items()},
            completed=completed,
            rejected=dict(intake["rejected"]),
            sources=sources,
            completion_reasons=reasons,
        )
        state_next = {
            "round": state["round"] + 1,
            "scenario_id": state["scenario_id"],
            "policy": dict(applied["health_authority_1"].fields),
            "regions": regions_applied,
            "summary": self._summary(regions_applied),
            "exogenous_params": state["exogenous_params"],
        }
        return Outcome(
            role_outcomes={s: {"action": a.fields} for s, a in applied.items()},
            system_metrics=applied_metrics,
            state_next=state_next,
            branches={"authoritative": authoritative_metrics, "applied": applied_metrics},
            resolution=report,
            meta={"adapter_version": ADAPTER_VERSION,
                  "approximations": ["deterministic_seir_weekly_aggregation"],
                  "provenance": {"scenario_id": state["scenario_id"]},
                  "resolved_actions": applied},
        )

    # ------------------------------------------------------------------
    @property
    def default_action_provider(self) -> EpidemicDefaults:
        return self._defaults

    def _default_actions(self, state, ctx) -> dict[str, Action]:
        out = {}
        for role in self.roles:
            for slot in role.slots():
                out[slot] = self._defaults.action_for(state, slot, None, ctx)
        return out

    def _simulate(self, state, actions: dict[str, Action], exogenous: dict):
        return step_week(
            regions=state["regions"],
            policy=actions["health_authority_1"].fields,
            allocations={s: a.fields for s, a in actions.items()
                         if s.startswith("region_manager_")},
            exogenous=exogenous,
        )

    @staticmethod
    def _summary(regions: dict) -> dict:
        return {
            "total_infected": round(sum(r["I"] for r in regions.values()), 1),
            "total_deaths": round(sum(r["D"] for r in regions.values()), 1),
            "total_vaccinated": round(sum(r["vaccinated"] for r in regions.values()), 1),
        }
