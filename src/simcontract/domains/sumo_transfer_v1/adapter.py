"""SUMO Level-1 adapter: wraps an external, non-co-designed simulator
(Eclipse SUMO, via its public ``traci`` API) behind the frozen
SimulationAdapter protocol, with zero changes to contracts/, engine/, or
analysis/.

See docs/protocols/p2a_sumo_level1_transfer.md for the full design
rationale. Two points that would otherwise look like bugs are deliberate,
protocol-documented design choices:

- Uninterrupted execution (not ``saveState``/``loadState``) is the
  authoritative run semantics. ``saveState`` is used only as a bounded,
  local device to fork the single-round authoritative (default-action)
  counterfactual alongside the continuing applied trajectory -- the probe
  (protocol Sec. 4) found checkpoint reload repeatable but not equivalent
  to uninterrupted execution beyond ~5 simulated seconds, so it is never
  used to carry the real run forward across rounds.
- The domain default policy is a fixed phase (0), not "leave the network
  file's own program running unmanaged" -- this keeps the
  default/applied branch comparison symmetric.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import traci

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

from .defaults import SumoDefaults
from .manifest import ADAPTER_VERSION, DOMAIN_ID, MANIFEST, ROLES

_HERE = Path(__file__).parent
_SCENARIO_DIR = _HERE / "scenarios" / "grid3x3_v1"
_NET = str(_SCENARIO_DIR / "net.xml")
_ROUTES_BY_SCENARIO = {
    "grid3x3_moderate_v1": str(_SCENARIO_DIR / "routes_moderate.rou.xml"),
    "grid3x3_dense_v1": str(_SCENARIO_DIR / "routes_dense.rou.xml"),
}
_TLS = "B1"
_SLOT = "traffic_authority_1"
ROUND_SECONDS = 5  # inside the probe's verified exact-match window (protocol Sec. 4/6)


def _sumo_binary() -> str:
    """Resolve the sumo binary from the installed ``eclipse-sumo`` package
    rather than relying on the shell PATH/SUMO_HOME being set."""
    import sumo as _sumo_pkg
    return os.path.join(os.path.dirname(_sumo_pkg.__file__), "bin", "sumo")


def schema() -> ActionSchema:
    return ActionSchema.from_file(_HERE / "contract" / "action_schema.yaml")


def catalog() -> MetricCatalog:
    return MetricCatalog.from_file(_HERE / "contract" / "metric_catalog.yaml")


def observation() -> ObservationPolicy:
    return ObservationPolicy.from_file(_HERE / "contract" / "observation_policy.yaml")


def weights_for(role: str, persona: str | None) -> dict[str, float]:
    return {}


def _waiting_time(conn) -> float:
    return float(sum(conn.vehicle.getWaitingTime(v) for v in conn.vehicle.getIDList()))


def _start_args(scenario_id: str, seed: int, load_state: str | None = None) -> list[str]:
    args = [_sumo_binary(), "-n", _NET, "-r", _ROUTES_BY_SCENARIO[scenario_id],
            "--seed", str(seed), "--no-step-log", "true", "--no-warnings", "true"]
    if load_state:
        args += ["--load-state", load_state]
    return args


class SumoTransferAdapter:
    """One live SUMO connection per adapter instance. ``AdapterRegistry``
    constructs a fresh instance per run (see ``plugins/registry.py``), so
    each instance owns exactly one connection for exactly one run --
    including the fresh rerun ``engine/replay_executor.py`` already
    performs for every domain.
    """

    domain_id = DOMAIN_ID
    contract_version = CONTRACT_VERSION
    adapter_version = ADAPTER_VERSION
    roles = ROLES

    def __init__(self) -> None:
        self._defaults = SumoDefaults()
        self._schema = schema()
        self._label: str | None = None
        self._started = False

    @property
    def manifest(self) -> DomainManifest:
        return MANIFEST

    # ------------------------------------------------------------------
    def initial_state(self, scenario_id: str, seed: int) -> dict:
        if scenario_id not in _ROUTES_BY_SCENARIO:
            raise KeyError(f"unknown scenario {scenario_id!r}")
        self._label = f"sumo_transfer_{uuid.uuid4().hex}"
        traci.start(_start_args(scenario_id, seed), label=self._label)
        self._started = True
        return {"round": 0, "scenario_id": scenario_id, "seed": seed}

    def _conn(self):
        return traci.getConnection(self._label)

    def sample_exogenous(self, state: dict, rng) -> dict:
        # SUMO's own arrival process is fully determined by the fixed seed
        # passed to traci.start() in initial_state(); there is no separate
        # per-round exogenous draw here. Disclosed simplification (protocol
        # Sec. 4a): exogenous_digest is constant across rounds for this
        # domain.
        return {}

    def action_space(self, state, role_slot, rng, n: int) -> list[Action]:
        default = self._defaults.action_for(state, role_slot, None,
                                            StepContext(0, 0, {}, state["scenario_id"]))
        candidates = [default]
        candidates += self._schema.sample_candidates("traffic_authority", role_slot,
                                                      rng, max(0, n - 1))
        return candidates

    def preview(self, state, action: Action, ctx: StepContext) -> Preview:
        # Disclosed approximation (protocol Sec. 4a/8): a real preview would
        # require forking another live connection per candidate. This
        # minimal adapter returns the last-observed metric unchanged;
        # never used for a committed decision by the `rule` condition this
        # smoke test exercises (RuleController ignores previews entirely).
        return Preview(projected_metrics={"waiting_time": _waiting_time(self._conn())})

    def validate_semantic(self, state, action: Action) -> RejectionInfo | None:
        return None

    # ------------------------------------------------------------------
    def step(self, state, actions: dict[str, Action], ctx: StepContext) -> Outcome:
        intake = ctx.config.get("intake", {"submitted": {}, "rejected": {}, "sources": {}})
        default = self._defaults.action_for(state, _SLOT, None, ctx)

        completed, reasons, sources = {}, {}, {}
        if _SLOT in actions:
            applied_action = actions[_SLOT]
            sources[_SLOT] = intake["sources"].get(_SLOT, "human")
        else:
            applied_action = default
            completed[_SLOT] = default.digest()
            sources[_SLOT] = "domain_default"
            reasons[_SLOT] = ("rejected_upstream" if _SLOT in intake["rejected"]
                              else "no_accepted_action")

        conn = self._conn()

        # Fork the single-round authoritative (default-action) counterfactual
        # from a local checkpoint of the state entering this round -- never
        # the mechanism carrying the real run forward (protocol Sec. 4a/6).
        ckpt = f"/tmp/{self._label}_round{state['round']}.sumo"
        conn.simulation.saveState(ckpt)
        auth_label = f"{self._label}_auth_{state['round']}"
        traci.start(_start_args(state["scenario_id"], state["seed"], load_state=ckpt),
                   label=auth_label)
        auth_conn = traci.getConnection(auth_label)
        auth_conn.trafficlight.setPhase(_TLS, int(default.fields["phase"]))
        auth_conn.trafficlight.setPhaseDuration(_TLS, ROUND_SECONDS + 1)
        for _ in range(ROUND_SECONDS):
            auth_conn.simulationStep()
        authoritative_metrics = {"waiting_time": _waiting_time(auth_conn)}
        auth_conn.close()
        try:
            os.remove(ckpt)
        except OSError:
            pass

        # Continue the real, single, uninterrupted trajectory with the
        # applied action -- this is the authoritative run semantics.
        conn.trafficlight.setPhase(_TLS, int(applied_action.fields["phase"]))
        conn.trafficlight.setPhaseDuration(_TLS, ROUND_SECONDS + 1)
        for _ in range(ROUND_SECONDS):
            conn.simulationStep()
        applied_metrics = {"waiting_time": _waiting_time(conn)}

        report = ResolutionReport(
            submitted=dict(intake["submitted"]),
            accepted={s: a.digest() for s, a in actions.items()},
            completed=completed,
            rejected=dict(intake["rejected"]),
            sources=sources,
            completion_reasons=reasons,
        )
        return Outcome(
            role_outcomes={_SLOT: {"action": applied_action.fields}},
            system_metrics=applied_metrics,
            state_next={"round": state["round"] + 1, "scenario_id": state["scenario_id"],
                       "seed": state["seed"]},
            branches={"authoritative": authoritative_metrics, "applied": applied_metrics},
            resolution=report,
            meta={"adapter_version": ADAPTER_VERSION,
                 "approximations": [
                     "preview_returns_last_observed_metric_not_a_forward_simulation",
                     "authoritative_branch_computed_via_local_saveState_fork_"
                     "disclosed_limitation_protocol_sec4a",
                     "sample_exogenous_returns_empty_dict_no_per_round_draw",
                 ],
                 "provenance": {"scenario_id": state["scenario_id"]},
                 "resolved_actions": {_SLOT: applied_action}},
        )

    @property
    def default_action_provider(self) -> SumoDefaults:
        return self._defaults

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Adapter-owned explicit lifecycle method -- not part of
        ``SimulationAdapter`` (adding it does not modify the frozen
        contract; the protocol just does not require it to exist).
        ``SimulationAdapter`` has no teardown hook -- every existing domain
        is a pure function with nothing to release, which is a real
        architectural gap this adapter exposes. Callers that need
        deterministic cleanup (e.g. a confirmatory matrix that must prove
        zero leaked SUMO processes) should call this explicitly in a
        ``finally`` block rather than rely on ``__del__``, whose timing
        CPython does not guarantee across all execution paths."""
        if getattr(self, "_started", False):
            try:
                traci.getConnection(self._label).close()
            except Exception:
                pass
            self._started = False

    def __del__(self) -> None:
        # Safety net only, not the primary cleanup mechanism -- see close().
        self.close()
