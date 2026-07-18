"""Paper 2B-E3: structural boundary study.

Protocol: docs/protocols/p2b_e3_structural_boundary.md.

Question: under which structural conditions is a matched-exogenous
trajectory (MT) an EXACT, a useful APPROXIMATE, or a MISLEADING substitute
for a cloned-state local continuation (CL)? E3 maps the boundary; it does
NOT claim MT always fails. The two real domains anchor two corners with real
E2 evidence (energy = exact regime, state-independent outcome; epidemic =
divergent regime, path-dependent); E3 varies the structure continuously in a
parameterized generalisation of the 2B-E0 micro-model to fill in the map.

Model (extends E0 x_{t+1}=rho*x_t+load+u with structural factors):

    x_{t+1} = phi_feedback( rho*x_t + phi*tanh(x_t) + load_t + sigma*u_t )
    outcome  = benefit_decision - w_x * x_final           (delayed cost)

where the irreversibility factor phi_feedback is one of:
  reversible : identity
  ratchet    : max(x_t, .)   -- partially irreversible accumulation
  lockin     : threshold-triggered near-total persistence (increasing returns)

Structural factors (grounded in the E3 literature gate -- see protocol S2):
  persistence rho, feedback phi, irreversibility, delayed-cost w_x,
  volatility sigma, intervention timing t, intervention magnitude, horizon H.

The SR/CL/MT/RS estimands and the injected-shared-schedule discipline are
identical to 2B-E2; here they run on the parameterized model so every factor
can be varied.

Usage:
  python experiments/paper2b/e3_structural_boundary.py --pilot
  python experiments/paper2b/e3_structural_boundary.py            # confirmatory
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "p2b_e3_structural_boundary"

HORIZONS = [1, 3, 5]
TOL_NORM = 0.05                       # 2B-E2 IQR tolerance (secondary, reported)
TOL_REL = 0.10                        # E3 preregistered relative tolerance:
                                      # |MT-CL| within 10% of the local effect |CL|
EPS_ABS = 1e-6
X0 = 1.0
LOCKIN_THRESHOLD = 5.0

# Two-level factor settings for the fractional-factorial screening design.
LEVELS = {
    "rho":        {"lo": 0.2, "hi": 0.9},
    "phi":        {"lo": 0.0, "hi": 0.6},
    "irrev":      {"lo": "reversible", "hi": "lockin"},
    "w_x":        {"lo": 0.0, "hi": 1.0},
    "sigma":      {"lo": 0.3, "hi": 1.5},
    "timing":     {"lo": 2, "hi": 5},        # early vs late decision round (>=2 so history diverges)
    "magnitude":  {"lo": "small", "hi": "large"},
}
FACTORS = list(LEVELS)                        # order fixed for the design generators

# Intervention actions (benefit, load), scaled by magnitude.
DEFAULT_ACTION = (0.0, 0.0)
CANDIDATES = {  # (benefit, load) before magnitude scaling
    "aggressive": (3.0, 3.0),
    "efficient": (2.0, 1.0),
}
MAG_SCALE = {"small": 0.5, "large": 1.0}


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


@dataclass(frozen=True)
class Structure:
    rho: float
    phi: float
    irrev: str
    w_x: float
    sigma: float
    timing: int
    magnitude: str


def _apply_irrev(x_prev, raw, irrev):
    if irrev == "reversible":
        return raw
    if irrev == "ratchet":
        return max(x_prev, raw)
    if irrev == "lockin":
        # increasing-returns lock-in: above threshold, persistence -> ~1
        if x_prev >= LOCKIN_THRESHOLD:
            return x_prev + raw - x_prev * 0.0 + (raw - x_prev)  # near-full carry
        return raw
    raise ValueError(irrev)


def step(x, load, u, s: Structure):
    raw = s.rho * x + s.phi * math.tanh(x) + load + s.sigma * u
    return _apply_irrev(x, raw, s.irrev)


def outcome(benefit, x_final, w_x):
    return benefit - w_x * x_final


def _exog_schedule(seed, t, H, sigma, salt=""):
    """Deterministic shared exogenous schedule U = [u_t..u_{t+H-1}]."""
    rng = random.Random(hashlib.sha256(f"{seed}|{t}|{salt}".encode()).hexdigest())
    return [sigma * rng.gauss(0.0, 1.0) for _ in range(H)]


def _pre_state(seed, s: Structure, load_history):
    """Evolve from x0 through the (timing-1) pre-decision rounds applying
    load_history each round; returns the pre-decision state S_t."""
    x = X0
    U = _exog_schedule(seed, 0, s.timing - 1, s.sigma, salt="history") if s.timing > 1 else []
    for k in range(s.timing - 1):
        x = step(x, load_history, U[k], s)
    return x


def roll_out(x_start, action, s: Structure, U):
    """Apply `action` (benefit,load) at the decision round with U[0], then
    len(U)-1 default continuation rounds with U[1:]. Return final outcome."""
    benefit, load = action
    x = x_start
    for k, u in enumerate(U):
        ld = load if k == 0 else DEFAULT_ACTION[1]
        x = step(x, ld, u, s)
    return outcome(benefit, x, s.w_x)


def estimands(seed, s: Structure, cand_name, H):
    mag = MAG_SCALE[s.magnitude]
    b, ld = CANDIDATES[cand_name]
    intervention = (b * mag, ld * mag)
    default = DEFAULT_ACTION

    # factual history applies the intervention load; default history applies default.
    s_fac = _pre_state(seed, s, load_history=intervention[1])
    s_def = _pre_state(seed, s, load_history=default[1])

    U = _exog_schedule(seed, s.timing, H, s.sigma)          # injected shared schedule
    # CL: both branches from the factual clone.
    cl = roll_out(s_fac, intervention, s, U) - roll_out(s_fac, default, s, U)
    # MT: intervention from factual state, default from default-history state.
    mt = roll_out(s_fac, intervention, s, U) - roll_out(s_def, default, s, U)
    # RS: independently resampled schedules per branch.
    U_f = _exog_schedule(seed, s.timing, H, s.sigma, salt="rs_f")
    U_d = _exog_schedule(seed, s.timing, H, s.sigma, salt="rs_d")
    rs = roll_out(s_fac, intervention, s, U_f) - roll_out(s_def, default, s, U_d)

    return {"cl": cl, "mt": mt, "rs": rs, "ae": abs(mt - cl),
            "state_distance": abs(s_fac - s_def)}


def relative_error(cl, mt):
    """|MT - CL| relative to the local effect being estimated. The E3
    boundary-map classifier (preregistered tolerance TOL_REL)."""
    return abs(mt - cl) / (abs(cl) + EPS_ABS)


def classify(cl, mt, ae_raw):
    """exact: MT reproduces CL; divergent: sign flip or relative error over
    the preregistered tolerance; approximate: biased but conclusion-stable."""
    if ae_raw <= EPS_ABS:                     # MT == CL exactly (e.g. no delayed cost)
        return "exact"
    if abs(cl) > 1e-9 and abs(mt) > 1e-9 and (cl > 0) != (mt > 0):
        return "divergent"                    # sign reversal
    if relative_error(cl, mt) > TOL_REL:
        return "divergent"                    # magnitude beyond tolerance
    return "approximate"


def fractional_factorial(resolution_fraction=2):
    """2^(7-2) resolution-IV fractional factorial on the 7 structural factors
    (32 cells). +-1 coding; generators F = A*B*C, G = A*D*E (documented in
    the protocol). Returns a list of {factor: 'lo'/'hi'}."""
    import itertools
    A, B, C, D, E = FACTORS[0], FACTORS[1], FACTORS[2], FACTORS[3], FACTORS[4]
    F, G = FACTORS[5], FACTORS[6]
    cells = []
    for combo in itertools.product([-1, 1], repeat=5):
        a, b, c, d, e = combo
        f = a * b * c            # generator F = ABC
        g = a * d * e            # generator G = ADE
        signs = {A: a, B: b, C: c, D: d, E: e, F: f, G: g}
        cells.append({fac: ("hi" if signs[fac] == 1 else "lo") for fac in FACTORS})
    return cells


def pilot_cells():
    """~16 hand-picked corner/edge configs: all-lo, all-hi, and each single
    factor toggled hi from the all-lo baseline (screening the main effects)."""
    base = {f: "lo" for f in FACTORS}
    cells = [dict(base), {f: "hi" for f in FACTORS}]
    for f in FACTORS:
        c = dict(base); c[f] = "hi"; cells.append(c)
    # two mixed corners exercising key interactions
    cells.append({**base, "rho": "hi", "w_x": "hi", "timing": "hi"})           # persistence+delay+late
    cells.append({**base, "irrev": "hi", "phi": "hi", "sigma": "hi"})          # lockin+feedback+volatile
    return cells


def _structure_from(cell) -> Structure:
    return Structure(rho=LEVELS["rho"][cell["rho"]], phi=LEVELS["phi"][cell["phi"]],
                     irrev=LEVELS["irrev"][cell["irrev"]], w_x=LEVELS["w_x"][cell["w_x"]],
                     sigma=LEVELS["sigma"][cell["sigma"]], timing=LEVELS["timing"][cell["timing"]],
                     magnitude=LEVELS["magnitude"][cell["magnitude"]])


def run(cells, seeds, mode, out: Path):
    rows = []
    # normalization scale per structural cell: IQR of the all-default outcome
    # population (aggressive candidate excluded) over seeds and horizons.
    for ci, cell in enumerate(cells):
        s = _structure_from(cell)
        # default population for normalization: outcomes of the default action
        default_pop = []
        for seed in seeds:
            for H in HORIZONS:
                U = _exog_schedule(seed, s.timing, H, s.sigma)
                s_def = _pre_state(seed, s, load_history=DEFAULT_ACTION[1])
                default_pop.append(roll_out(s_def, DEFAULT_ACTION, s, U))
        if len(default_pop) >= 4:
            q = statistics.quantiles(default_pop, n=4)
            scale = q[2] - q[0]
        else:
            scale = 0.0
        if scale <= 0:
            scale = (max(default_pop) - min(default_pop)) if default_pop else 0.0

        for seed in seeds:
            for cand in CANDIDATES:
                for H in HORIZONS:
                    e = estimands(seed, s, cand, H)
                    ae_norm = (e["ae"] / scale) if scale > 0 else None
                    rows.append({
                        "cell": ci, "factors": cell, "seed": seed, "candidate": cand,
                        "horizon": H, "rho": s.rho, "phi": s.phi, "irrev": s.irrev,
                        "w_x": s.w_x, "sigma": s.sigma, "timing": s.timing,
                        "magnitude": s.magnitude,
                        "cl": e["cl"], "mt": e["mt"], "rs": e["rs"], "ae": e["ae"],
                        "ae_norm": ae_norm, "ae_rel": relative_error(e["cl"], e["mt"]),
                        "state_distance": e["state_distance"],
                        "regime": classify(e["cl"], e["mt"], e["ae"])})
    return rows


def summarize(rows):
    from collections import Counter
    regimes = Counter(r["regime"] for r in rows)
    # regime prevalence by factor level (boundary map)
    def _boundary_over(subset):
        b = {}
        for factor in FACTORS:
            b[factor] = {}
            for lvl in ("lo", "hi"):
                sub = [r for r in subset if r["factors"][factor] == lvl]
                c = Counter(r["regime"] for r in sub)
                n = len(sub) or 1
                b[factor][lvl] = {k: round(c.get(k, 0) / n, 3)
                                  for k in ("exact", "approximate", "divergent")}
        return b

    boundary = _boundary_over(rows)
    # Conditional map among cells where divergence is possible (delayed cost
    # present). The marginal map is gated by w_x -- with w_x=lo every cell is
    # exact, diluting the other factors' main effects -- so the interaction
    # structure only shows up conditional on w_x=hi.
    boundary_wx_hi = _boundary_over([r for r in rows if r["factors"]["w_x"] == "hi"])
    # absolute |MT-CL| median by horizon among non-exact cells (where MT
    # actually differs) -- shows the divergence MAGNITUDE growing with the
    # horizon, consistent with 2B-E2 (relative error is used only to classify,
    # not to trend, since its denominator |CL| also grows with the horizon).
    by_h = {}
    for H in HORIZONS:
        sub = [r for r in rows if r["horizon"] == H and r["regime"] != "exact"]
        by_h[H] = round(statistics.median(r["ae"] for r in sub), 4) if sub else None
    # sign / ranking disagreement
    sign_tot = sign_dis = 0
    for r in rows:
        if abs(r["cl"]) > 1e-9 and abs(r["mt"]) > 1e-9:
            sign_tot += 1
            sign_dis += int((r["cl"] > 0) != (r["mt"] > 0))
    rank_tot = rank_dis = 0
    by_key = {}
    for r in rows:
        k = (r["cell"], r["seed"], r["horizon"])
        by_key.setdefault(k, {})[r["candidate"]] = r
    for k, by_cand in by_key.items():
        if set(by_cand) >= set(CANDIDATES):
            cl_ord = by_cand["aggressive"]["cl"] > by_cand["efficient"]["cl"]
            mt_ord = by_cand["aggressive"]["mt"] > by_cand["efficient"]["mt"]
            rank_tot += 1
            rank_dis += int(cl_ord != mt_ord)
    return {
        "cells": len({r["cell"] for r in rows}), "records": len(rows),
        "regime_prevalence": {k: round(regimes.get(k, 0) / len(rows), 3)
                              for k in ("exact", "approximate", "divergent")},
        "abs_ae_median_by_horizon_nonexact": by_h,
        "sign_disagreement_rate": round(sign_dis / sign_tot, 4) if sign_tot else None,
        "ranking_disagreement_rate": round(rank_dis / rank_tot, 4) if rank_tot else None,
        "boundary_map_regime_share_by_factor_level": boundary,
        "boundary_map_conditional_on_delayed_cost": boundary_wx_hi,
        "tolerance_sensitivity": _tolerance_sensitivity(rows),
    }


def _tolerance_sensitivity(rows):
    """Regime prevalence under the preregistered tolerance and two neighbours
    (protocol S6): confirms the exact/approximate/divergent split is not an
    artefact of the specific 0.10 threshold."""
    from collections import Counter
    out = {}
    for tol in (0.05, 0.10, 0.20):
        c = Counter()
        for r in rows:
            if r["ae"] <= EPS_ABS:
                c["exact"] += 1
            elif abs(r["cl"]) > 1e-9 and abs(r["mt"]) > 1e-9 and (r["cl"] > 0) != (r["mt"] > 0):
                c["divergent"] += 1
            elif r["ae_rel"] > tol:
                c["divergent"] += 1
            else:
                c["approximate"] += 1
        n = len(rows)
        out[tol] = {k: round(c.get(k, 0) / n, 3) for k in ("exact", "approximate", "divergent")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--seeds", type=int, default=None)
    args = ap.parse_args()

    if args.pilot:
        cells = pilot_cells()
        seeds = list(range(1, (args.seeds or 15) + 1))
        out = OUT_ROOT / "pilot"
    else:
        cells = fractional_factorial()
        seeds = list(range(1, (args.seeds or 40) + 1))
        out = OUT_ROOT / "confirmatory"
    out.mkdir(parents=True, exist_ok=True)

    rows = run(cells, seeds, "pilot" if args.pilot else "confirmatory", out)
    summ = summarize(rows)
    summ["mode"] = "pilot" if args.pilot else "confirmatory"
    summ["seeds"] = len(seeds)
    summ["design"] = "corner_screening" if args.pilot else "2^(7-2)_resolution_IV_frac_factorial"
    summ["software_commit"] = _git_commit()

    (out / "e3_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (out / "aggregate_results.json").write_text(json.dumps(summ, indent=2))
    (out / "environment.json").write_text(json.dumps({
        "software_commit": summ["software_commit"], "mode": summ["mode"],
        "cells": summ["cells"], "seeds": len(seeds), "horizons": HORIZONS,
        "factors": FACTORS, "levels": LEVELS, "tolerance": TOL_NORM,
        "design": summ["design"]}, indent=2))

    print(f"[2B-E3 {summ['mode']}] cells={summ['cells']} records={summ['records']} "
          f"seeds={len(seeds)}")
    print(f"  regime prevalence: {summ['regime_prevalence']}")
    print(f"  abs |MT-CL| median by horizon (non-exact): {summ['abs_ae_median_by_horizon_nonexact']}")
    print(f"  sign disagreement={summ['sign_disagreement_rate']} "
          f"ranking disagreement={summ['ranking_disagreement_rate']}")
    print("  boundary map (divergent share by factor level | marginal / conditional on w_x=hi):")
    cond = summ["boundary_map_conditional_on_delayed_cost"]
    for f, lv in summ["boundary_map_regime_share_by_factor_level"].items():
        cl_, ch_ = cond[f]["lo"]["divergent"], cond[f]["hi"]["divergent"]
        print(f"    {f:10s} marginal lo={lv['lo']['divergent']:.2f} hi={lv['hi']['divergent']:.2f}"
              f"   | w_x=hi lo={cl_:.2f} hi={ch_:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
