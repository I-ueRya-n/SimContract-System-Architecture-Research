"""E2-E5 strong matrix: rerun identity, replay equivalence, negative controls,
invariant suite, and controller-interface compatibility at scale.

Matrix: 2 domains x all declared scenarios x {rule, random_valid, top_score}
x 30 seeds x 6 rounds = 360 canonical runs; every run is re-executed once
(rerun identity) and replayed once from its bundle (replay equivalence).
Negative controls per (domain, scenario, condition): a config change must
change the content hash, and a tampered bundle must fail verification.

Usage:
  PYTHONPATH=src python3 experiments/strong_matrix.py            # full matrix
  PYTHONPATH=src python3 experiments/strong_matrix.py --verify   # recompute aggregates
Output: paper2_evidence/strong_matrix/
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e5_invariant_suite import check_bundle  # noqa: E402

from simcontract.composition import create_application  # noqa: E402
from simcontract.contracts import BundleView  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper2_evidence" / "strong_matrix"

DOMAINS = ["energy_market_v1", "epidemic_policy_v1"]
CONDITIONS = ["rule", "random_valid", "top_score"]
SEEDS = range(1, 31)
ROUNDS = 6
INVARIANTS = [f"SC-I{i}" for i in range(1, 8)]


def one_config(app, domain, scenario, condition, seed, workdir: Path,
               with_negative_controls: bool) -> dict:
    run1 = workdir / "run1"
    s1 = app.run_session(domain=domain, scenario=scenario, seed=seed,
                         rounds=ROUNDS, conditions={"all": condition},
                         personas={}, out_dir=run1)
    run2 = workdir / "run2"
    s2 = app.run_session(domain=domain, scenario=scenario, seed=seed,
                         rounds=ROUNDS, conditions={"all": condition},
                         personas={}, out_dir=run2)
    rerun_match = s1["content_hash"] == s2["content_hash"]
    shutil.rmtree(run2)

    rep = app.replay_run(run1)
    invariants = check_bundle(run1)

    view = BundleView.load(run1)
    conditions_ok = all(tag == condition
                        for r in view.rounds
                        for tag in r.resolution["sources"].values())
    row = {
        "domain": domain, "scenario": scenario, "condition": condition,
        "seed": seed, "content_hash": s1["content_hash"][:16],
        "rerun_match": rerun_match,
        "replay_equal": rep.equal_rounds, "replay_total": rep.rounds_compared,
        "rounds_completed": len(view.rounds), "decisions": len(view.decisions),
        "fallback_events": len(view.events),
        "all_sources_match_condition": conditions_ok,
        "invariants": invariants,
    }

    if with_negative_controls:
        run3 = workdir / "run3"
        s3 = app.run_session(domain=domain, scenario=scenario, seed=seed,
                             rounds=ROUNDS + 1, conditions={"all": condition},
                             personas={}, out_dir=run3)
        row["config_change_detected"] = s3["content_hash"] != s1["content_hash"]
        shutil.rmtree(run3)

        tampered = workdir / "tampered"
        shutil.copytree(run1, tampered)
        rounds_file = tampered / "rounds.json"
        rounds_file.write_text(
            rounds_file.read_text().replace('"round_no": 1', '"round_no": 9', 1))
        v = app.verify_bundle(tampered)
        row["tamper_detected"] = not (v.get("content_hash_ok") and v.get("files_ok"))
        shutil.rmtree(tampered)

    shutil.rmtree(run1)
    return row


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    inv_pass = {i: sum(1 for r in rows if r["invariants"][i]) for i in INVARIANTS}
    neg = [r for r in rows if "config_change_detected" in r]
    by_cond = defaultdict(lambda: {"runs": 0, "rerun": 0, "replay": 0,
                                   "fallbacks": 0, "sources_ok": 0})
    for r in rows:
        c = by_cond[r["condition"]]
        c["runs"] += 1
        c["rerun"] += r["rerun_match"]
        c["replay"] += (r["replay_equal"] == r["replay_total"])
        c["fallbacks"] += r["fallback_events"]
        c["sources_ok"] += r["all_sources_match_condition"]
    return {
        "canonical_runs": n,
        "rerun_hash_match": sum(r["rerun_match"] for r in rows),
        "replay_equivalent_runs": sum(
            1 for r in rows if r["replay_equal"] == r["replay_total"]),
        "replay_rounds_equal": sum(r["replay_equal"] for r in rows),
        "replay_rounds_total": sum(r["replay_total"] for r in rows),
        "rounds_completed_ok": sum(1 for r in rows if r["rounds_completed"] == ROUNDS),
        "total_decisions": sum(r["decisions"] for r in rows),
        "total_fallback_events": sum(r["fallback_events"] for r in rows),
        "source_tags_match_condition": sum(
            1 for r in rows if r["all_sources_match_condition"]),
        "invariant_pass": inv_pass,
        "negative_controls": {
            "configs": len(neg),
            "config_change_detected": sum(r["config_change_detected"] for r in neg),
            "tamper_detected": sum(r["tamper_detected"] for r in neg),
        },
        "by_condition": dict(by_cond),
    }


def write_outputs(rows: list[dict], agg: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "per_run_results.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    (OUT / "aggregate_results.json").write_text(json.dumps(agg, indent=2, sort_keys=True))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    (OUT / "environment.json").write_text(json.dumps({
        "python": sys.version.split()[0], "platform": platform.platform(),
        "software_commit": commit,
        "matrix": f"{len(DOMAINS)} domains x all scenarios x {CONDITIONS} x "
                  f"{len(list(SEEDS))} seeds x {ROUNDS} rounds",
    }, indent=2))


def verify() -> int:
    rows = [json.loads(l) for l in open(OUT / "per_run_results.jsonl")]
    stored = json.load(open(OUT / "aggregate_results.json"))
    ok = json.dumps(stored, sort_keys=True) == json.dumps(
        json.loads(json.dumps(aggregate(rows))), sort_keys=True)
    print(f"[strong-matrix verify] aggregates match per-run records: {ok}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        return verify()
    app = create_application()
    rows = []
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for domain in DOMAINS:
            scenarios = app.list_domains()  # warm registry; scenarios read below
            adapter = app._registry.create(domain)
            for scenario in adapter.manifest.scenario_ids:
                for condition in CONDITIONS:
                    for seed in SEEDS:
                        rows.append(one_config(
                            app, domain, scenario, condition, seed,
                            work, with_negative_controls=(seed == 1)))
    agg = aggregate(rows)
    write_outputs(rows, agg)
    print(f"[strong-matrix] runs={agg['canonical_runs']} "
          f"rerun={agg['rerun_hash_match']} "
          f"replay={agg['replay_equivalent_runs']} "
          f"rounds_ok={agg['rounds_completed_ok']} "
          f"fallbacks={agg['total_fallback_events']} "
          f"neg={agg['negative_controls']}")
    for i in INVARIANTS:
        print(f"  {i}: {agg['invariant_pass'][i]}/{agg['canonical_runs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
