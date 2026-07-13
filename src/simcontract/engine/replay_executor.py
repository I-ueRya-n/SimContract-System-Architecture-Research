"""Decision replay: re-execute the engine path from a recorded bundle
(spec 8, SC-I1/I5). Bundle verification without execution lives in the
evidence layer (``evidence/replay_bundle.py``); rerun is ``run`` with the
recorded configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from simcontract.contracts import (
    ActionSchema,
    BundleView,
    MetricCatalog,
    ObservationPolicy,
    SimulationAdapter,
)
from .session import SessionRunner


@dataclass
class ReplayReport:
    rounds_compared: int = 0
    equal_rounds: int = 0
    mismatches: list[dict] = field(default_factory=list)

    @property
    def equivalent(self) -> bool:
        return self.rounds_compared > 0 and self.equal_rounds == self.rounds_compared


def replay_bundle(bundle: BundleView, adapter: SimulationAdapter,
                  schema: ActionSchema, observation: ObservationPolicy,
                  catalog: MetricCatalog) -> ReplayReport:
    """Re-execute using recorded resolved actions + recorded seeds; compare metrics."""
    preset = {
        r.round_no: {slot: a["fields"] for slot, a in r.resolved_actions.items()}
        for r in bundle.rounds
    }
    runner = SessionRunner(adapter, schema, observation, catalog)
    rerun = runner.run(
        scenario_id=bundle.manifest.scenario_id,
        run_seed=bundle.manifest.run_seed,
        rounds=bundle.manifest.rounds,
        controllers={},                      # all slots preset
        personas={},
        run_id=bundle.manifest.run_id + "-replay",
        preset_actions=preset,
    )
    report = ReplayReport()
    for original, again in zip(bundle.rounds, rerun.rounds):
        report.rounds_compared += 1
        if (original.system_metrics == again.system_metrics
                and original.branches == again.branches):
            report.equal_rounds += 1
        else:
            report.mismatches.append({
                "round": original.round_no,
                "original": original.system_metrics,
                "replayed": again.system_metrics,
            })
    return report
