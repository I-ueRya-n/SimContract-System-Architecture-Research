"""Paper 2B-E0: minimal hand-computable counterexample.

Protocol: docs/protocols/p2b_e0_micro_counterexample.md.

Purpose. Lift Paper 2B's core claim from "a phenomenon observed inside a
complex simulator" to a closed-form, hand-verifiable fact: even when the
exogenous input schedule is *identical*, if two compared branches begin
from different pre-intervention endogenous states, a matched-schedule
historical contrast (MT) can estimate a different quantity than a
cloned-state continuation (CL) -- differing in magnitude, in sign, or in
the ranking of interventions.

The model (one persistent endogenous state, one delayed consequence):

    state transition:   x_{t+1} = rho * x_t + load_t + u_t
    action:             a decision with two fields (benefit b, load l)
    outcome (delayed):  Y = b_decision - w_x * x_final

`rho` is state persistence; `load` is the action's accumulating footprint;
`u_t` is the shared exogenous shock; `w_x` weights the delayed state cost.
The delayed consequence is that a decision's `load` raises the state at the
outcome horizon and is therefore penalised through -w_x * x_final, while its
`benefit` is collected immediately -- an immediate-benefit / delayed-cost
trade-off.

Rounds (H = horizon after the decision): round 1 is pre-decision (it is
where the submitted history and the default history diverge), round 2 is
the decision, rounds 3..(2+H-1) are continuation under the default policy,
and the outcome is read at x_{2+H}.

Closed forms (default d has b_d, l_d; candidate i has b_i, l_i; the shared
exogenous schedule cancels in every difference, which is the whole point):

    Delta_SR_i        = (b_i-b_d) - w_x            * (l_i-l_d)     # one-step, H=1
    Delta_CL_{i,H}    = (b_i-b_d) - w_x*rho^{H-1}  * (l_i-l_d)     # cloned continuation
    Delta_MT_{i,H}    = (b_i-b_d) - w_x*(rho^H+rho^{H-1}) * (l_i-l_d)  # matched-history
    AE_MT_{i,H}       = | Delta_MT - Delta_CL | = w_x * rho^H * |l_i-l_d|

AE is exactly zero iff rho=0 (memoryless), w_x=0 (no delayed cost), or
l_i=l_d (no historical divergence). This script simulates the model
round-by-round AND evaluates the closed forms, and asserts they are equal
to floating tolerance -- the code is the machine-checkable proof of the
hand computation, not a separate approximation of it.

Usage: python experiments/paper2b/e0_micro_counterexample.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper2_evidence" / "p2b_e0_micro_counterexample"
TOL = 1e-9


@dataclass(frozen=True)
class Action:
    benefit: float
    load: float


DEFAULT = Action(benefit=0.0, load=0.0)


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


# ---------------------------------------------------------------------------
# Explicit round-by-round simulator (the "executable implementation").
# ---------------------------------------------------------------------------
def _step(x: float, load: float, u: float, rho: float) -> float:
    return rho * x + load + u


def _simulate(x0: float, loads: list[float], us: list[float], rho: float) -> list[float]:
    """Return the state trajectory [x0, x_after_round1, x_after_round2, ...]."""
    xs = [x0]
    x = x0
    for load, u in zip(loads, us):
        x = _step(x, load, u, rho)
        xs.append(x)
    return xs


def _outcome(b_decision: float, x_final: float, w_x: float) -> float:
    return b_decision - w_x * x_final


def _exog(H: int) -> list[float]:
    """A fixed, shared exogenous schedule over 1 history + 1 decision + (H-1)
    continuation rounds. Deterministic and identical across every branch:
    'same noise'. Values are arbitrary and non-zero to prove they cancel."""
    base = [0.3, -0.7, 0.5, -0.2, 0.9, 0.1, -0.4]
    return base[: 1 + H]


def simulate_estimands(rho: float, w_x: float, x0: float, cand: Action,
                       H: int, default: Action = DEFAULT) -> dict:
    """Compute SR, CL_H, MT_H for one candidate vs the default, by explicit
    simulation. Continuation policy is the default action."""
    us = _exog(H)
    u_hist, u_dec, u_cont = us[0], us[1], us[2:]           # len(u_cont) == H-1

    # Pre-decision states: factual history (candidate's own load) vs default history.
    x2_F = _simulate(x0, [cand.load], [u_hist], rho)[-1]
    x2_D = _simulate(x0, [default.load], [u_hist], rho)[-1]

    def continue_from(x2: float, decision_load: float) -> float:
        loads = [decision_load] + [default.load] * (H - 1)
        return _simulate(x2, loads, [u_dec] + u_cont, rho)[-1]

    # SR (one-step, H=1): both branches cloned from the factual pre-state.
    x3_sr_a = continue_from_onestep(x2_F, cand.load, u_dec, rho)
    x3_sr_b = continue_from_onestep(x2_F, default.load, u_dec, rho)
    d_sr = _outcome(cand.benefit, x3_sr_a, w_x) - _outcome(default.benefit, x3_sr_b, w_x)

    # CL (cloned continuation, horizon H): both branches from the same factual clone.
    xf_cl_a = continue_from(x2_F, cand.load)
    xf_cl_b = continue_from(x2_F, default.load)
    d_cl = _outcome(cand.benefit, xf_cl_a, w_x) - _outcome(default.benefit, xf_cl_b, w_x)

    # MT (matched-schedule historical contrast, horizon H): branches begin from
    # DIFFERENT pre-decision states (factual history vs default history).
    xf_mt_f = continue_from(x2_F, cand.load)
    xf_mt_d = continue_from(x2_D, default.load)
    d_mt = _outcome(cand.benefit, xf_mt_f, w_x) - _outcome(default.benefit, xf_mt_d, w_x)

    return {"SR": d_sr, "CL": d_cl, "MT": d_mt,
            "AE": abs(d_mt - d_cl),
            "x2_F": x2_F, "x2_D": x2_D}


def continue_from_onestep(x2: float, decision_load: float, u_dec: float, rho: float) -> float:
    return _step(x2, decision_load, u_dec, rho)


# ---------------------------------------------------------------------------
# Closed forms (the "hand computation").
# ---------------------------------------------------------------------------
def closed_form(rho: float, w_x: float, cand: Action, H: int,
                default: Action = DEFAULT) -> dict:
    db = cand.benefit - default.benefit
    dl = cand.load - default.load
    d_sr = db - w_x * dl
    d_cl = db - w_x * (rho ** (H - 1)) * dl
    d_mt = db - w_x * (rho ** H + rho ** (H - 1)) * dl
    return {"SR": d_sr, "CL": d_cl, "MT": d_mt, "AE": w_x * (rho ** H) * abs(dl)}


# ---------------------------------------------------------------------------
# Canonical regime parameterisations (hand-calculated in the protocol).
# ---------------------------------------------------------------------------
CAND_AGGRESSIVE = Action(benefit=3.0, load=3.0)   # high benefit, high delayed load
CAND_EFFICIENT = Action(benefit=2.0, load=1.0)    # lower benefit, low delayed load

REGIMES = {
    "R1_equivalence": {"rho": 0.0, "w_x": 0.5, "H": 2, "cands": [CAND_AGGRESSIVE]},
    "R2_magnitude_error": {"rho": 0.5, "w_x": 0.5, "H": 2, "cands": [CAND_AGGRESSIVE]},
    "R3_sign_reversal": {"rho": 0.9, "w_x": 1.0, "H": 2, "cands": [CAND_AGGRESSIVE]},
    "R4_ranking_reversal": {"rho": 0.8, "w_x": 0.5, "H": 2,
                            "cands": [CAND_AGGRESSIVE, CAND_EFFICIENT]},
}


def classify(sr: float, cl: float, mt: float, tol: float = 1e-6) -> str:
    """Regime of a single candidate's CL-vs-MT relationship."""
    if abs(mt - cl) <= tol:
        return "equivalence"
    if cl * mt < -tol * tol and (cl > tol or cl < -tol):
        # opposite signs (and CL non-negligible)
        if (cl > 0) != (mt > 0):
            return "sign_reversal"
    return "magnitude_error"


def _hash_obj(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    all_consistent = True
    fixtures = []

    for name, cfg in REGIMES.items():
        rho, w_x, H = cfg["rho"], cfg["w_x"], cfg["H"]
        cand_results = []
        for idx, cand in enumerate(cfg["cands"]):
            sim = simulate_estimands(rho, w_x, x0=1.0, cand=cand, H=H)
            cf = closed_form(rho, w_x, cand, H)
            consistent = all(abs(sim[k] - cf[k]) <= TOL for k in ("SR", "CL", "MT", "AE"))
            all_consistent = all_consistent and consistent
            cand_results.append({
                "candidate": {"benefit": cand.benefit, "load": cand.load},
                "H": H, "rho": rho, "w_x": w_x,
                "simulated": {k: round(sim[k], 10) for k in ("SR", "CL", "MT", "AE")},
                "closed_form": {k: round(cf[k], 10) for k in ("SR", "CL", "MT", "AE")},
                "sim_matches_closed_form": consistent,
                "regime": classify(sim["SR"], sim["CL"], sim["MT"]),
            })
            fixtures.append({"regime": name, "candidate_index": idx,
                             "rho": rho, "w_x": w_x, "H": H,
                             "benefit": cand.benefit, "load": cand.load,
                             "expected": {k: round(cf[k], 10) for k in ("SR", "CL", "MT", "AE")}})

        entry = {"config": {"rho": rho, "w_x": w_x, "H": H}, "candidates": cand_results}

        # Ranking check for the multi-candidate regime.
        if len(cand_results) >= 2:
            cl_rank = sorted(range(len(cand_results)),
                             key=lambda j: cand_results[j]["simulated"]["CL"], reverse=True)
            mt_rank = sorted(range(len(cand_results)),
                             key=lambda j: cand_results[j]["simulated"]["MT"], reverse=True)
            entry["cl_ranking"] = cl_rank
            entry["mt_ranking"] = mt_rank
            entry["ranking_reversal"] = cl_rank != mt_rank
        results[name] = entry

    # Regime demonstration checks (the four required regimes must each appear).
    demonstrated = {
        "R1_equivalence": results["R1_equivalence"]["candidates"][0]["regime"] == "equivalence",
        "R2_magnitude_error": results["R2_magnitude_error"]["candidates"][0]["regime"] == "magnitude_error",
        "R3_sign_reversal": results["R3_sign_reversal"]["candidates"][0]["regime"] == "sign_reversal",
        "R4_ranking_reversal": results["R4_ranking_reversal"].get("ranking_reversal", False),
    }
    all_regimes_ok = all(demonstrated.values())

    # Exhaustive sweep: classify AE and sign behaviour across a grid, to show
    # the regimes are a structural family, not four cherry-picked points.
    sweep = []
    for rho in [round(0.1 * k, 1) for k in range(0, 10)]:
        for w_x in [0.25, 0.5, 1.0, 1.5]:
            cf = closed_form(rho, w_x, CAND_AGGRESSIVE, H=2)
            sweep.append({"rho": rho, "w_x": w_x,
                          "CL": round(cf["CL"], 6), "MT": round(cf["MT"], 6),
                          "AE": round(cf["AE"], 6),
                          "sign_reversal": (cf["CL"] > 0) != (cf["MT"] > 0) and abs(cf["CL"]) > 1e-9})

    payload = {
        "results": results,
        "regimes_demonstrated": demonstrated,
        "all_four_regimes_demonstrated": all_regimes_ok,
        "simulation_matches_closed_form_everywhere": all_consistent,
        "sweep": sweep,
        "software_commit": _git_commit(),
    }
    (OUT / "e0_results.json").write_text(json.dumps(payload, indent=2))
    fixtures_payload = {"fixtures": fixtures}
    (OUT / "e0_fixtures.json").write_text(json.dumps(fixtures_payload, indent=2))
    fixtures_hash = _hash_obj(fixtures_payload)
    (OUT / "e0_fixtures.sha256").write_text(fixtures_hash + "  e0_fixtures.json\n")

    ok = all_consistent and all_regimes_ok
    print(f"[2B-E0] {'ALL CHECKS PASS' if ok else 'CHECK FAILURE'}")
    print(f"  simulation == closed form everywhere: {all_consistent}")
    for name, entry in results.items():
        c0 = entry["candidates"][0]
        line = (f"  {name}: rho={c0['rho']} w_x={c0['w_x']} "
                f"CL={c0['simulated']['CL']:+.4f} MT={c0['simulated']['MT']:+.4f} "
                f"AE={c0['simulated']['AE']:.4f} regime={c0['regime']}")
        if "ranking_reversal" in entry:
            line += f" | CL_rank={entry['cl_ranking']} MT_rank={entry['mt_ranking']} reversal={entry['ranking_reversal']}"
        print(line)
    print(f"  four required regimes demonstrated: {demonstrated}")
    print(f"  fixtures hash: {fixtures_hash[:16]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
