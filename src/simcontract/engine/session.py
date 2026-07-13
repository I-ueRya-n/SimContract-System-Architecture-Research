"""Session runner: the round loop of spec 6.1."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any

from simcontract.contracts import (
    Action,
    ActionSchema,
    DecisionRecord,
    FailureRecord,
    InvocationRecord,
    MetricCatalog,
    ObservationPolicy,
    RoundRecord,
    RunManifest,
    SimulationAdapter,
    digest,
)

from .controllers import ControllerResult, state_digest_of
from .seeding import derive_seed, rng_for


@dataclass
class SessionResult:
    manifest: RunManifest
    rounds: list[RoundRecord] = field(default_factory=list)
    decisions: list[DecisionRecord] = field(default_factory=list)
    events: list[FailureRecord] = field(default_factory=list)
    invocations: list[InvocationRecord] = field(default_factory=list)
    final_state: Any = None


class SessionRunner:
    def __init__(self, adapter: SimulationAdapter, schema: ActionSchema,
                 observation: ObservationPolicy, catalog: MetricCatalog,
                 candidate_count: int = 8):
        self.adapter = adapter
        self.schema = schema
        self.observation = observation
        self.catalog = catalog
        self.candidate_count = candidate_count

    # ------------------------------------------------------------------
    def run(self, *, scenario_id: str, run_seed: int, rounds: int,
            controllers: dict[str, Any], personas: dict[str, str | None],
            run_id: str | None = None,
            preset_actions: dict[int, dict[str, dict[str, Any]]] | None = None,
            on_round=None) -> SessionResult:
        """Execute a session.

        ``controllers`` maps role slot -> controller object (spec 6.3).
        ``preset_actions`` (replay): {round_no: {slot: fields}} submitted as-is
        with source tag ``human`` semantics bypassed — used by replay to
        re-execute recorded resolutions.
        """
        adapter = self.adapter
        manifest = RunManifest(
            run_id=run_id or f"{adapter.domain_id}-{run_seed}",
            domain_id=adapter.domain_id,
            scenario_id=scenario_id,
            contract_version=adapter.contract_version,
            adapter_version=getattr(adapter, "adapter_version", "0"),
            run_seed=run_seed,
            rounds=rounds,
            conditions={s: getattr(c, "condition", "preset") for s, c in controllers.items()},
            personas=dict(personas),
            config_digest=digest({"candidates": self.candidate_count}),
            created_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        )
        result = SessionResult(manifest=manifest)

        state = adapter.initial_state(scenario_id, run_seed)
        stage_order = sorted({r.stage for r in adapter.roles})

        for round_no in range(1, rounds + 1):
            round_seed = derive_seed(run_seed, round_no)
            exogenous = adapter.sample_exogenous(state, rng_for(round_seed, "exogenous"))
            from simcontract.contracts import StepContext  # local import keeps module top light

            ctx = StepContext(round_no=round_no, round_seed=round_seed,
                              exogenous=exogenous, scenario_id=scenario_id)

            accepted: dict[str, Action] = {}
            intake_submitted: dict[str, str] = {}
            intake_rejected: dict[str, dict[str, str]] = {}
            intake_sources: dict[str, str] = {}

            for stage in stage_order:
                for spec_role in [r for r in adapter.roles if r.stage == stage]:
                    for slot in spec_role.slots():
                        self._resolve_slot(
                            slot=slot, role=spec_role.role, state=state, ctx=ctx,
                            controllers=controllers, personas=personas,
                            preset=(preset_actions or {}).get(round_no, {}).get(slot),
                            accepted=accepted, intake_submitted=intake_submitted,
                            intake_rejected=intake_rejected,
                            intake_sources=intake_sources, result=result,
                        )

            ctx.config["intake"] = {
                "submitted": intake_submitted,
                "rejected": intake_rejected,
                "sources": intake_sources,
            }
            outcome = adapter.step(state, accepted, ctx)

            unknown = self.catalog.validate_metrics(outcome.system_metrics)
            if unknown:
                raise ValueError(f"metrics not in catalog: {unknown}")

            resolved_actions = {
                slot: {"role": a.role, "fields": a.fields}
                for slot, a in outcome.meta.get("resolved_actions", {}).items()
            }
            result.rounds.append(RoundRecord(
                round_no=round_no,
                round_seed=round_seed,
                exogenous_digest=digest(exogenous),
                system_metrics=outcome.system_metrics,
                branches=outcome.branches,
                resolution=outcome.resolution.to_dict(),
                resolved_actions=resolved_actions,
            ))
            state = outcome.state_next
            if on_round is not None:
                on_round(round_no, outcome)

        result.final_state = state
        return result

    # ------------------------------------------------------------------
    def _resolve_slot(self, *, slot, role, state, ctx, controllers, personas,
                      preset, accepted, intake_submitted, intake_rejected,
                      intake_sources, result: SessionResult) -> None:
        view = self.observation.view(state, role)

        if preset is not None:  # replay path
            action = Action(role=role, slot=slot, fields=dict(preset))
            accepted[slot] = action
            intake_submitted[slot] = action.digest()
            intake_sources[slot] = "human"
            return

        controller = controllers.get(slot)
        if controller is None:  # unassigned slot -> domain completes (SC-I2)
            return

        rng_c = rng_for(ctx.round_seed, slot, "candidates")
        candidates = self.adapter.action_space(state, slot, rng_c, self.candidate_count)
        previews = [self.adapter.preview(state, a, ctx) for a in candidates]

        cres: ControllerResult = controller.act(view, slot, candidates, previews, ctx)
        if cres.llm_record is not None:
            result.invocations.append(InvocationRecord(
                round_no=ctx.round_no, slot=slot, **cres.llm_record))

        condition = getattr(controller, "condition", "unknown")
        state_dig = state_digest_of(view)

        if cres.action is None:
            result.events.append(FailureRecord(
                round_no=ctx.round_no, slot=slot, stage="select",
                family="llm" if "llm" in condition else "controller",
                reason=cres.fallback_reason or "controller_absent"))
            result.decisions.append(DecisionRecord(
                round_no=ctx.round_no, role=role, slot=slot, condition=condition,
                persona=personas.get(slot), candidate_digests=[a.digest() for a in candidates],
                scores=cres.scores, selected_digest=None, source_tag=condition,
                rationale=cres.rationale, state_digest=state_dig))
            return

        action = cres.action
        intake_submitted[slot] = action.digest()

        rejection = self.schema.validate_syntactic(action)          # engine tier
        if rejection is None:
            rejection = self.adapter.validate_semantic(state, action)  # adapter tier
        if rejection is not None:
            intake_rejected[slot] = rejection.to_dict()
            result.events.append(FailureRecord(
                round_no=ctx.round_no, slot=slot, stage="validate",
                family="adapter" if rejection.stage == "adapter_semantic" else "controller",
                reason=rejection.code, detail=rejection.detail))
            result.decisions.append(DecisionRecord(
                round_no=ctx.round_no, role=role, slot=slot, condition=condition,
                persona=personas.get(slot), candidate_digests=[a.digest() for a in candidates],
                scores=cres.scores, selected_digest=action.digest(), source_tag=condition,
                rationale=cres.rationale, state_digest=state_dig))
            return

        accepted[slot] = action
        intake_sources[slot] = condition
        result.decisions.append(DecisionRecord(
            round_no=ctx.round_no, role=role, slot=slot, condition=condition,
            persona=personas.get(slot), candidate_digests=[a.digest() for a in candidates],
            scores=cres.scores, selected_digest=action.digest(), source_tag=condition,
            rationale=cres.rationale, state_digest=state_dig))
