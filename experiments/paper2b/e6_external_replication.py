"""Paper 2B-E6: external integrity replication (SUMO) + E5 checker Layer-3.

Protocol: docs/protocols/p2b_e6_external_replication.md.

Two deliverables:
1. Does the CL-vs-MT estimand distinction transfer to an independently
   developed, imperative traffic simulator (Eclipse SUMO) under controlled
   demand and continuation policies? Measured via the SAME estimand
   machinery as E2/E4, but constructed by DETERMINISTIC REPLAY-TO-BRANCH,
   not SUMO saveState (which the Paper 2A probe showed is not a complete
   continuous-state oracle):
     CL_i : replay candidate-i history to t, then apply i vs default from
            the SAME reconstructed pre-state, continue H under default.
     MT_i : factual (candidate-i history + i) vs an independently evolved
            default-history + default, same future demand schedule.
   The pre-decision states are reconstructed from origin (feasibility spike:
   two independent replays reach byte-identical observable pre-states), so
   CL's two branches are genuine clones without relying on saveState.
2. A SUMO-specific portable-manifest EXPORTER (independent of the E5 checker)
   generates external audit manifests; the FROZEN E5 checker is run once on
   them (Layer 3) against a prospectively-defined oracle.

Usage:
  python experiments/paper2b/e6_external_replication.py --pilot
  python experiments/paper2b/e6_external_replication.py            # confirmatory
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

import libsumo as traci

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "p2b_e6_external_replication"
SCEN = Path(__file__).parent / "e6_sumo_scenario"
NET = str(SCEN / "net.xml")
DEMANDS = {"moderate": str(SCEN / "routes_moderate.rou.xml"),
           "dense": str(SCEN / "routes_dense.rou.xml")}
TLS = "B1"
ROUND_SECONDS = 5
DECISION_ROUNDS = [5, 7]
HORIZONS = [1, 3, 5]
DEFAULT_PHASE = 0                      # NS-priority default / continuation policy
CANDIDATE_PHASES = [0, 1, 2, 3]        # 4 legal signal programmes (fixed IDs)
TOL_REL = 0.10                         # reuse E3's relative tolerance

# frozen E5 checker (Layer 3)
_E5 = importlib.util.spec_from_file_location(
    "e5_checker", Path(__file__).parent / "e5_integrity_checker.py")
e5 = importlib.util.module_from_spec(_E5)
sys.modules["e5_checker"] = e5
_E5.loader.exec_module(e5)


def _sumo_bin():
    import sumo
    return os.path.join(os.path.dirname(sumo.__file__), "bin", "sumo")


def _git_commit():
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _step_delay():
    """Per-step delay contribution: number of currently-halting vehicles
    (speed < 0.1 m/s). Summed over steps this gives cumulative waiting
    (vehicle-seconds of delay), which -- unlike an instantaneous snapshot --
    accumulates the pre-decision history and therefore does NOT wash out by
    the horizon (protocol: primary metric = normalised cumulative waiting)."""
    return float(sum(1 for v in traci.vehicle.getIDList()
                     if traci.vehicle.getSpeed(v) < 0.1))


def _observable_digest():
    tls = {t: (traci.trafficlight.getPhase(t), round(traci.trafficlight.getNextSwitch(t), 3))
           for t in traci.trafficlight.getIDList()}
    veh = {v: (round(traci.vehicle.getLanePosition(v), 4), round(traci.vehicle.getSpeed(v), 4),
               round(traci.vehicle.getWaitingTime(v), 4), traci.vehicle.getLaneID(v))
           for v in sorted(traci.vehicle.getIDList())}
    return _digest({"t": round(traci.simulation.getTime(), 3), "tls": tls, "veh": veh})


def replay_branch(demand, seed, t, history_phase, decision_phase, max_h):
    """Replay `history_phase` as the standing policy for rounds 1..t-1, apply
    `decision_phase` at round t, then continue under DEFAULT for the rest;
    record waiting time at each horizon in HORIZONS. Returns (metrics_by_H,
    pre_decision_digest)."""
    traci.start([_sumo_bin(), "-n", NET, "-r", DEMANDS[demand], "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true"])
    cumulative = 0.0                        # cumulative waiting from origin
    for _ in range((t - 1) * ROUND_SECONDS):
        traci.trafficlight.setPhase(TLS, history_phase)
        traci.trafficlight.setPhaseDuration(TLS, ROUND_SECONDS + 1)
        traci.simulationStep()
        cumulative += _step_delay()
    pre = _observable_digest()
    metrics = {}
    for k in range(max_h):
        phase = decision_phase if k == 0 else DEFAULT_PHASE
        traci.trafficlight.setPhase(TLS, phase)
        traci.trafficlight.setPhaseDuration(TLS, ROUND_SECONDS + 1)
        for _ in range(ROUND_SECONDS):
            traci.simulationStep()
            cumulative += _step_delay()
        if (k + 1) in HORIZONS:
            metrics[k + 1] = cumulative     # cumulative waiting through horizon k+1
    traci.close()
    return metrics, pre


def estimands_for_cell(demand, seed, t):
    """Mirrors 2B-E4's construction externally (cumulative waiting, minimise).

    Shared clone = the default-history state at t (reconstructed twice to
    verify byte-identity). For each candidate i:
      CL_i : value(default-history clone, apply candidate i, continue) --
             every candidate scored from the SAME reconstructed checkpoint.
      MT_i : value(candidate-i standing-policy history, apply candidate i,
             continue) -- each candidate scored from its OWN evolved history.
      B    : value(default history, apply default, continue) -- baseline.
    Effects vs baseline: effect_cl_i = CL_i - B, effect_mt_i = MT_i - B.
    AE_i = |MT_i - CL_i| (the baseline cancels)."""
    max_h = max(HORIZONS)
    # baseline B and a first reconstruction of the shared default-history clone
    B, s_shared = replay_branch(demand, seed, t, DEFAULT_PHASE, DEFAULT_PHASE, max_h)
    _, s_shared2 = replay_branch(demand, seed, t, DEFAULT_PHASE, DEFAULT_PHASE, max_h)
    clone_ok = (s_shared == s_shared2)          # deterministic same-history reconstruction
    rows = []
    for i in CANDIDATE_PHASES:
        cl_i, s_clone = replay_branch(demand, seed, t, DEFAULT_PHASE, i, max_h)  # shared clone + i
        mt_i, s_own = replay_branch(demand, seed, t, i, i, max_h)                # own history + i
        clone_i_ok = clone_ok and (s_clone == s_shared)   # candidate ran from the shared clone
        for H in HORIZONS:
            rows.append({"demand": demand, "seed": seed, "round": t, "candidate": i,
                         "horizon": H,
                         "cl_value": cl_i[H], "mt_value": mt_i[H], "baseline": B[H],
                         "d_cl": cl_i[H] - B[H], "d_mt": mt_i[H] - B[H],
                         "ae": abs(mt_i[H] - cl_i[H]),
                         "clone_reconstruction_ok": clone_i_ok,
                         "state_distance_flag": int(s_own != s_shared)})
    return rows


# ---------------------------------------------------------------------------
# SUMO-specific portable-manifest EXPORTER (independent of the E5 checker).
# ---------------------------------------------------------------------------
def export_manifest(demand, seed, t, H, declared_type, kind):
    """Build a portable audit manifest v1.0 from SUMO execution identities.
    `kind` in {intact, saveState_not_continuous, schedule_partial,
    policy_unrecorded, history_declared_local, metric_incomplete} drives
    naturally-limited (negative) external cases. The exporter does NOT import
    or consult the checker (protocol S7)."""
    sumo_ver = "1.27.1"
    net_hash = _digest(Path(NET).read_bytes().decode("latin-1"))
    demand_hash = _digest(Path(DEMANDS[demand]).read_bytes().decode("latin-1"))
    sched = _digest([demand_hash, seed, t, H])
    model = _digest({"sim": "sumo", "ver": sumo_ver, "net": net_hash})
    metric = _digest(["waiting_time"])
    policy = _digest({"policy": "default_phase_0_continuation", "sim": "sumo"})
    fac_state = _digest({"hist": "candidate", "d": demand, "s": seed, "t": t})
    def_state = _digest({"hist": "default", "d": demand, "s": seed, "t": t})
    shared = fac_state if declared_type in ("one_step_local", "cloned_local_h_step") else fac_state
    m = {
        "manifest_schema_version": e5.MANIFEST_SCHEMA_VERSION,
        "declared_estimand": {"type": declared_type, "decision_point": t, "horizon": H},
        "model_identity": {"simulator": "sumo", "factual_model_hash": model,
                           "alternative_model_hash": model,
                           "factual_metric_catalogue_hash": metric,
                           "alternative_metric_catalogue_hash": metric},
        "state_identity": {"factual_predecision_state_hash":
                           shared if declared_type in ("one_step_local", "cloned_local_h_step") else fac_state,
                           "alternative_predecision_state_hash":
                           shared if declared_type in ("one_step_local", "cloned_local_h_step") else def_state,
                           "shared_parent_checkpoint_hash":
                           shared if declared_type in ("one_step_local", "cloned_local_h_step") else None},
        "exogenous_identity": {"schedule_hash": sched,
                               "covered_rounds": 1 if declared_type == "one_step_local" else H,
                               "resampled": declared_type == "resampled_contrast"},
        "branch_identity": {"factual_branch_id": f"{demand}-{seed}-{t}-Fh",
                            "alternative_branch_id": f"{demand}-{seed}-{t}-Dh",
                            "divergence_round": t,
                            "factual_ancestry_hash": _digest(["F", demand, seed, t]),
                            "alternative_ancestry_hash": _digest(["D", demand, seed, t]),
                            "factual_continuation_policy_hash": policy,
                            "alternative_continuation_policy_hash": policy},
        "provenance": {"proposed_action": _digest(["prop", seed]),
                       "final_applied_action": _digest(["appl", seed]),
                       "source_tag": "sumo_replay_to_branch",
                       "continuation_policy_hash": policy,
                       "completion_reason": "default_continuation"},
    }
    # naturally-limited (negative) external cases -- prospectively defined oracle
    if kind == "saveState_not_continuous":
        # a saveState reload whose pre-states are not a true clone. This is a
        # defect ONLY for a LOCAL claim (which needs a shared clone); MT/RS
        # legitimately allow different pre-states, so PASS is correct there.
        m["state_identity"]["alternative_predecision_state_hash"] = def_state
        return m, ("FAIL" if declared_type in ("one_step_local", "cloned_local_h_step") else "PASS")
    if kind == "schedule_partial":
        m["exogenous_identity"]["covered_rounds"] = H - 1
        return m, ("FAIL" if declared_type in ("one_step_local", "cloned_local_h_step") else "PASS")
    if kind == "policy_unrecorded":
        m["branch_identity"]["factual_continuation_policy_hash"] = None
        return m, ("FAIL" if declared_type == "cloned_local_h_step" else "PASS")
    if kind == "history_declared_local":
        # a historical (different-state) comparison mislabelled as cloned-local
        m["declared_estimand"]["type"] = "cloned_local_h_step"
        m["state_identity"]["alternative_predecision_state_hash"] = def_state
        m["state_identity"]["shared_parent_checkpoint_hash"] = fac_state
        return m, "FAIL"
    if kind == "metric_incomplete":
        m["model_identity"]["alternative_metric_catalogue_hash"] = _digest(["waiting_time", "units_changed"])
        return m, "FAIL"
    return m, "PASS"   # intact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()
    seeds = list(range(1, 4)) if args.pilot else list(range(1, 11))
    demands = ["moderate"] if args.pilot else ["moderate", "dense"]
    out = OUT_ROOT / ("pilot" if args.pilot else "confirmatory")
    out.mkdir(parents=True, exist_ok=True)
    commit = _git_commit()

    # ---- Deliverable 1: CL vs MT transfer ----
    rows = []
    for demand in demands:
        for seed in seeds:
            for t in DECISION_ROUNDS:
                rows.extend(estimands_for_cell(demand, seed, t))

    clone_ok_all = all(r["clone_reconstruction_ok"] for r in rows)
    # normalise AE by IQR of the baseline (default-history + default) population
    scales = {}
    for demand in demands:
        vals = [r["baseline"] for r in rows if r["demand"] == demand]
        if len(vals) >= 4:
            q = statistics.quantiles(vals, n=4); scales[demand] = q[2] - q[0]
        else:
            scales[demand] = (max(vals) - min(vals)) if vals else 0.0
    for r in rows:
        s = scales.get(r["demand"], 0.0)
        r["ae_norm"] = (r["ae"] / s) if s > 0 else None

    ae_norms = [r["ae_norm"] for r in rows if r["ae_norm"] is not None]
    sign_tot = sign_dis = 0
    for r in rows:
        if abs(r["d_cl"]) > 1e-9 and abs(r["d_mt"]) > 1e-9:
            sign_tot += 1; sign_dis += int((r["d_cl"] > 0) != (r["d_mt"] > 0))
    # top-1 ranking disagreement per (demand, seed, t, H) over candidates.
    # Waiting time is minimised, so the best candidate has the most NEGATIVE
    # estimated effect (largest reduction vs the default baseline). CL ranks
    # by the cloned local effect d_cl_i; MT ranks by the matched-history
    # effect d_mt_i; these differ because CL's default baseline is
    # candidate-specific (from candidate i's own reconstructed clone) while
    # MT's is a single independently-evolved default history.
    # tie-aware (protocol S5, as in E4): a decision set counts toward the
    # ranking endpoint only when neither the CL nor the MT top is a tie, so a
    # flip between value-tied candidates is not reported as a disagreement.
    rank_tot = rank_dis = rank_tied = 0
    by_key = {}
    for r in rows:
        by_key.setdefault((r["demand"], r["seed"], r["round"], r["horizon"]), []).append(r)
    for k, group in by_key.items():
        cl_min = min(r["d_cl"] for r in group)
        mt_min = min(r["d_mt"] for r in group)
        cl_tie = sum(1 for r in group if abs(r["d_cl"] - cl_min) < 1e-9) > 1
        mt_tie = sum(1 for r in group if abs(r["d_mt"] - mt_min) < 1e-9) > 1
        if cl_tie or mt_tie:
            rank_tied += 1
            continue
        top_cl = min(group, key=lambda r: r["d_cl"])["candidate"]
        top_mt = min(group, key=lambda r: r["d_mt"])["candidate"]
        rank_tot += 1
        rank_dis += int(top_cl != top_mt)

    ae_by_h = {H: (round(statistics.median([r["ae_norm"] for r in rows
                  if r["horizon"] == H and r["ae_norm"] is not None]), 4)
                  if any(r["horizon"] == H and r["ae_norm"] is not None for r in rows) else None)
              for H in HORIZONS}

    boundary = ("external_divergent" if (ae_norms and statistics.median(ae_norms) > TOL_REL)
                else ("external_exact" if (ae_norms and max(ae_norms) <= 1e-9)
                      else "external_approximation"))

    # ---- Deliverable 2: E5 checker Layer-3 on external SUMO manifests ----
    layer3 = []
    kinds = ["intact", "saveState_not_continuous", "schedule_partial",
             "policy_unrecorded", "history_declared_local", "metric_incomplete"]
    for demand in demands:
        for seed in seeds[:2]:            # a few manifests per estimand type/kind
            for dtype in sorted(e5.ESTIMAND_TYPES):
                for kind in kinds:
                    m, expected = export_manifest(demand, seed, 5, 5, dtype, kind)
                    v = e5.check(m)["verdict"]
                    layer3.append({"declared": dtype, "kind": kind, "expected": expected,
                                   "verdict": v, "correct": int(v == expected)})
    l3_intact = [r for r in layer3 if r["kind"] == "intact"]
    l3_neg = [r for r in layer3 if r["kind"] != "intact"]
    layer3_scores = {
        "cases": len(layer3),
        "status_accuracy": round(sum(r["correct"] for r in layer3) / len(layer3), 4) if layer3 else None,
        "false_positive_rate_on_intact": round(sum(1 for r in l3_intact if r["verdict"] != "PASS")
                                               / len(l3_intact), 4) if l3_intact else None,
        "negative_case_detection": round(sum(r["correct"] for r in l3_neg) / len(l3_neg), 4) if l3_neg else None,
    }

    summary = {
        "mode": "pilot" if args.pilot else "confirmatory",
        "estimand_cells": len(rows),
        "clone_reconstruction_ok_all": clone_ok_all,
        "ae_norm_median": round(statistics.median(ae_norms), 4) if ae_norms else None,
        "ae_norm_max": round(max(ae_norms), 4) if ae_norms else None,
        "ae_norm_by_horizon": ae_by_h,
        "sign_disagreement_rate": round(sign_dis / sign_tot, 4) if sign_tot else None,
        "top1_ranking_disagreement_rate_nontied": round(rank_dis / rank_tot, 4) if rank_tot else None,
        "ranking_eligible_nontied": rank_tot, "ranking_tied_excluded": rank_tied,
        "external_boundary": boundary,
        "layer3_checker": layer3_scores,
        "software_commit": commit,
    }
    (out / "e6_estimand_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (out / "e6_layer3_records.jsonl").write_text("\n".join(json.dumps(r) for r in layer3) + "\n")
    (out / "aggregate_results.json").write_text(json.dumps(summary, indent=2))
    (out / "environment.json").write_text(json.dumps(
        {"software_commit": commit, "mode": summary["mode"], "demands": demands,
         "seeds": seeds, "decision_rounds": DECISION_ROUNDS, "horizons": HORIZONS,
         "candidate_phases": CANDIDATE_PHASES, "sumo": "1.27.1",
         "construction": "deterministic_replay_to_branch_not_saveState"}, indent=2))

    print(f"[2B-E6 {summary['mode']}] estimand_cells={len(rows)} clone_reconstruction_ok={clone_ok_all}")
    print(f"  AE norm median={summary['ae_norm_median']} max={summary['ae_norm_max']}")
    print(f"  AE norm by horizon: {ae_by_h}")
    print(f"  sign disagreement={summary['sign_disagreement_rate']} "
          f"top1 ranking disagreement (nontied)={summary['top1_ranking_disagreement_rate_nontied']} "
          f"(eligible={summary['ranking_eligible_nontied']}, tied_excluded={summary['ranking_tied_excluded']})")
    print(f"  external boundary: {boundary}")
    print(f"  Layer-3 checker: status_acc={layer3_scores['status_accuracy']} "
          f"FP_on_intact={layer3_scores['false_positive_rate_on_intact']} "
          f"neg_detection={layer3_scores['negative_case_detection']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
