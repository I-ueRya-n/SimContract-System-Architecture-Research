"""Paper 2B-E4: conclusion-impact study.

Protocol: docs/protocols/p2b_e4_conclusion_impact.md.

Question (the last link in the chain): does the SR/CL/MT/RS estimand
mismatch change a model-relative *decision* -- the top-ranked intervention,
the intervention ranking, a threshold classification -- not just a number?
E0 showed the difference is mathematically possible; E2 that it exists in
full domains and grows with the horizon; E3 which structures produce it;
E4 asks whether it alters conclusions.

Decision set: one shared pre-decision checkpoint, K>=3 valid candidate
interventions with fixed IDs, one objective (a metric oriented by its
catalog direction), one horizon, one shared injected exogenous schedule,
one continuation policy. The CL ranking clones the SAME checkpoint for every
candidate (the correct decision-local comparison); the MT ranking evaluates
each candidate on its OWN separately-evolved standing-policy history (the
flawed "separate runs" comparison). Primary endpoint: top-1 disagreement
between argmax_CL and argmax_MT.

No production code is modified; the E2 roll-out/schedule machinery is
reused through its public functions.

Usage:
  python experiments/paper2b/e4_conclusion_impact.py --pilot
  python experiments/paper2b/e4_conclusion_impact.py            # confirmatory
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from simcontract.composition import create_application
from simcontract.contracts import Action, BundleView, StepContext, digest
from simcontract.contracts.seeding import derive_seed, rng_for

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "p2b_e4_conclusion_impact"

# reuse E2's roll-out and schedule construction
_E2 = importlib.util.spec_from_file_location(
    "e2_cloned", Path(__file__).parent / "e2_cloned_continuation.py")
e2 = importlib.util.module_from_spec(_E2)
sys.modules["e2_cloned"] = e2
_E2.loader.exec_module(e2)

DOMAINS = ["energy_market_v1", "epidemic_policy_v1"]
DECISION_SLOT = {"energy_market_v1": "regulator_1",
                 "epidemic_policy_v1": "health_authority_1"}
HORIZONS = [1, 3, 5]
SESSION_ROUNDS = 8
DECISION_ROUNDS = [3, 5]
K_CANDIDATES = 4
TIE_EPS = 1e-9


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


def _default_map(adapter, state, ctx):
    return e2._default_actions(adapter, state, ctx)


def _candidate_maps(adapter, state, seed, t, domain):
    """K candidate action-maps: the decision slot varies over K sampled valid
    actions; all other slots stay at the domain default. Deterministic given
    (seed, t)."""
    slot = DECISION_SLOT[domain]
    role = next(r.role for r in adapter.roles if slot in r.slots())
    ctx = StepContext(round_no=t, round_seed=derive_seed(seed, t),
                      exogenous={}, scenario_id=state["scenario_id"])
    base = _default_map(adapter, state, ctx)
    rng = rng_for(derive_seed(seed, t, "e4cands"))
    cands = adapter.action_space(state, slot, rng, K_CANDIDATES)
    maps = []
    for i, a in enumerate(cands[:K_CANDIDATES]):
        m = dict(base)
        m[slot] = a
        maps.append((f"cand{i}", m))
    return maps


def _history_state(adapter, scenario, seed, t, action_map_or_default):
    """Pre-decision state at round t after applying the given policy at every
    round 1..t-1. `action_map_or_default` is either a callable(state,ctx)->map
    (default policy) or a fixed action-map (standing candidate policy)."""
    state = adapter.initial_state(scenario, seed)
    for r in range(1, t):
        round_seed = derive_seed(seed, r)
        exo = adapter.sample_exogenous(state, rng_for(round_seed, "exogenous"))
        ctx = StepContext(round_no=r, round_seed=round_seed, exogenous=exo,
                          scenario_id=scenario)
        if callable(action_map_or_default):
            amap = action_map_or_default(state, ctx)
        else:
            # fixed standing policy: re-key the decision-slot action to this round
            amap = {s: a for s, a in action_map_or_default.items()}
        state = adapter.step(state, amap, ctx).state_next
    return state


def _oriented(value, direction):
    return value if direction == "max" else -value


def kendall_tau(order_a, order_b):
    """Kendall tau over two orderings given as lists of candidate ids."""
    ids = list(order_a)
    rank_a = {c: i for i, c in enumerate(order_a)}
    rank_b = {c: i for i, c in enumerate(order_b)}
    n = len(ids)
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = ids[i], ids[j]
            s = (rank_a[ci] - rank_a[cj]) * (rank_b[ci] - rank_b[cj])
            if s > 0:
                conc += 1
            elif s < 0:
                disc += 1
    denom = n * (n - 1) / 2
    return (conc - disc) / denom if denom else 1.0


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
    rows = []

    for domain in DOMAINS:
        adapter = app._registry.create(domain)
        _, _, catalog, _ = app._assets_for(domain)
        directions = {k: catalog.direction(k) for k in sorted(catalog.keys)}  # sorted: deterministic row order
        scenarios = list(adapter.manifest.scenario_ids)[:scenarios_per_domain]
        for scenario in scenarios:
            for seed in seeds:
                for t in DECISION_ROUNDS:
                    # shared decision checkpoint: the default-history state at t
                    s_shared = _history_state(adapter, scenario, seed, t,
                                              lambda st, cx: _default_map(adapter, st, cx))
                    cand_maps = _candidate_maps(adapter, s_shared, seed, t, domain)
                    # per-candidate standing-policy history state (for MT)
                    hist_states = {cid: _history_state(adapter, scenario, seed, t, amap)
                                   for cid, amap in cand_maps}
                    for H in HORIZONS:
                        U = e2.build_schedule(adapter, s_shared, seed, t, H)
                        cl_metrics, mt_metrics = {}, {}
                        for cid, amap in cand_maps:
                            cl_metrics[cid] = e2.roll_out(adapter, s_shared, amap, seed, t, U)
                            mt_metrics[cid] = e2.roll_out(adapter, hist_states[cid], amap, seed, t, U)
                        for m, dirn in directions.items():
                            cl_val = {cid: _oriented(cl_metrics[cid][m], dirn) for cid, _ in cand_maps}
                            mt_val = {cid: _oriented(mt_metrics[cid][m], dirn) for cid, _ in cand_maps}
                            order_cl = sorted(cl_val, key=lambda c: cl_val[c], reverse=True)
                            order_mt = sorted(mt_val, key=lambda c: mt_val[c], reverse=True)
                            top_cl, top_mt = order_cl[0], order_mt[0]
                            # regret: CL-value lost by picking MT's choice (oriented, so
                            # higher is better; regret >= 0).
                            regret = cl_val[top_cl] - cl_val[top_mt]
                            rows.append({
                                "domain": domain, "scenario": scenario, "seed": seed,
                                "round": t, "horizon": H, "objective": m,
                                "top1_disagree": int(top_cl != top_mt),
                                "kendall_tau": round(kendall_tau(order_cl, order_mt), 6),
                                "regret_cl_value": regret,
                                "top_cl": top_cl, "top_mt": top_mt,
                                "order_cl": order_cl, "order_mt": order_mt})

    # ---- degeneracy: an objective is degenerate for a domain if a single
    # candidate is the CL-top in every decision set (no contest -- excluded
    # from the primary top-1 endpoint, per the dominant-candidate caution). ----
    from collections import Counter
    degenerate = {}
    for d in DOMAINS:
        for m in {r["objective"] for r in rows if r["domain"] == d}:
            tops = {r["top_cl"] for r in rows if r["domain"] == d and r["objective"] == m}
            degenerate[(d, m)] = (len(tops) == 1)

    def _pairwise_inversion(r):
        # discordant-pair fraction between the CL and MT orderings = (1 - tau)/2
        return (1.0 - r["kendall_tau"]) / 2.0

    n = len(rows)
    eligible = [r for r in rows if not degenerate[(r["domain"], r["objective"])]]
    by_domain = {}
    for d in DOMAINS:
        dr = [r for r in rows if r["domain"] == d]
        de = [r for r in eligible if r["domain"] == d]
        by_domain[d] = {
            "decision_sets": len(dr),
            "eligible_decision_sets": len(de),
            "degenerate_objectives": sorted(m for (dd, m), v in degenerate.items() if dd == d and v),
            "top1_disagreement_rate_pooled": round(sum(r["top1_disagree"] for r in dr) / len(dr), 4) if dr else None,
            "top1_disagreement_rate_eligible": round(sum(r["top1_disagree"] for r in de) / len(de), 4) if de else None,
            "pairwise_inversion_rate_eligible": round(statistics.fmean(_pairwise_inversion(r) for r in de), 4) if de else None,
            "mean_kendall_tau_eligible": round(statistics.fmean(r["kendall_tau"] for r in de), 4) if de else None,
            "top1_disagreement_eligible_by_horizon": {
                H: round(sum(r["top1_disagree"] for r in de if r["horizon"] == H)
                         / max(1, len([r for r in de if r["horizon"] == H])), 4)
                for H in HORIZONS},
        }
    regret_when_disagree = [r["regret_cl_value"] for r in rows if r["top1_disagree"]]
    summary = {
        "mode": "pilot" if args.pilot else "confirmatory",
        "decision_sets": n,
        "eligible_decision_sets": len(eligible),
        "candidates_per_set": K_CANDIDATES,
        "PRIMARY_top1_disagreement_rate_eligible": round(sum(r["top1_disagree"] for r in eligible) / len(eligible), 4) if eligible else None,
        "top1_disagreement_rate_pooled": round(sum(r["top1_disagree"] for r in rows) / n, 4) if n else None,
        "pairwise_inversion_rate_eligible": round(statistics.fmean(_pairwise_inversion(r) for r in eligible), 4) if eligible else None,
        "mean_kendall_tau_eligible": round(statistics.fmean(r["kendall_tau"] for r in eligible), 4) if eligible else None,
        "by_domain": by_domain,
        "nonzero_regret_when_disagree_count": sum(1 for x in regret_when_disagree if abs(x) > TIE_EPS),
        "median_regret_when_disagree": round(statistics.median(regret_when_disagree), 6) if regret_when_disagree else None,
        "software_commit": commit,
    }

    (out / "e4_rows.jsonl").write_text("\n".join(json.dumps(r, default=str) for r in rows) + "\n")
    (out / "aggregate_results.json").write_text(json.dumps(summary, indent=2, default=str))
    (out / "environment.json").write_text(json.dumps({
        "software_commit": commit, "domains": DOMAINS, "decision_slot": DECISION_SLOT,
        "scenarios_per_domain": scenarios_per_domain, "seeds": seeds,
        "horizons": HORIZONS, "decision_rounds": DECISION_ROUNDS,
        "candidates_per_set": K_CANDIDATES, "session_rounds": SESSION_ROUNDS}, indent=2))

    print(f"[2B-E4 {summary['mode']}] decision_sets={n} eligible={len(eligible)} "
          f"candidates={K_CANDIDATES}")
    print(f"  PRIMARY top-1 disagreement (eligible): {summary['PRIMARY_top1_disagreement_rate_eligible']}"
          f"  (pooled incl. degenerate: {summary['top1_disagreement_rate_pooled']})")
    print(f"  pairwise inversion rate (eligible): {summary['pairwise_inversion_rate_eligible']}"
          f"  mean Kendall tau: {summary['mean_kendall_tau_eligible']}")
    for d, bd in by_domain.items():
        print(f"  {d}: eligible={bd['eligible_decision_sets']} "
              f"top1={bd['top1_disagreement_rate_eligible']} "
              f"inversion={bd['pairwise_inversion_rate_eligible']} "
              f"by_H={bd['top1_disagreement_eligible_by_horizon']}")
        print(f"    degenerate objectives (excluded): {bd['degenerate_objectives']}")
    print(f"  nonzero CL-regret when top-1 disagrees: {summary['nonzero_regret_when_disagree_count']} "
          f"(median {summary['median_regret_when_disagree']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
