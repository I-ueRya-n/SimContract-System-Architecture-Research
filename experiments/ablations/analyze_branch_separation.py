"""Paper 2 ablation A2: offline analysis comparing same-resolution branch
separation against a separate default (rule) trajectory.

Protocol: docs/protocols/p2_ablation_no_branch_separation.md. This is an
OFFLINE ANALYSIS SCRIPT, not a wrapper: it generates paired runs through the
existing, unmodified public API (Application.run_session, using the
pre-existing on_round hook to capture pre-decision state) and computes all
divergences from the resulting bundles. No production code is touched, and
no runtime behaviour is altered -- the ablation is evaluated entirely by
comparison, never by suppressing a mechanism at execution time.

Usage:
  python experiments/ablations/analyze_branch_separation.py --pilot
  python experiments/ablations/analyze_branch_separation.py            # confirmatory
  python experiments/ablations/analyze_branch_separation.py --verify [--pilot]
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from simcontract.composition import create_application
from simcontract.contracts import BundleView

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "p2_ablation_no_branch_separation"
SUBMITTED_CONDITIONS = ["random_valid", "top_score"]
BASELINE_CONDITION = "rule"

# Documented, per-domain comparable pre-decision state field vectors (protocol
# S4/S6): dotted path -> extractor. These are state entering round t, i.e.
# state_next from round t-1 (or initial_state before round 1) -- never
# system_metrics from round t itself, to avoid duplicating the
# attribution-error endpoint.
#
# CORRECTED after the pilot (source-verified, not assumed): a field belongs in
# this vector only if the domain's own step/_clear/_simulate function actually
# reads it back. `state["policy"]` is written to state_next by both adapters
# but never read by either adapter (grep-verified: zero occurrences outside
# the state_next assignment) -- it is pure bookkeeping and was dropped.
# energy_market_v1's `_clear()` reads only `actions`, `exogenous`, and the
# per-run-constant `state["generators"]`; `state["market"]` is read nowhere
# except `sample_exogenous`'s `eps` term, and that AR(1) chain is identical
# across trajectories by construction (it depends only on the round-seeded
# RNG and its own recursion, never on submitted actions), which is exactly
# what the 100% exogenous_match_rate gate already confirms empirically. So
# energy_market_v1 has NO state field that mechanistically carries
# trajectory-distinguishing history into the outcome computation -- the field
# vector is deliberately empty, and `state_distance` returns 0.0 with an
# explicit "not applicable" reason rather than a misleading number. This is
# itself the structural-limitation finding (protocol S7), not a gap.
# epidemic_policy_v1's `_simulate()` reads `state["regions"]` (the SEIR
# compartments) directly -- genuine carried, trajectory-varying mechanistic
# state. `summary.*` is a low-dimensional, documented aggregate of `regions`
# (total infected/deaths/vaccinated), used instead of the full per-region
# vector to keep the field count small and stable across scenarios.
STATE_FIELDS = {
    "energy_market_v1": {},
    "epidemic_policy_v1": {
        "summary.total_infected": lambda s: s["summary"]["total_infected"],
        "summary.total_deaths": lambda s: s["summary"]["total_deaths"],
        "summary.total_vaccinated": lambda s: s["summary"]["total_vaccinated"],
    },
}


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


def run_one(app, domain: str, scenario: str, condition: str, seed: int,
           rounds: int, workdir: Path) -> tuple[BundleView, dict[int, dict]]:
    """Execute one session via the existing public API; capture pre-decision
    state per round via the pre-existing on_round hook. Returns (bundle,
    {round_no: state_entering_this_round})."""
    adapter_for_state = app._registry.create(domain)
    states_entering: dict[int, dict] = {1: adapter_for_state.initial_state(scenario, seed)}

    def on_round(round_no, outcome):
        states_entering[round_no + 1] = outcome.state_next

    out_dir = workdir / f"{domain}-{scenario}-{condition}-{seed}"
    app.run_session(domain=domain, scenario=scenario, seed=seed, rounds=rounds,
                    conditions={"all": condition}, personas={}, out_dir=out_dir,
                    on_round=on_round)
    bundle = BundleView.load(out_dir)
    shutil.rmtree(out_dir)
    return bundle, states_entering


def state_distance(fields: dict, s_sub: dict, s_rule: dict,
                   scales: dict[str, float]) -> float | None:
    """Mean absolute normalized difference over the documented field vector.
    Returns None (not 0.0) when the domain has no mechanistically carried
    state field, so "no carried state" is never silently confused with
    "carried state that happens to match"."""
    if not fields:
        return None
    diffs = []
    for name, extractor in fields.items():
        scale = scales.get(name, 1.0)
        diffs.append(abs(extractor(s_sub) - extractor(s_rule)) / scale)
    return sum(diffs) / len(diffs)


def iqr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    q1, q3 = statistics.quantiles(values, n=4)[0], statistics.quantiles(values, n=4)[2]
    return q3 - q1


def compute_scales(rule_runs: dict, domain: str, metric_keys: list[str]) -> dict:
    """Preregistered IQR normalization over the rule (default) population for
    this domain, for both metrics and state fields. Zero-IQR fallback: use
    (max-min); if that is also zero, use 1.0 and flag as constant."""
    scales, flags = {}, {}
    fields = STATE_FIELDS[domain]

    def _scale_for(values):
        v = iqr(values)
        if v > 0:
            return v, "iqr"
        span = max(values) - min(values) if values else 0.0
        if span > 0:
            return span, "iqr_zero_fallback_range"
        return 1.0, "constant_unnormalized"

    for m in metric_keys:
        vals = [r.system_metrics[m] for key, (bundle, _) in rule_runs.items()
                if key[0] == domain for r in bundle.rounds]
        scales[f"metric:{m}"], flags[f"metric:{m}"] = _scale_for(vals)
    for name, extractor in fields.items():
        vals = [extractor(states[t]) for key, (_, states) in rule_runs.items()
                if key[0] == domain for t in range(1, len(states))]
        scales[f"state:{name}"], flags[f"state:{name}"] = _scale_for(vals)
    return {"scales": scales, "flags": flags}


def build_config(pilot: bool) -> dict:
    if pilot:
        return {"domains": ["energy_market_v1"], "seeds": list(range(1, 6)),
                "rounds": 6, "mode": "pilot"}
    return {"domains": ["energy_market_v1", "epidemic_policy_v1"],
           "seeds": list(range(1, 31)), "rounds": 6, "mode": "confirmatory"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--domains", type=str, default=None,
                    help="override domain list, comma-separated (exploratory use)")
    ap.add_argument("--tag", type=str, default=None,
                    help="output subfolder suffix for exploratory sub-pilots")
    args = ap.parse_args()
    out_name = ("pilot" if args.pilot else "confirmatory") + (f"_{args.tag}" if args.tag else "")
    out = OUT_ROOT / out_name

    if args.verify:
        rows = [json.loads(l) for l in open(out / "per_metric_round.csv.jsonl")] \
            if (out / "per_metric_round.csv.jsonl").exists() else None
        print("[A2 verify] see aggregate_results.json; recompute path not "
              "wired for --verify in this exploratory pilot script.")
        return 0

    cfg = build_config(args.pilot)
    if args.domains:
        cfg["domains"] = args.domains.split(",")
    out.mkdir(parents=True, exist_ok=True)
    app = create_application()
    commit = _git_commit()

    gate_log: list[dict] = []
    pairing_keys = set()
    rule_runs: dict[tuple, tuple] = {}
    submitted_runs: dict[tuple, tuple] = {}

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for domain in cfg["domains"]:
            adapter = app._registry.create(domain)
            for scenario in adapter.manifest.scenario_ids:
                for seed in cfg["seeds"]:
                    key = (domain, scenario, seed)
                    assert key not in pairing_keys, f"duplicate pairing key {key}"
                    pairing_keys.add(key)
                    rule_runs[key] = run_one(app, domain, scenario,
                                             BASELINE_CONDITION, seed,
                                             cfg["rounds"], work)
                    for cond in SUBMITTED_CONDITIONS:
                        submitted_runs[key + (cond,)] = run_one(
                            app, domain, scenario, cond, seed, cfg["rounds"], work)

    # ---- Gate 1: pairing completeness ----
    missing = [k + (c,) for k in pairing_keys for c in SUBMITTED_CONDITIONS
              if k + (c,) not in submitted_runs]
    gate_log.append({"gate": "pairing_completeness", "pass": not missing,
                     "detail": f"{len(missing)} missing pairs"})

    # ---- Gate 2: rule equivalence (applied == authoritative every round) ----
    rule_violations = []
    for key, (bundle, _) in rule_runs.items():
        for r in bundle.rounds:
            for m, v in r.branches["applied"].items():
                if abs(v - r.branches["authoritative"][m]) > 1e-6:
                    rule_violations.append((key, r.round_no, m))
    gate_log.append({"gate": "rule_equivalence", "pass": not rule_violations,
                     "detail": f"{len(rule_violations)} round/metric violations"})

    # ---- Gate 3: exogenous equality ----
    exo_total, exo_match = 0, 0
    for key in pairing_keys:
        rule_bundle, _ = rule_runs[key]
        rule_digest = {r.round_no: r.exogenous_digest for r in rule_bundle.rounds}
        for cond in SUBMITTED_CONDITIONS:
            sub_bundle, _ = submitted_runs[key + (cond,)]
            for r in sub_bundle.rounds:
                exo_total += 1
                exo_match += (r.exogenous_digest == rule_digest[r.round_no])
    gate_log.append({"gate": "exogenous_equality", "pass": exo_total == exo_match,
                     "detail": f"{exo_match}/{exo_total} rounds match"})

    # ---- Gate 4: metric compatibility ----
    metric_mismatches = []
    for key in pairing_keys:
        rule_bundle, _ = rule_runs[key]
        rule_keys_per_round = [set(r.system_metrics) for r in rule_bundle.rounds]
        for cond in SUBMITTED_CONDITIONS:
            sub_bundle, _ = submitted_runs[key + (cond,)]
            for i, r in enumerate(sub_bundle.rounds):
                if set(r.system_metrics) != rule_keys_per_round[i]:
                    metric_mismatches.append((key, cond, r.round_no))
    gate_log.append({"gate": "metric_compatibility", "pass": not metric_mismatches,
                     "detail": f"{len(metric_mismatches)} mismatches"})

    # ---- Gate 5: no duplicate/self-pairing keys ----
    gate_log.append({"gate": "no_duplicate_keys",
                     "pass": len(pairing_keys) == len(set(pairing_keys)),
                     "detail": f"{len(pairing_keys)} unique keys"})

    # ---- Gate 6: round alignment ----
    align_bad = []
    for key in pairing_keys:
        rule_bundle, _ = rule_runs[key]
        rule_nos = [r.round_no for r in rule_bundle.rounds]
        for cond in SUBMITTED_CONDITIONS:
            sub_bundle, _ = submitted_runs[key + (cond,)]
            if [r.round_no for r in sub_bundle.rounds] != rule_nos:
                align_bad.append((key, cond))
    gate_log.append({"gate": "round_alignment", "pass": not align_bad,
                     "detail": f"{len(align_bad)} misaligned pairs"})

    gates_ok = all(g["pass"] for g in gate_log)
    (out / "pairing_audit.json").write_text(json.dumps({
        "pairing_keys": len(pairing_keys), "submitted_runs": len(submitted_runs),
        "rule_runs": len(rule_runs), "gates": gate_log, "all_gates_pass": gates_ok,
    }, indent=2, default=str))

    if not gates_ok:
        print("[A2] GATE FAILURE -- aborting before aggregate computation:")
        for g in gate_log:
            print(f"  {g['gate']}: {'PASS' if g['pass'] else 'FAIL'} ({g['detail']})")
        return 1

    # ---- Normalization scales (Gate 7 folded in: flags recorded) ----
    scales_by_domain = {}
    for domain in cfg["domains"]:
        metric_keys = list(next(iter(
            b.rounds[0].system_metrics for k, (b, _) in rule_runs.items()
            if k[0] == domain)))
        scales_by_domain[domain] = compute_scales(rule_runs, domain, metric_keys)
    (out / "normalization_scales.json").write_text(
        json.dumps(scales_by_domain, indent=2))

    # ---- Per-metric-round records ----
    rows = []
    exo_rows = []
    for key in sorted(pairing_keys):
        domain, scenario, seed = key
        rule_bundle, rule_states = rule_runs[key]
        rule_by_round = {r.round_no: r for r in rule_bundle.rounds}
        fields = STATE_FIELDS[domain]
        scales = scales_by_domain[domain]["scales"]
        cond_rank_input: dict[int, dict[str, dict[str, float]]] = {}
        for cond in SUBMITTED_CONDITIONS:
            sub_bundle, sub_states = submitted_runs[key + (cond,)]
            for r in sub_bundle.rounds:
                t = r.round_no
                rule_r = rule_by_round[t]
                exo_rows.append({"domain": domain, "scenario": scenario,
                                 "seed": seed, "round": t, "condition": cond,
                                 "match": r.exogenous_digest == rule_r.exogenous_digest})
                h_t = state_distance(fields, sub_states[t], rule_states[t],
                                     {k.split("state:")[-1]: v for k, v in scales.items()
                                      if k.startswith("state:")})
                for m in r.system_metrics:
                    d_local = r.branches["applied"][m] - r.branches["authoritative"][m]
                    d_traj = r.branches["applied"][m] - rule_r.branches["applied"][m]
                    scale = scales.get(f"metric:{m}", 1.0)
                    e_raw = abs(d_traj - d_local)
                    row = {"domain": domain, "scenario": scenario, "seed": seed,
                          "round": t, "condition": cond, "metric": m,
                          "d_local": d_local, "d_trajectory": d_traj,
                          "attribution_error": e_raw,
                          "attribution_error_normalized": e_raw / scale,
                          "sign_disagreement": (d_local * d_traj) < 0,
                          "trajectory_history_distance": h_t}
                    rows.append(row)
                    cond_rank_input.setdefault((t, m), {})[cond] = {
                        "local": d_local, "traj": d_traj}

        # rank disagreement between the two submitted conditions
        for (t, m), by_cond in cond_rank_input.items():
            if set(by_cond) == set(SUBMITTED_CONDITIONS):
                a, b = SUBMITTED_CONDITIONS
                rank_local = by_cond[a]["local"] > by_cond[b]["local"]
                rank_traj = by_cond[a]["traj"] > by_cond[b]["traj"]
                for cond in SUBMITTED_CONDITIONS:
                    for row in rows:
                        if (row["domain"] == domain and row["scenario"] == scenario
                                and row["seed"] == seed and row["round"] == t
                                and row["metric"] == m and row["condition"] == cond):
                            row["rank_disagreement"] = rank_local != rank_traj

    with open(out / "per_metric_round.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(out / "exogenous_match.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(exo_rows[0].keys()))
        w.writeheader()
        for r in exo_rows:
            w.writerow(r)

    # ---- Aggregate (overall, then per-domain -- domain heterogeneity in the
    # underlying step functions means pooling across domains would mask the
    # structural pattern the pilot exists to surface) ----
    def _agg_over(subset: list[dict]) -> dict:
        n = len(subset)
        if n == 0:
            return {"records": 0}
        err_by_round: dict[int, list[float]] = {}
        for r in subset:
            err_by_round.setdefault(r["round"], []).append(r["attribution_error_normalized"])
        ranked = [r for r in subset if "rank_disagreement" in r]
        h_vals = [r["trajectory_history_distance"] for r in subset
                 if r["trajectory_history_distance"] is not None]
        corr = None
        if len(h_vals) == n and n > 1 and len(set(h_vals)) > 1:
            errs = [r["attribution_error_normalized"] for r in subset]
            if len(set(errs)) > 1:
                corr = statistics.correlation(h_vals, errs)
        return {
            "records": n,
            "attribution_error_normalized": {
                "median": statistics.median(r["attribution_error_normalized"] for r in subset),
                "mean": statistics.fmean(r["attribution_error_normalized"] for r in subset),
                "max": max(r["attribution_error_normalized"] for r in subset),
            },
            "sign_disagreement_rate": sum(r["sign_disagreement"] for r in subset) / n,
            "rank_disagreement_rate": (sum(r["rank_disagreement"] for r in ranked) / len(ranked)
                                      if ranked else None),
            "error_growth_by_round": {
                t: statistics.fmean(vs) for t, vs in sorted(err_by_round.items())},
            "history_distance_defined": len(h_vals) == n,
            "history_error_correlation": corr,
        }

    agg = {"overall": _agg_over(rows), "exogenous_match_rate": exo_match / exo_total,
          "by_domain": {d: _agg_over([r for r in rows if r["domain"] == d])
                       for d in cfg["domains"]}}
    (out / "aggregate_results.json").write_text(json.dumps(agg, indent=2, default=str))
    (out / "environment.json").write_text(json.dumps({
        "software_commit": commit, "config": cfg}, indent=2))

    print(f"[A2 {out_name}] records={len(rows)} gates=ALL_PASS")
    for d, a in agg["by_domain"].items():
        print(f"  {d}: median_err={a['attribution_error_normalized']['median']:.4f} "
              f"sign_disagree={a['sign_disagreement_rate']:.3f} "
              f"rank_disagree={a['rank_disagreement_rate']}")
        print(f"    error_growth_by_round: {a['error_growth_by_round']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
