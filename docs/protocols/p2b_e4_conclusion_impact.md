# Paper 2B-E4 — Conclusion-Impact Study

**Protocol version:** 1.0 (frozen 2026-07-18; pilot findings §9 are
implementation/reporting only and do not change the confirmatory design)
**Experiment type:** Decision-impact comparison of CL vs MT rankings over
candidate interventions.
**Primary paper:** Paper 2B. **Implementation:**
`experiments/paper2b/e4_conclusion_impact.py`.
**Depends on:** E0 (difference possible), E2 (difference exists, grows with
horizon), E3 (structural conditions). E4 asks the last question: does the
mismatch change a model-relative *decision*?

## 1. Question

Does the SR/CL/MT/RS estimand mismatch make a researcher, within the same
model, choose a different top-ranked intervention, a different intervention
ranking, or a different threshold classification --- not merely report a
different number? The claim boundary is model-relative: the domains have no
real-world calibration, so E4 speaks only to whether MT and CL support
different \emph{model-relative} conclusions, never to real-world policy
correctness.

## 2. Literature gate (narrow; done before this freeze)

Five sources web-verified 2026-07-18, each grounding a specific endpoint:

| Source | Grounds |
|---|---|
| Saaty 1987 (Decision Sci. 18(2), doi 10.1111/j.1540-5915.1987.tb01514.x) | rank reversal / top-1 disagreement |
| Kendall 1938 (Biometrika 30:81-93, doi 10.1093/biomet/30.1-2.81) | Kendall-$\tau$ ranking-distance endpoint |
| Kim \& Nelson 2006 (Handbooks OR\&MS 13:501-534) | selecting the best simulated system |
| Nelson \& Matejcik 1995 (Mgmt Sci 41(12):1935-1945, doi 10.1287/mnsc.41.12.1935) | CRN applied to selection -- the tightest CRN-to-decision link |
| Bell 1982 (Oper. Res. 30(5):961-981, doi 10.1287/opre.30.5.961) | regret theory -> CL-evaluated selection regret |

## 3. Decision set

One decision set is: a shared pre-decision checkpoint `S_t` (the
default-history state at round `t` --- the state the decision is actually made
from), `K=4` valid candidate interventions with fixed IDs (the decision slot
--- `regulator_1` for energy, `health_authority_1` for epidemic --- varied over
`K` actions sampled deterministically from the adapter's `action_space`, all
other slots at default), one objective (a metric oriented by its catalog
direction, higher-is-better after orientation), one horizon `H\in\{1,3,5\}`,
one shared injected exogenous schedule, and the default continuation policy.

## 4. Two rankings compared

```text
CL ranking : clone the SHARED checkpoint S_t, apply each candidate at t,
             continue H rounds under default -> value_CL(i). The correct
             decision-local ranking (all candidates from one clone).
MT ranking : evaluate each candidate on its OWN separately-evolved
             standing-policy history state S_t^{hist_i} (candidate i applied
             every pre-decision round), same injected schedule -> value_MT(i).
             The flawed "separate runs" ranking.
```

`argmax_CL` vs `argmax_MT` is the primary comparison; the divergence comes
entirely from the per-candidate diverged pre-decision states, not from
randomness (the schedule is injected identically).

## 5. Objective and tie semantics

Each metric is oriented by its catalog direction (`max`: value; `min`:
$-$value), so higher oriented value is always better. Candidates are ranked
by oriented value. Metrics are continuous, so exact ties are near-impossible
and are broken deterministically by candidate index; a top-1 disagreement
therefore always reflects a genuine ordering difference, and its practical
weight is read from the regret endpoint (a flip between near-tied candidates
has near-zero regret).

## 6. Degeneracy (eligibility)

An objective is **degenerate for a domain** if a single candidate is the
CL-top in every decision set --- there is no decision to make, so it is
**excluded from the primary top-1 endpoint** (dominant-candidate caution).
Degenerate objectives are reported separately, not hidden. The primary
endpoint's denominator is eligible decision sets (non-degenerate objectives).

## 7. Endpoints

**Primary:** top-1 disagreement rate over eligible decision sets =
$\#\{\arg\max_{MT}\neq\arg\max_{CL}\}/\#\text{eligible}$.

**Secondary:** pairwise inversion rate (discordant-pair fraction
$=(1-\tau)/2$); mean Kendall $\tau$; top-1 disagreement by horizon;
CL-evaluated selection regret
$R=\text{value}_{CL}(a^*_{CL})-\text{value}_{CL}(a^*_{MT})$ among
disagreement cases (the model-relative value lost by acting on MT's choice,
evaluated against the CL reference).

## 8. Confirmatory matrix

2 domains $\times$ 2 scenarios $\times$ 30 seeds $\times$ 2 decision rounds
$\times$ `H\in\{1,3,5\}` $\times$ 6 objectives $\times$ `K=4` candidates.
The experimental unit is the **decision set** (domain, scenario, seed,
round, objective, horizon); candidates within a set are correlated, not
independent samples. No production `src/` change; the E2 roll-out and
schedule functions are reused through their public interface.

## 9. Pilot findings (implementation/reporting only; design unchanged)

Pilot: 2 domains $\times$ 1 scenario $\times$ 5 seeds = 360 decision sets
(240 eligible). Findings:

1. **The mechanism is live.** Candidate policies genuinely differ
   (e.g. restriction 0/1/2), and their standing-policy histories diverge
   substantially (default history 7469 infected vs a candidate history
   13668) --- distinct state digests for all candidates.
2. **Degenerate objectives exist and were excluded** (energy:
   `renewable_share`, `unserved_energy`; epidemic: `equity_gap`,
   `overflow_days` --- one candidate always dominates). Reported separately;
   removed from the primary denominator.
3. **Top-1 decision flips are rare despite large magnitude errors.**
   Eligible top-1 disagreement 0.83% pooled (energy 0%, structural; epidemic
   1.67%), pairwise inversion ~1%, mean Kendall $\tau$ 0.99 --- the
   "magnitude-biased but conclusion-stable" regime dominates, consistent
   with E3's approximate region being common.
4. **When top-1 flips, CL-regret is nonzero** (both pilot flips had
   nonzero regret, median 7544 infections) --- the flips that do occur carry
   real model-relative cost.
5. **Correction (reporting only):** added the degeneracy/eligibility split
   and the pairwise-inversion endpoint after the pilot exposed the
   dominant-candidate dilution. No design change.

## 10. Claim boundary

Supports: MT and CL supported different model-relative intervention
rankings in a specified (small) proportion of evaluated eligible decision
sets, with nonzero CL-regret when the top choice flipped, and no impact in
the structurally exact domain. Does not establish: that MT causes the wrong
\emph{real-world} policy (the objectives are model-relative and
uncalibrated), nor the prevalence of decision flips in any model outside the
two evaluated domains.
