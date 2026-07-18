"""SUMO Level-1 adapter compliance/evidence-generation smoke test.

Protocol: docs/protocols/p2a_sumo_level1_transfer.md Sec. 8. This is the
adapter feasibility gate list, run before any confirmatory matrix:

  1. SUMO starts and terminates cleanly.
  2. At least two legal interventions produce distinguishable outcomes.
  3. Identical initial configuration, seed, and action schedule reproduce
     the same evidence content (via engine/replay_executor.py's existing
     full fresh rerun -- unmodified).
  4. A generic evidence bundle is generated and BundleView/verify_bundle
     consume it with zero changes.
  5. Integration effort (adapter-specific files/LOC vs. common-core diff)
     is recorded prospectively.

Usage: python experiments/sumo_transfer/smoke_test.py
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from simcontract.composition import create_application

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper2_evidence" / "p2a_sumo_level1_smoke"


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


def main() -> int:
    app = create_application()
    gates: list[dict] = []

    assert "sumo_transfer_v1" in app._registry.aliases(), (
        "sumo_transfer_v1 not registered -- composition.py import failed")
    gates.append({"gate": "registered_via_sanctioned_seam", "pass": True,
                 "detail": "sumo_transfer_v1 present in AdapterRegistry.aliases()"})

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)

        # ---- Gate 1: starts/terminates cleanly (rule condition: applied ==
        # authoritative every round by construction, same invariant A2
        # relies on for the other two domains -- not itself a divergence test) ----
        out_a = work / "run_a"
        res_a = app.run_session(domain="sumo_transfer_v1", scenario="grid3x3_v1",
                                seed=1, rounds=3, conditions={"all": "rule"},
                                personas={}, out_dir=out_a)
        bundle_a = res_a["result"]
        metrics_by_round = [r.system_metrics["waiting_time"] for r in bundle_a.rounds]
        gates.append({"gate": "starts_and_terminates_cleanly", "pass": True,
                     "detail": f"3-round rule-condition run completed, bundle={res_a['bundle']}"})

        # ---- Gate 2: distinguishable outcomes -- needs a condition that can
        # actually diverge from the default (rule cannot, by construction),
        # and enough simulated time for congestion to build at the junction ----
        out_b = work / "run_b"
        res_b = app.run_session(domain="sumo_transfer_v1", scenario="grid3x3_v1",
                                seed=2, rounds=10, conditions={"all": "random_valid"},
                                personas={}, out_dir=out_b)
        bundle_b = res_b["result"]
        auth_by_round = [r.branches["authoritative"]["waiting_time"] for r in bundle_b.rounds]
        applied_by_round = [r.branches["applied"]["waiting_time"] for r in bundle_b.rounds]
        distinguishable = any(a != b for a, b in zip(auth_by_round, applied_by_round))
        gates.append({"gate": "distinguishable_authoritative_vs_applied", "pass": distinguishable,
                     "detail": f"random_valid, 10 rounds: authoritative={auth_by_round} "
                               f"applied={applied_by_round}"})

        # ---- Gate 3: replay_run (full fresh rerun) reproduces recorded evidence ----
        bundle_dir_a = Path(res_a["bundle"])
        replay_report = app.replay_run(bundle_dir_a)
        gates.append({"gate": "replay_run_reproduces_evidence", "pass": replay_report.equivalent,
                     "detail": f"rounds_compared={replay_report.rounds_compared} "
                               f"equal_rounds={replay_report.equal_rounds} "
                               f"mismatches={replay_report.mismatches}"})

        # ---- Gate 4: generic bundle tools consume it unmodified ----
        verify_result = app.verify_bundle(bundle_dir_a)
        gates.append({"gate": "verify_bundle_unmodified", "pass": verify_result["content_hash_ok"],
                     "detail": f"content_hash_ok={verify_result['content_hash_ok']} "
                               f"files_ok={verify_result['files_ok']}"})

        analysis_out = work / "analysis"
        report_path = app.analyse_bundles([bundle_dir_a], out=analysis_out)
        gates.append({"gate": "generic_analyzer_unmodified", "pass": report_path.exists(),
                     "detail": f"report={report_path}"})

    all_pass = all(g["pass"] for g in gates)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "smoke_gates.json").write_text(json.dumps({
        "gates": gates, "all_gates_pass": all_pass,
        "software_commit": _git_commit(),
        "metrics_by_round": metrics_by_round,
    }, indent=2, default=str))

    print(f"[SUMO Level-1 smoke test] {'ALL GATES PASS' if all_pass else 'GATE FAILURE'}")
    for g in gates:
        print(f"  {g['gate']}: {'PASS' if g['pass'] else 'FAIL'} -- {g['detail']}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
