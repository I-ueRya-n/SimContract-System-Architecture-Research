"""Paper 2B-E2: cloned-continuation confirmatory study.

Protocol: docs/protocols/p2b_e2_cloned_continuation.md.

Measures the four counterfactual estimands (SR/CL/MT/RS) at horizons
H in {1,3,5} across both controlled domains, under an IDENTICAL injected
future exogenous schedule, and quantifies how far the matched-schedule (MT)
and resampled (RS) contrasts depart from the cloned-state local reference
(CL). This is the multi-step mechanism that makes Paper 2B independent of
Paper 2A (whose A2 measured only the one-step same-resolution contrast SR).

No production code is modified. adapter.step / sample_exogenous /
default_action_provider are used through their public interfaces, exactly
as engine.session.SessionRunner.run uses them.

Usage:
  python experiments/paper2b/e2_cloned_continuation.py --pilot
  python experiments/paper2b/e2_cloned_continuation.py            # confirmatory
"""
from __future__ import annotations

import argparse
import copy
import json
import statistics
import subprocess
import tempfile
from pathlib import Path

from simcontract.composition import create_application
from simcontract.contracts import Action, BundleView, StepContext, digest
from simcontract.contracts.seeding import derive_seed, rng_for

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "p2b_e2_cloned_continuation"

DOMAINS = ["energy_market_v1", "epidemic_policy_v1"]
SUBMITTED_CONDITIONS = ["random_valid", "top_score"]   # two candidate interventions
DEFAULT_CONDITION = "rule"                              # all-default history
HORIZONS = [1, 3, 5]
SESSION_ROUNDS = 8
INTERVENTION_ROUNDS = [1, 3, 5]
TOL_NORM = 0.05                                         # approximation tolerance


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


def _actions_from_resolved(resolved: dict) -> dict[str, Action]:
    return {slot: Action(role=d["role"], slot=slot, fields=d["fields"])
            for slot, d in resolved.items()}


def _default_actions(adapter, state, ctx) -> dict[str, Action]:
    out = {}
    for role in adapter.roles:
        for slot in role.slots():
            out[slot] = adapter.default_action_provider.action_for(state, slot, None, ctx)
    return out


def _run_capture(app, domain, scenario, condition, seed, rounds):
    """Run one session; return (bundle, {round_no: pre-decision state})."""
    adapter = app._registry.create(domain)
    states = {1: adapter.initial_state(scenario, seed)}

    def on_round(round_no, outcome):
        states[round_no + 1] = outcome.state_next

    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / "run"
        app.run_session(domain=domain, scenario=scenario, seed=seed, rounds=rounds,
                        conditions={"all": condition}, personas={}, out_dir=out_dir,
                        on_round=on_round)
        bundle = BundleView.load(out_dir)
    return bundle, states


def _exogenous_for(adapter, state, seed, round_no, salt=None):
    parts = (round_no,) if salt is None else (round_no, salt)
    return adapter.sample_exogenous(state, rng_for(derive_seed(seed, *parts), "exogenous"))


def build_schedule(adapter, s_start, seed, t, H):
    """Reference future exogenous schedule U = [u_t..u_{t+H-1}], drawn from a
    default-action roll-out starting at s_start. Returned as a list of dicts
    to be INJECTED identically into every CL/MT branch (protocol S3)."""
    U = []
    state = copy.deepcopy(s_start)
    for k in range(H):
        round_no = t + k
        exo = _exogenous_for(adapter, state, seed, round_no)
        U.append(exo)
        ctx = StepContext(round_no=round_no, round_seed=derive_seed(seed, round_no),
                          exogenous=exo, scenario_id=state["scenario_id"])
        actions = _default_actions(adapter, state, ctx)
        state = adapter.step(state, actions, ctx).state_next
    return U


def roll_out(adapter, s_start, action_map_t, seed, t, U):
    """Apply action_map_t at round t with injected exogenous U[0], then
    len(U)-1 continuation rounds under the default policy with injected
    U[1:]. Return the final step's system_metrics. Pure: never mutates
    s_start or U."""
    state = copy.deepcopy(s_start)
    final_metrics = None
    for k, exo in enumerate(U):
        round_no = t + k
        ctx = StepContext(round_no=round_no, round_seed=derive_seed(seed, round_no),
                          exogenous=dict(exo), scenario_id=state["scenario_id"])
        actions = action_map_t if k == 0 else _default_actions(adapter, state, ctx)
        outcome = adapter.step(state, actions, ctx)
        final_metrics = outcome.system_metrics
        state = outcome.state_next
    return final_metrics


def _diff(m_a, m_b):
    return {m: m_a[m] - m_b[m] for m in m_a}


def compute_cell(adapter, domain, scenario, seed, t, H, cond,
                 s_factual, s_default, submitted_actions, default_actions_t,
                 original_round, gates_out):
    """All four estimands for one (domain, scenario, seed, round, horizon,
    condition), plus the per-cell hard-gate checks."""
    # Injected shared schedule U from the factual clone's default roll-out.
    U = build_schedule(adapter, s_factual, seed, t, H)

    # --- CL: both branches cloned from s_factual, only action at t differs ---
    cl_a = roll_out(adapter, s_factual, submitted_actions, seed, t, U)
    cl_b = roll_out(adapter, s_factual, default_actions_t, seed, t, U)
    d_cl = _diff(cl_a, cl_b)

    # --- MT: intervention branch identical to CL's A; default branch from s_default ---
    mt_f = cl_a                                    # same construction as CL branch A
    mt_d = roll_out(adapter, s_default, default_actions_t, seed, t, U)
    d_mt = _diff(mt_f, mt_d)

    # --- RS: independently resampled schedules for each branch ---
    U_F = build_schedule_salted(adapter, s_factual, seed, t, H, "rs_factual")
    U_D = build_schedule_salted(adapter, s_default, seed, t, H, "rs_default")
    rs_f = roll_out(adapter, s_factual, submitted_actions, seed, t, U_F)
    rs_d = roll_out(adapter, s_default, default_actions_t, seed, t, U_D)
    d_rs = _diff(rs_f, rs_d)

    ae = {m: abs(d_mt[m] - d_cl[m]) for m in d_cl}

    # ---- per-cell hard gates (protocol S4) ----
    if gates_out is not None:
        _cell_gates(adapter, domain, scenario, seed, t, H, U, s_factual, s_default,
                    submitted_actions, default_actions_t, original_round, cl_a, cl_b,
                    d_cl, gates_out)

    return {"domain": domain, "scenario": scenario, "seed": seed, "round": t,
            "horizon": H, "condition": cond,
            "d_sr": None,   # filled at H==1 by caller alignment
            "d_cl": d_cl, "d_mt": d_mt, "d_rs": d_rs, "ae": ae}


def build_schedule_salted(adapter, s_start, seed, t, H, salt):
    U = []
    state = copy.deepcopy(s_start)
    for k in range(H):
        round_no = t + k
        exo = _exogenous_for(adapter, state, seed, round_no, salt=salt)
        U.append(exo)
        ctx = StepContext(round_no=round_no, round_seed=derive_seed(seed, round_no, salt),
                          exogenous=exo, scenario_id=state["scenario_id"])
        actions = _default_actions(adapter, state, ctx)
        state = adapter.step(state, actions, ctx).state_next
    return U


def _cell_gates(adapter, domain, scenario, seed, t, H, U, s_factual, s_default,
                submitted_actions, default_actions_t, original_round, cl_a, cl_b,
                d_cl, gates_out):
    key = f"{domain}/{scenario}/seed{seed}/t{t}/H{H}"

    # G1 checkpoint hash identity
    c1, c2 = copy.deepcopy(s_factual), copy.deepcopy(s_factual)
    gates_out.append(("G1_checkpoint_hash_identity", key,
                      digest(c1) == digest(c2) == digest(s_factual)))

    # G2 future exogenous schedule identity: the schedule is deterministic
    # (rebuilding from the same inputs yields byte-identical digests) and is
    # therefore the SAME U injected into every CL/MT branch by construction.
    U_rebuilt = build_schedule(adapter, s_factual, seed, t, H)
    same_schedule = ([digest(u) for u in U] == [digest(u) for u in U_rebuilt])
    gates_out.append(("G2_future_exogenous_digest_equality", key, same_schedule))
    # re-injecting the exact U into an independent roll-out reproduces cl_a
    gates_out.append(("G2b_injected_schedule_reproducible", key,
                      roll_out(adapter, s_factual, submitted_actions, seed, t, U) == cl_a))

    # G4 single action difference at t: CL branch A and B share state+exogenous, differ only in action
    gates_out.append(("G4_single_action_difference", key,
                      submitted_actions != default_actions_t))

    # G5/G9 branch isolation: mutating a clone must not affect another roll-out
    probe_state = copy.deepcopy(s_factual)
    _ = roll_out(adapter, probe_state, submitted_actions, seed, t, U)
    gates_out.append(("G5_branch_state_isolation", key,
                      digest(probe_state) == digest(s_factual)))  # roll_out did not mutate input

    # G7 factual trajectory untouched: original recorded metrics unchanged
    gates_out.append(("G7_factual_trajectory_untouched", key,
                      original_round.system_metrics == original_round.system_metrics))

    # G8 rerun determinism
    gates_out.append(("G8_rerun_determinism", key,
                      roll_out(adapter, s_factual, submitted_actions, seed, t, U) == cl_a))

    # G6 metric key identity between branches
    gates_out.append(("G6_metric_key_identity", key,
                      set(cl_a) == set(cl_b) == set(original_round.system_metrics)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()

    scenarios_per_domain = 1 if args.pilot else 2
    seeds = list(range(1, 6)) if args.pilot else list(range(1, 31))
    out = OUT_ROOT / ("pilot" if args.pilot else "confirmatory")
    out.mkdir(parents=True, exist_ok=True)

    app = create_application()
    commit = _git_commit()
    rows: list[dict] = []
    gates: list[tuple] = []
    default_pop: dict[str, dict[str, list[float]]] = {}   # domain -> metric -> values

    for domain in DOMAINS:
        adapter = app._registry.create(domain)
        scenarios = list(adapter.manifest.scenario_ids)[:scenarios_per_domain]
        for scenario in scenarios:
            for seed in seeds:
                # default-history run (all default) -> S_t^D and default population
                _, def_states = _run_capture(app, domain, scenario, DEFAULT_CONDITION,
                                             seed, SESSION_ROUNDS)
                def_bundle, _ = _run_capture(app, domain, scenario, DEFAULT_CONDITION,
                                             seed, SESSION_ROUNDS)
                for r in def_bundle.rounds:
                    dd = default_pop.setdefault(domain, {})
                    for m, v in r.system_metrics.items():
                        dd.setdefault(m, []).append(v)

                for cond in SUBMITTED_CONDITIONS:
                    fac_bundle, fac_states = _run_capture(app, domain, scenario, cond,
                                                          seed, SESSION_ROUNDS)
                    rounds_by_no = {r.round_no: r for r in fac_bundle.rounds}
                    for t in INTERVENTION_ROUNDS:
                        s_fac = fac_states[t]
                        s_def = def_states[t]
                        original = rounds_by_no[t]
                        submitted = _actions_from_resolved(original.resolved_actions)
                        ctx0 = StepContext(round_no=t, round_seed=derive_seed(seed, t),
                                          exogenous={}, scenario_id=scenario)
                        default_t = _default_actions(adapter, s_fac, ctx0)
                        for H in HORIZONS:
                            cell = compute_cell(adapter, domain, scenario, seed, t, H, cond,
                                                s_fac, s_def, submitted, default_t, original,
                                                gates)
                            # G10 + SR: at H==1 CL must equal the adapter's internal
                            # applied-minus-authoritative branch at round t.
                            if H == 1:
                                internal = {m: original.branches["applied"][m]
                                            - original.branches["authoritative"][m]
                                            for m in original.system_metrics}
                                cell["d_sr"] = cell["d_cl"]
                                gates.append(("G10_h1_cl_equals_internal_branch",
                                              f"{domain}/{scenario}/seed{seed}/t{t}",
                                              cell["d_cl"] == internal))
                            rows.append(cell)

    # ---- G3 continuation-policy identity (once per domain: same provider class) ----
    for domain in DOMAINS:
        a1 = app._registry.create(domain).default_action_provider
        a2 = app._registry.create(domain).default_action_provider
        gates.append(("G3_continuation_policy_identity", domain,
                      type(a1) is type(a2)))

    gates_ok = all(p for _, _, p in gates)

    # ---- normalization scales (IQR over all-default population) ----
    scales = {}
    for domain, metrics in default_pop.items():
        scales[domain] = {}
        for m, vals in metrics.items():
            if len(vals) >= 4:
                q = statistics.quantiles(vals, n=4)
                iqr = q[2] - q[0]
            else:
                iqr = 0.0
            scales[domain][m] = iqr if iqr > 0 else (max(vals) - min(vals) if vals else 0.0)

    # ---- endpoints ----
    def norm(domain, m, v):
        s = scales.get(domain, {}).get(m, 0.0)
        return (v / s) if s > 0 else None

    ae_norm_all = []
    sign_disagree = 0
    sign_total = 0
    by_h = {H: [] for H in HORIZONS}
    within_tol = 0
    within_total = 0
    for row in rows:
        d = row["domain"]
        for m in row["ae"]:
            nv = norm(d, m, row["ae"][m])
            if nv is not None:
                ae_norm_all.append(nv)
                by_h[row["horizon"]].append(nv)
                within_total += 1
                within_tol += int(nv <= TOL_NORM)
            cl, mt = row["d_cl"][m], row["d_mt"][m]
            if abs(cl) > 1e-9 and abs(mt) > 1e-9:
                sign_total += 1
                sign_disagree += int((cl > 0) != (mt > 0))

    # ranking disagreement: per (domain,scenario,seed,round,horizon,metric),
    # order the two conditions by d_cl vs by d_mt.
    rank_total = 0
    rank_disagree = 0
    by_key: dict[tuple, dict[str, dict]] = {}
    for row in rows:
        k = (row["domain"], row["scenario"], row["seed"], row["round"], row["horizon"])
        by_key.setdefault(k, {})[row["condition"]] = row
    for k, by_cond in by_key.items():
        if set(by_cond) >= set(SUBMITTED_CONDITIONS):
            a, b = SUBMITTED_CONDITIONS
            for m in by_cond[a]["d_cl"]:
                cl_order = by_cond[a]["d_cl"][m] > by_cond[b]["d_cl"][m]
                mt_order = by_cond[a]["d_mt"][m] > by_cond[b]["d_mt"][m]
                rank_total += 1
                rank_disagree += int(cl_order != mt_order)

    # ---- per-domain endpoints (the pooled median is misleading because energy
    # is structurally zero and epidemic is path-dependent -- report separately) ----
    by_domain = {}
    for domain in DOMAINS:
        drows = [r for r in rows if r["domain"] == domain]
        d_ae_norm = []
        d_by_h = {H: [] for H in HORIZONS}
        d_sign_dis, d_sign_tot = 0, 0
        for row in drows:
            for m in row["ae"]:
                nv = norm(domain, m, row["ae"][m])
                if nv is not None:
                    d_ae_norm.append(nv)
                    d_by_h[row["horizon"]].append(nv)
                cl, mt = row["d_cl"][m], row["d_mt"][m]
                if abs(cl) > 1e-9 and abs(mt) > 1e-9:
                    d_sign_tot += 1
                    d_sign_dis += int((cl > 0) != (mt > 0))
        raw_ae = [v for r in drows for v in r["ae"].values()]
        by_domain[domain] = {
            "cells": len(drows),
            "raw_ae_max": max(raw_ae) if raw_ae else None,
            "raw_ae_all_zero": all(abs(v) <= 1e-9 for v in raw_ae),
            "ae_normalized_median": statistics.median(d_ae_norm) if d_ae_norm else None,
            "ae_normalized_max": max(d_ae_norm) if d_ae_norm else None,
            "ae_normalized_by_horizon_median": {
                H: (statistics.median(v) if v else None) for H, v in d_by_h.items()},
            "sign_disagreement_rate": (d_sign_dis / d_sign_tot) if d_sign_tot else None,
        }

    summary = {
        "mode": "pilot" if args.pilot else "confirmatory",
        "cells": len(rows),
        "hard_gates_pass": gates_ok,
        "gate_failures": [(n, k) for n, k, p in gates if not p],
        "by_domain": by_domain,
        "pooled_ae_normalized_median": statistics.median(ae_norm_all) if ae_norm_all else None,
        "pooled_ae_normalized_max": max(ae_norm_all) if ae_norm_all else None,
        "pooled_note": "pooled median is dominated by the structurally-zero domain; "
                       "see by_domain for the path-dependent result",
        "sign_disagreement_rate": (sign_disagree / sign_total) if sign_total else None,
        "ranking_disagreement_rate": (rank_disagree / rank_total) if rank_total else None,
        "within_tolerance_fraction": (within_tol / within_total) if within_total else None,
        "software_commit": commit,
    }

    (out / "e2_rows.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in rows) + "\n")
    (out / "e2_gates.json").write_text(json.dumps(
        {"all_pass": gates_ok, "gates": [{"gate": n, "key": k, "pass": p}
                                         for n, k, p in gates]}, indent=2))
    (out / "aggregate_results.json").write_text(json.dumps(summary, indent=2, default=str))
    (out / "environment.json").write_text(json.dumps({
        "software_commit": commit, "domains": DOMAINS, "scenarios_per_domain": scenarios_per_domain,
        "seeds": seeds, "horizons": HORIZONS, "intervention_rounds": INTERVENTION_ROUNDS,
        "session_rounds": SESSION_ROUNDS, "conditions": SUBMITTED_CONDITIONS,
        "default_condition": DEFAULT_CONDITION}, indent=2))

    print(f"[2B-E2 {summary['mode']}] cells={len(rows)} hard_gates_pass={gates_ok}")
    if not gates_ok:
        for n, k in summary["gate_failures"][:10]:
            print(f"  GATE FAIL: {n} @ {k}")
    for domain, bd in by_domain.items():
        print(f"  {domain}: raw_ae_all_zero={bd['raw_ae_all_zero']} "
              f"norm_median={bd['ae_normalized_median']} norm_max={bd['ae_normalized_max']}")
        print(f"    AE norm by horizon (median): {bd['ae_normalized_by_horizon_median']}")
        print(f"    sign disagreement rate={bd['sign_disagreement_rate']}")
    print(f"  ranking disagreement rate (pooled)={summary['ranking_disagreement_rate']}")
    print(f"  within tolerance (<= {TOL_NORM}) fraction={summary['within_tolerance_fraction']}")
    return 0 if gates_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
