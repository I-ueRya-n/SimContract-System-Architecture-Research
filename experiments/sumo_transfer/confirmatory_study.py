"""SUMO Level-1 confirmatory transfer study.

Protocol: docs/protocols/p2a_sumo_level1_transfer.md Sec. 10-14. 60
canonical runs: 1 network x 2 demand configurations x 3 deterministic
conditions x 10 paired seeds, 10 rounds x 5 simulated seconds each. Every
run is checked against the full Sec. 11 checklist before being counted.

Not `top_score`: `preview()` is a disclosed approximation (protocol Sec. 8)
returning the constant last-observed metric regardless of candidate, so
`top_score`'s ranking would be degenerate here. Two fixed, legal,
deterministic interventions are used instead: phase 2 (EW-priority) and
phase 1 (all-stop transitional) -- both distinguishable from `rule`'s
phase-0 (NS-priority) baseline and from each other. An earlier choice
(phase 1 vs. phase 3) was corrected after a first confirmatory pass showed
those two are a degenerate pair (protocol Sec. 10 correction note): both
are short all-restrictive yellow transitions, so locking either one for a
full round blocks the junction equivalently.

Explicit cleanup (protocol Sec. 12): this script constructs the adapter and
SessionRunner directly -- mirroring Application.run_session()'s own
construction path -- specifically so it can call adapter.close() in a
finally block, rather than relying on __del__ alone.

Usage: python experiments/sumo_transfer/confirmatory_study.py
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from simcontract.composition import create_application
from simcontract.contracts import Action, BundleView, ControllerResult, digest
from simcontract.engine.replay_executor import replay_bundle
from simcontract.engine.session import SessionRunner
from simcontract.evidence import BundleEvidenceWriter, verify_bundle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper2_evidence" / "p2a_sumo_level1_confirmatory"
SCENARIOS = ["grid3x3_moderate_v1", "grid3x3_dense_v1"]
CONDITIONS = ["rule", "fixed_valid_intervention_A", "fixed_valid_intervention_B"]
SEEDS = list(range(101, 111))
ROUNDS = 10


class FixedPhaseController:
    """Deliberately not top_score -- see module docstring and protocol Sec. 10."""

    def __init__(self, condition: str, phase: int):
        self.condition = condition
        self._phase = phase

    def act(self, view, slot, candidates, previews, ctx) -> ControllerResult:
        return ControllerResult(action=Action(role="traffic_authority", slot=slot,
                                              fields={"phase": self._phase}))


# phase 0 (rule/default) = NS-priority; phase 2 = EW-priority; phase 1 =
# all-stop transitional -- three genuinely distinguishable conditions.
# Not phase 1 vs phase 3 (see protocol Sec. 10 correction: both are
# all-restrictive yellow transitions, a degenerate pair).
PHASE_BY_CONDITION = {"fixed_valid_intervention_A": 2, "fixed_valid_intervention_B": 1}


def _sumo_process_count() -> int:
    r = subprocess.run(["pgrep", "-fc", "sumo"], capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def _controllers_for(app, adapter, schema, weights_for, condition: str):
    if condition == "rule":
        return app.build_controllers(adapter, schema, weights_for, {"all": "rule"}, {})
    return {"traffic_authority_1": FixedPhaseController(condition, PHASE_BY_CONDITION[condition])}


def run_one(app, scenario: str, condition: str, seed: int, out_dir: Path) -> dict:
    """Mirrors Application.run_session()'s construction path exactly, so
    this script can hold a reference to the adapter for explicit close()
    (protocol Sec. 12) -- Application.run_session() does not expose it."""
    adapter = app._registry.create("sumo_transfer_v1")
    schema, observation, catalog, weights_for = app._assets_for("sumo_transfer_v1")
    controllers = _controllers_for(app, adapter, schema, weights_for, condition)
    writer = BundleEvidenceWriter(out_dir)
    runner = SessionRunner(adapter, schema, observation, catalog, sink=writer)
    try:
        t0 = time.perf_counter()
        result = runner.run(scenario_id=scenario, run_seed=seed, rounds=ROUNDS,
                            controllers=controllers, personas={})
        wall_s = time.perf_counter() - t0
    finally:
        adapter.close()
    return {"bundle_dir": out_dir, "content_hash": writer.content_hash, "wall_s": wall_s}


def replay_one(app, bundle_dir: Path):
    """Mirrors Application.replay_run() exactly, so this script can hold a
    reference to the replay adapter for explicit close() too."""
    bundle = BundleView.load(bundle_dir)
    alias = bundle.manifest.domain_id
    adapter = app._registry.create(alias)
    schema, observation, catalog, _ = app._assets_for(alias)
    try:
        return replay_bundle(bundle, adapter, schema, observation, catalog)
    finally:
        adapter.close()


def main() -> int:
    app = create_application()
    OUT.mkdir(parents=True, exist_ok=True)
    procs_before = _sumo_process_count()

    records: list[dict] = []
    with_bundles_root = OUT / "bundles"
    with_bundles_root.mkdir(exist_ok=True)

    for scenario in SCENARIOS:
        for condition in CONDITIONS:
            for seed in SEEDS:
                run_id = f"{scenario}-{condition}-{seed}"
                out_dir = with_bundles_root / run_id
                run_info = run_one(app, scenario, condition, seed, out_dir)
                bundle = BundleView.load(out_dir)

                verify_result = verify_bundle(out_dir)
                replay_report = replay_one(app, out_dir)

                # generic analyzer compatibility, per run
                analysis_out = OUT / "analysis" / run_id
                report_path = app.analyse_bundles([out_dir], out=analysis_out)

                config_digest = digest({
                    "net_hash": digest(Path(ROOT / "src" / "simcontract" / "domains" /
                                            "sumo_transfer_v1" / "scenarios" / "grid3x3_v1" /
                                            "net.xml").read_bytes().decode("utf-8", "ignore")),
                    "scenario": scenario, "condition": condition, "seed": seed,
                })

                records.append({
                    "run_id": run_id,
                    "scenario": scenario,
                    "condition": condition,
                    "seed": seed,
                    "fresh_execution_ok": True,
                    "verify_bundle_ok": verify_result["content_hash_ok"] and verify_result["files_ok"],
                    "replay_equivalent": replay_report.equivalent,
                    "replay_mismatches": len(replay_report.mismatches),
                    "generic_analyzer_ok": report_path.exists(),
                    "config_digest": config_digest,
                    "bundle_bytes": sum(f.stat().st_size for f in out_dir.rglob("*") if f.is_file()),
                    "wall_s": run_info["wall_s"],
                    "rounds": len(bundle.rounds),
                })
                print(f"  [{len(records)}/60] {run_id}: "
                      f"verify={records[-1]['verify_bundle_ok']} "
                      f"replay={records[-1]['replay_equivalent']} "
                      f"mismatches={records[-1]['replay_mismatches']}")

    procs_after = _sumo_process_count()
    leaked = max(0, procs_after - procs_before)

    all_verify_ok = all(r["verify_bundle_ok"] for r in records)
    all_replay_ok = all(r["replay_equivalent"] for r in records)
    all_analyzer_ok = all(r["generic_analyzer_ok"] for r in records)
    total_mismatches = sum(r["replay_mismatches"] for r in records)

    summary = {
        "total_runs": len(records),
        "expected_runs": len(SCENARIOS) * len(CONDITIONS) * len(SEEDS),
        "run_level_replay_pass_rate": sum(r["replay_equivalent"] for r in records) / len(records),
        "evidence_mismatch_count": total_mismatches,
        "process_cleanup_failure_count": leaked,
        "contract_compliance_pass_rate": sum(r["verify_bundle_ok"] for r in records) / len(records),
        "generic_analyzer_pass_rate": sum(r["generic_analyzer_ok"] for r in records) / len(records),
        "sumo_processes_before": procs_before,
        "sumo_processes_after": procs_after,
        "total_bundle_bytes": sum(r["bundle_bytes"] for r in records),
        "mean_wall_s_per_run": sum(r["wall_s"] for r in records) / len(records),
        "all_gates_pass": (all_verify_ok and all_replay_ok and all_analyzer_ok
                          and leaked == 0 and len(records) == len(SCENARIOS) * len(CONDITIONS) * len(SEEDS)),
    }

    (OUT / "confirmatory_records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n")
    (OUT / "aggregate_results.json").write_text(json.dumps(summary, indent=2))

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    (OUT / "environment.json").write_text(json.dumps({
        "software_commit": commit,
        "scenarios": SCENARIOS, "conditions": CONDITIONS, "seeds": SEEDS, "rounds": ROUNDS,
    }, indent=2))

    print(f"\n[SUMO Level-1 confirmatory] {'GO' if summary['all_gates_pass'] else 'STOP'}")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0 if summary["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
