# Paper 2B-E4 — conclusion-impact study

Protocol: `docs/protocols/p2b_e4_conclusion_impact.md` v1.0 (SHA-256 prefix
`d33a5d7cde2aee7e`). Script:
`experiments/paper2b/e4_conclusion_impact.py`. Regression tests:
`tests/unit/test_p2b_e4_conclusion.py` (4 tests). Pilot under `pilot/`,
confirmatory under `confirmatory/`.

## What E4 answers — the last link in the chain

E0 showed the estimand mismatch is mathematically possible; E2 that it
exists in full domains and grows in magnitude with the horizon; E3 which
structures produce it. E4 asks whether it changes a model-relative
**decision** --- the top-ranked intervention, the ranking, a classification
--- not just a number.

## Design

Each decision set: a shared pre-decision checkpoint, K=4 valid candidate
interventions (decision-slot policy varied, other slots default), one
objective (a metric oriented by its catalog direction), one horizon. The
**CL ranking** clones the same checkpoint for every candidate (the correct
decision-local comparison); the **MT ranking** evaluates each candidate on
its own separately-evolved standing-policy history (the flawed "separate
runs" comparison, whose divergence comes entirely from the per-candidate
pre-decision states). Primary endpoint: top-1 disagreement over **eligible**
decision sets (objectives with a single dominant candidate are degenerate
and excluded — the dominant-candidate caution). Confirmatory: 2 domains × 2
scenarios × 30 seeds × 2 rounds × H∈{1,3,5} × 6 objectives × 4 candidates =
**4320 decision sets (2880 eligible)**.

## Result: the mismatch rarely changes the decision, and carries real regret when it does

| Measure | Value |
|---|---|
| PRIMARY top-1 disagreement (eligible) | **1.18%** (pooled incl. degenerate 0.79%) |
| Pairwise inversion rate (eligible) | 0.55% |
| Mean Kendall τ (eligible) | 0.989 |
| energy_market_v1 (eligible 1440) | **0%** top-1, τ = 1.0 (structural anchor) |
| epidemic_policy_v1 (eligible 1440) | 2.36% top-1, 1.1% inversion |
| epidemic top-1 by horizon | **H1 7.08% / H3 0% / H5 0%** |
| CL-regret when top-1 flips | 27 cases, all nonzero, median 5262 infections |

### The three findings

1. **The mismatch is magnitude-large but decision-stable.** Despite the
   substantial normalised attribution error E2/E3 report, the top-1 decision
   flips in only ~1% of eligible decision sets and the mean Kendall τ is
   0.99. This is the "biased but conclusion-stable" regime (E3's approximate
   region) being common — a result that *bounds* the practical danger of MT
   rather than overstating it.
2. **Effect-magnitude divergence and decision-ranking instability need not
   move together (observed), with an explanatory hypothesis the design does
   not identify.** Although attribution-error *magnitude* increased with the
   horizon in E2, top-1 disagreement here was concentrated at H=1 (7.1%) and
   disappeared at H=3/H=5 (0%) in the evaluated intervention sets — so
   magnitude divergence and decision-ranking instability moved in opposite
   directions across the horizon. A *plausible explanation* is that
   longer-horizon candidate effects became sufficiently separated to
   preserve their ordering, but E4's design does not independently identify
   that mechanism (it did not compute or freeze the CL candidate-separation
   margin, the MT perturbation relative to the top-1/top-2 gap, or ranking
   stability as a function of effect margin).
3. **When a flip happens, it is not a near-tie artefact.** All 27
   confirmatory flips carry nonzero **CL-evaluated, model-relative regret**
   among the 27 disagreement cases (median 5262 infections) — a
   model-relative quantity, not a calibrated real-world health loss.
4. **The structurally exact domain has zero decision impact.** Every energy
   decision set has τ = 1.0 and 0% top-1 disagreement, as the E2/E3
   state-independence predicts (a regression test locks τ = 1 for all energy
   objectives).

## Files

- `confirmatory/e4_rows.jsonl` — one record per decision set: CL/MT top
  choice, full orderings, Kendall τ, top-1 disagreement, CL-regret.
- `confirmatory/aggregate_results.json` — eligible/pooled top-1 rate,
  pairwise inversion, per-domain and per-horizon breakdown, degenerate
  objectives, regret.
- `pilot/` — the 360-set plumbing run; never pooled into the confirmatory
  result.

## Claim boundary

Supports: MT and CL supported different **model-relative** intervention
rankings in ~1% of eligible decision sets, concentrated at short horizons,
with nonzero CL-regret when the top choice flipped, and zero impact in the
structurally exact domain. Does not establish: that MT causes the wrong
**real-world** policy (the objectives are model-relative and uncalibrated),
nor the prevalence of decision flips in any model beyond the two evaluated
domains.
