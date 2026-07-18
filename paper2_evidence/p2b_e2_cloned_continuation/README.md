# Paper 2B-E2 — cloned-continuation confirmatory study

Protocol: `docs/protocols/p2b_e2_cloned_continuation.md` v1.0. Script:
`experiments/paper2b/e2_cloned_continuation.py`. Regression tests:
`tests/unit/test_p2b_e2_estimands.py` (4 tests). Pilot output under
`pilot/`; confirmatory under `confirmatory/`. The pilot's implementation-only
corrections (a G2-gate tautology; per-domain reporting) are recorded in
protocol §9 and do not change the confirmatory design.

## What E2 adds beyond Paper 2A

Paper 2A's A2 measured only the **one-step** same-resolution contrast (SR).
E2 measures the **multi-step** cloned-state local reference (CL) and how far
the matched-schedule (MT) and resampled (RS) contrasts depart from it, at
horizons `H in {1,3,5}`, under an **identical injected future exogenous
schedule**. This is the mechanism that makes Paper 2B independent of Paper 2A.

## Result (confirmatory: 2160 cells, all hard gates pass)

2 domains x 2 scenarios x 30 seeds x 3 intervention rounds x `H in {1,3,5}`
x 2 submitted conditions. All ten hard gates (G1–G10) pass on every cell,
including G10: at `H=1` the cloned CL estimand equals the adapter's own
applied-minus-authoritative branch exactly — the generalisation of the
feasibility probe's `-880.77` cross-check to the whole matrix.

| Domain | raw AE | norm. median | norm. max | AE by horizon (median) | sign disagree |
|---|---|---:|---:|---|---:|
| `energy_market_v1` | **all zero** | 0.000 | 0.000 | H1 0.000 / H3 0.000 / H5 0.000 | 0.0% |
| `epidemic_policy_v1` | up to 36 355 | 0.238 | 4.472 | **H1 0.175 / H3 0.257 / H5 0.295** | 11.1% |

Pooled ranking-disagreement rate 9.9%; within-tolerance (normalised
`AE <= 0.05`) fraction 71.5% — so ~28% of cells exceed the pre-registered
approximation tolerance, concentrated entirely in the path-dependent domain.

### The two findings

1. **Energy is structurally zero.** All 1080 energy cells have `AE = 0`
   exactly: its clearing function does not read carried state, so cloned and
   matched-schedule default branches coincide (a regression test locks this
   as `cl_b == mt_d`). This is E0's R1 equivalence regime and A2's exact-zero
   result, now confirmed multi-step.
2. **Epidemic's departure grows with the horizon.** Normalised `AE` medians
   rise monotonically `0.175 -> 0.257 -> 0.295` across `H = 1,3,5`, with
   11% sign disagreements and 10% ranking disagreements between the cloned
   reference and the matched-schedule contrast. A2 (one-step) could not show
   this growth; it is the core new empirical content of Paper 2B's E2.

## Files

- `confirmatory/e2_rows.jsonl` — one record per cell: `d_sr`, `d_cl`,
  `d_mt`, `d_rs`, and `ae` per metric.
- `confirmatory/e2_gates.json` — every hard-gate check (all pass).
- `confirmatory/aggregate_results.json` — per-domain and per-horizon
  endpoints, sign/ranking disagreement, within-tolerance fraction.
- `confirmatory/environment.json` — software commit and full matrix config.
- `pilot/` — the plumbing run (180 cells); never pooled into the
  confirmatory result.

## Hard gates (protocol §4)

G1 checkpoint hash identity; G2 future-exogenous schedule identity (real
determinism check after the pilot fix); G3 continuation-policy identity; G4
single-action difference at `t`; G5 branch-state isolation; G6
simulator/metric identity; G7 factual trajectory untouched; G8 rerun
determinism; G9 no cross-branch state read; G10 `H=1` CL equals SR and the
adapter's internal branch. All pass on all 2160 cells.

## Claim boundary

Supports: a real-domain, multi-step measurement showing the matched-schedule
contrast departs from the cloned-state local reference, that the departure
is exactly zero where the outcome is state-independent and grows with the
horizon where it is path-dependent, all under gate-verified checkpoint /
schedule / policy / isolation identity. Does not establish: how often each
regime occurs across the full structural space (2B-E3), whether the
departures change a scientific decision (2B-E4), or any behavioural validity
of the domains.
