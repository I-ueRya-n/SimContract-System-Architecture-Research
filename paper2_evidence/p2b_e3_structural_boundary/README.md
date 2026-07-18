# Paper 2B-E3 — structural boundary study

Protocol: `docs/protocols/p2b_e3_structural_boundary.md` v1.0 (SHA-256
prefix `91368cbb25041e17`). Script:
`experiments/paper2b/e3_structural_boundary.py`. Regression tests:
`tests/unit/test_p2b_e3_structural.py` (6 tests). Pilot under `pilot/`,
confirmatory under `confirmatory/`.

## What E3 answers

Under which structural conditions is a matched-exogenous trajectory (MT) an
**exact**, an **approximate**, or a **misleading** substitute for a
cloned-state local continuation (CL)? E3 produces the boundary map. It does
not claim MT always fails: the two real domains anchor two corners with
executed 2B-E2 evidence (`energy_market_v1` exact; `epidemic_policy_v1`
divergent), and E3 fills the interior by varying structure in a
parameterized generalisation of the 2B-E0 micro-model.

## Design

A 2^(7-2) resolution-IV fractional factorial (32 structural cells;
generators `timing = rho*phi*irrev`, `magnitude = rho*w_x*sigma`) over seven
factors (persistence, feedback, irreversibility, delayed cost, volatility,
timing, magnitude), with horizon `H in {1,3,5}` and two candidate
interventions crossed fully within every cell, over 40 paired seeds =
**7680 records**. Not a full 2^7 Cartesian product, per Kleijnen 2015 /
Sanchez et al. 2020. The literature gate (7 web-verified sources) grounds
the factor definitions and the design choice (protocol §2).

## Result: a well-separated three-regime boundary map

Regime prevalence: **exact 50%, approximate 15%, divergent 35%** — all three
regimes located in factor space (the success criterion; a model where MT
never or always diverged would be a failure to separate them). Sign
disagreement 11.7%, ranking disagreement 1.2% (the strongest divergence
form; rare, as expected).

### The boundary (headline)

1. **Delayed cost is the master gate.** With `w_x = 0` (no delayed
   consequence) every cell is exact (0% divergent), regardless of all other
   factors — the E0/E2 structural fact. With `w_x` high, 70% of cells
   diverge. This gating is why the *marginal* effects of the other factors
   look flat: half the design (w_x=lo) is uniformly exact and dilutes them.
2. **Given delayed cost, persistence is the dominant driver.** Conditional
   on `w_x` high, divergent share rises from **43% at low persistence to 97%
   at high persistence**. Feedback (66→74%), late timing (68→72%), and
   magnitude (67→73%) add modest divergence; volatility (72→68%) and
   lock-in irreversibility (74→66%) slightly *reduce* it (noise masks the
   systematic bias; ceilings saturate it — the bounded-feedback nuance the
   pilot flagged).

This maps to the three regimes the roadmap called for:

```text
no delayed cost, or memoryless, or early intervention   -> exact
delayed cost + low persistence                          -> approximate (biased, stable)
delayed cost + high persistence (+ feedback/late/large) -> divergent (sign/ranking/magnitude)
```

### Robustness

The exact/approximate/divergent split is robust to the tolerance: at
`TOL_REL in {0.05, 0.10, 0.20}` the exact share is constant at 50%
(tolerance-independent, the w_x=0 structural anchor) and the
approximate/divergent boundary moves smoothly (12.4/37.6 → 15/35 → 18.1/31.9),
with no cliff — the split is not an artefact of the preregistered 0.10
threshold (protocol §6).

## Files

- `confirmatory/e3_rows.jsonl` — one record per (cell, seed, candidate,
  horizon): CL, MT, RS, AE, relative error, state-distance, regime.
- `confirmatory/aggregate_results.json` — regime prevalence, marginal and
  w_x-conditional boundary maps, tolerance sensitivity, sign/ranking rates.
- `confirmatory/environment.json` — software commit, factors, levels, design.
- `pilot/` — the 11-cell corner-screening plumbing run (990 records); never
  pooled into the confirmatory result.

## Claim boundary

Supports: a structural boundary map locating where MT is exact, an
acceptable approximation, or misleading, as a function of persistence,
feedback, irreversibility, delayed cost, volatility, timing, and magnitude,
in a parameterized micro-model with two real-domain corners anchored by
2B-E2. Does not establish: the prevalence of each regime in any specific
real model beyond the anchors, whether the divergences change a scientific
decision (that is 2B-E4), or any behavioural validity.
