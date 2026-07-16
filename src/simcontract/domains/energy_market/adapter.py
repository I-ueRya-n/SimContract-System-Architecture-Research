"""Energy-market adapter: SimulationAdapter for the merit-order auction domain."""
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

from .actions import GeneratorBid
from .defaults import EnergyDefaults
from .manifest import ADAPTER_VERSION, DOMAIN_ID, MANIFEST, ROLES
from .model import clear_market
from .state import initial_state as build_initial_state

_HERE = Path(__file__).parent


def schema() -> ActionSchema:
    return ActionSchema.from_file(_HERE / "contract" / "action_schema.yaml")


def catalog() -> MetricCatalog:
    return MetricCatalog.from_file(_HERE / "contract" / "metric_catalog.yaml")


def observation() -> ObservationPolicy:
    return ObservationPolicy.from_file(_HERE / "contract" / "observation_policy.yaml")


class EnergyMarketAdapter:
    domain_id = DOMAIN_ID
    contract_version = CONTRACT_VERSION
    adapter_version = ADAPTER_VERSION
    roles = ROLES

    def __init__(self) -> None:
        self._defaults = EnergyDefaults()
        self._schema = schema()

    @property
    def manifest(self) -> DomainManifest:
        return MANIFEST

    # ------------------------------------------------------------------
    def initial_state(self, scenario_id: str, seed: int) -> dict:
        return build_initial_state(scenario_id)

    def sample_exogenous(self, state: dict, rng: random.Random) -> dict:
        params = state["exogenous_params"]
        eps = (float(params["demand_ar1"]) * float(state["market"]["eps"])
               + rng.gauss(0.0, float(params["demand_sigma"])))
        return {
            "demand_shock": round(eps, 6),
            "wind_availability": round(
                rng.uniform(float(params["wind_min"]), float(params["wind_max"])), 6),
        }

    # ------------------------------------------------------------------
    def action_space(self, state: dict, role_slot: str, rng: random.Random,
                     n: int) -> list[Action]:
        role = role_slot.rsplit("_", 1)[0]
        default = self._defaults.action_for(state, role_slot, None,
                                            StepContext(0, 0, {}, state["scenario_id"]))
        candidates = [default]
        for cand in self._schema.sample_candidates(role, role_slot, rng, max(0, n - 1)):
            fields = dict(cand.fields)
            if role == "generator":
                cap = state["generators"][role_slot]["cap"]
                if fields.get("maintenance"):
                    fields["capacity_offered"] = 0.0
                else:
                    fields["capacity_offered"] = round(min(fields["capacity_offered"], cap), 4)
            candidates.append(Action(role=role, slot=role_slot, fields=fields))
        return candidates

    def preview(self, state: dict, action: Action, ctx: StepContext) -> Preview:
        actions = self._default_actions(state, ctx)
        actions[action.slot] = action
        metrics = self._clear(state, actions, ctx.exogenous)
        return Preview(projected_metrics=metrics)

    def validate_semantic(self, state: dict, action: Action) -> RejectionInfo | None:
        if action.role == "generator":
            bid = GeneratorBid.from_fields(action.fields)
            cap = state["generators"][action.slot]["cap"]
            if bid.capacity_offered > cap + 1e-9:
                return RejectionInfo("adapter_semantic", "capacity_exceeded",
                                     f"{action.slot} offered {bid.capacity_offered} > cap {cap}")
            if bid.maintenance and bid.capacity_offered > 1e-9:
                return RejectionInfo("adapter_semantic", "maintenance_conflict",
                                     "maintenance unit cannot offer capacity")
        return None

    # ------------------------------------------------------------------
    def step(self, state: dict, actions: dict[str, Action], ctx: StepContext) -> Outcome:
        intake = ctx.config.get("intake", {"submitted": {}, "rejected": {}, "sources": {}})

        defaults = self._default_actions(state, ctx)
        applied: dict[str, Action] = dict(defaults)
        completed: dict[str, str] = {}
        reasons: dict[str, str] = {}
        sources: dict[str, str] = {}
        for slot in applied:
            if slot in actions:
                applied[slot] = actions[slot]
                sources[slot] = intake["sources"].get(slot, "human")
            else:
                completed[slot] = defaults[slot].digest()
                sources[slot] = "domain_default"
                reasons[slot] = ("rejected_upstream" if slot in intake["rejected"]
                                 else "no_accepted_action")

        applied_metrics = self._clear(state, applied, ctx.exogenous)
        authoritative_metrics = self._clear(state, defaults, ctx.exogenous)  # same exogenous (SC-I1)

        regulator_action = applied["regulator_1"]
        state_next = {
            "round": state["round"] + 1,
            "scenario_id": state["scenario_id"],
            "policy": dict(regulator_action.fields),
            "market": {
                "last_clearing_price": applied_metrics["clearing_price"],
                "last_demand": applied_metrics["consumer_cost"]
                / max(applied_metrics["clearing_price"], 1e-9),
                "eps": ctx.exogenous["demand_shock"],
            },
            "generators": state["generators"],
            "exogenous_params": state["exogenous_params"],
        }

        report = ResolutionReport(
            submitted=dict(intake["submitted"]),
            accepted={s: a.digest() for s, a in actions.items()},
            completed=completed,
            rejected=dict(intake["rejected"]),
            sources=sources,
            completion_reasons=reasons,
        )
        return Outcome(
            role_outcomes={s: {"action": a.fields} for s, a in applied.items()},
            system_metrics=applied_metrics,
            state_next=state_next,
            branches={"authoritative": authoritative_metrics, "applied": applied_metrics},
            resolution=report,
            meta={
                "adapter_version": ADAPTER_VERSION,
                "approximations": ["aggregate_uniform_price_auction"],
                "provenance": {"scenario_id": state["scenario_id"]},
                "resolved_actions": applied,
            },
        )

    # ------------------------------------------------------------------
    @property
    def default_action_provider(self) -> EnergyDefaults:
        return self._defaults

    def _default_actions(self, state: dict, ctx: StepContext) -> dict[str, Action]:
        out: dict[str, Action] = {}
        for role in self.roles:
            for slot in role.slots():
                out[slot] = self._defaults.action_for(state, slot, None, ctx)
        return out

    def _clear(self, state: dict, actions: dict[str, Action], exogenous: dict) -> dict:
        return clear_market(
            policy=actions["regulator_1"].fields,
            generator_actions={s: a.fields for s, a in actions.items()
                               if s.startswith("generator_")},
            retailer_actions={s: a.fields for s, a in actions.items()
                              if s.startswith("retailer_")},
            exogenous=exogenous,
            params=state["generators"],
        )
