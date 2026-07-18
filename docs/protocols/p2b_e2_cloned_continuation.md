# Paper 2B-E2 — Cloned-Continuation Confirmatory Study

**Protocol version:** 1.0 (frozen 2026-07-18, before confirmatory execution;
pilot findings recorded in §9 do not change the confirmatory design)
**Experiment type:** Confirmatory paired comparison of counterfactual
estimands under a shared, injected exogenous schedule.
**Primary paper:** Paper 2B. **Implementation:**
`experiments/paper2b/e2_cloned_continuation.py`.
**Depends on:** the executed feasibility probe (`p2b_feasibility_cloned_continuation`)
and 2B-E0 (`p2b_e0_micro_counterexample`). E2 is the mechanism that makes
Paper 2B independent of Paper 2A: A2 measured only the one-step
same-resolution contrast (SR); E2 measures the multi-step cloned-state
local reference (CL) and how far the matched-schedule (MT) and resampled
(RS) contrasts depart from it.

## 1. Objective

For a real decision point in each controlled domain, measure the four
estimands of §Estimands under an **identical, injected future exogenous
schedule**, at horizons `H in {1,3,5}`, and quantify when the convenient
matched-schedule contrast (MT) departs from the cloned-state local
reference (CL) --- in magnitude, sign, and intervention ranking --- and how
that departure grows with the horizon.

## 2. Estimands (framework realisation of the Sec. estimands)

Let `S_t^F` be the factual pre-decision state at round `t` (from a
submitted-condition run), `S_t^D` the pre-decision state of a separately
evolved all-default run at the same round, `a_t` the submitted intervention
action recorded at round `t`, `d_t` the domain default action, `pi` the
continuation policy (domain default every round), `U = [u_t..u_{t+H-1}]` a
future exogenous schedule, and `Y_m` metric `m` at the outcome horizon.

Define `roll_out(S, action_t, U, H)` = apply `action_t` at round `t` with
exogenous `u_t`, then `H-1` continuation rounds under `pi` with exogenous
`u_{t+1}..u_{t+H-1}`, all via the unmodified public `adapter.step`; return
the metric vector of the final step.

```text
Delta_SR_{t,m}     = roll_out(S_t^F, a_t, U, 1) - roll_out(S_t^F, d_t, U, 1)
Delta_CL_{t,m,H}   = roll_out(S_t^F, a_t, U, H) - roll_out(S_t^F, d_t, U, H)
Delta_MT_{t,m,H}   = roll_out(S_t^F, a_t, U, H) - roll_out(S_t^D, d_t, U, H)
Delta_RS_{t,m,H}   = roll_out(S_t^F, a_t, U_F, H) - roll_out(S_t^D, d_t, U_D, H)
AE_MT_{t,m,H}      = | Delta_MT - Delta_CL |
```

CL clones `S_t^F` for both branches; MT's default branch begins from the
separately evolved `S_t^D`; SR is CL at `H=1`; RS additionally uses
independently resampled schedules `U_F != U_D != U`. `AE_MT` isolates the
history-divergence contribution because CL and MT share the intervention
branch exactly and differ only in the default branch's pre-decision state.

## 3. Shared exogenous schedule (injection, not per-branch redraw)

`U` is drawn **once** from a reference roll-out (default action throughout,
from `S_t^F`) and the identical `u`-dicts are injected into every CL and MT
branch via `StepContext.exogenous`. This makes "same future exogenous
schedule" a construction guarantee independent of any domain's
`sample_exogenous` state-dependence (energy's AR(1) `eps` reads carried
state; epidemic's does not). RS deliberately breaks this: `U_F` and `U_D`
are redrawn under distinct rng labels so history divergence and sampling
variation combine. Gate G2 verifies the injected digests are byte-identical
across CL/MT branches.

## 4. Hard gates (every branch pair must pass; a failure aborts the cell)

```text
G1  checkpoint hash identity          clones of S_t^F share one digest
G2  future exogenous digest equality  CL/MT branches use byte-identical U
G3  continuation-policy identity       same default provider object/version
G4  single-action difference at t      CL branch A vs B differ ONLY in a_t vs d_t
                                       (state, exogenous, ctx otherwise identical)
G5  branch state isolation             deepcopy; mutating one branch's state
                                       cannot affect another (mutation probe)
G6  simulator/scenario/metric identity same adapter, scenario, metric keys, units
G7  factual trajectory untouched       cloning does not alter the original run's
                                       recorded metrics
G8  rerun determinism                  repeating a roll_out reproduces it exactly
G9  no cross-branch state read         branch B result invariant to a post-hoc
                                       mutation of branch A's state (isolation)
G10 H=1 CL aligns with SR + internal   Delta_CL at H=1 == Delta_SR, and both equal
                                       the adapter's own applied-minus-authoritative
                                       branch at round t (the A2/probe identity)
```

## 5. Primary and secondary endpoints

Primary: `AE_MT_{t,m,H}` (absolute) and its IQR-normalised form (scale from
the all-default population, as in A2); sign disagreement between `Delta_CL`
and `Delta_MT`; intervention-ranking disagreement (order of two submitted
conditions by `Delta_CL` vs by `Delta_MT`); and `AE_MT` growth across
`H in {1,3,5}`. Secondary: branch-state distance at the horizon;
divergence-onset round; delayed-effect capture (does the effect at `H=5`
exceed `H=1`?); and the proportion of cells within a pre-registered
approximation tolerance `tau = 0.05` normalised.

## 6. Experimental unit and matrix

The unit is **(domain, scenario, seed, intervention round, horizon,
metric)** --- NOT a whole submitted run (unlike Paper 2A's 240-run count).
Confirmatory matrix: 2 domains x 2 scenarios x 30 paired seeds x the
intervention rounds x `H in {1,3,5}` x the domain metrics, with two
submitted conditions (`random_valid`, `top_score`) providing the two
candidate interventions for the ranking endpoint and `rule` providing the
all-default history. Intervention rounds: the mid-run rounds for which a
`t+H-1 <= rounds` continuation fits (rounds 1..(R-max_H)); `R=6`, so rounds
1 with `H<=5`.

## 7. Exclusions and stop rules

Exclude a metric from the normalised endpoints (not from the raw record) if
its all-default IQR is zero (constant metric; flagged, not dropped). Stop
and disclose a domain as out of scope if cloned continuation cannot be
constructed without modifying frozen production semantics, or if any hard
gate G1--G10 cannot be made to pass by fixing experiment-owned code only.
No production `src/` change is permitted; E2 uses the public API exactly as
the engine does.

## 8. Pilot (plumbing only; not a confirmatory claim)

2 domains x 1 scenario each x 5 seeds x `H in {1,3,5}`, checking: checkpoint
identity, injected-schedule equality, continuation isolation, metric
alignment, H-step indexing, CL/MT/RS computation, output schema, runtime and
storage. Pilot output lives under `.../pilot/` and is never pooled into the
confirmatory result.

## 9. Pilot findings (implementation-only corrections; design unchanged)

Pilot: 2 domains x 1 scenario x 5 seeds x `H in {1,3,5}` x 3 intervention
rounds x 2 conditions = 180 cells. All hard gates G1--G10 pass. Findings:

1. **Energy is structurally zero, epidemic is path-dependent.** Every
   `energy_market_v1` cell has `AE = 0` exactly (540/540 raw values), while
   `epidemic_policy_v1` has 300/540 nonzero, normalised median $0.25$, max
   $2.0$. This reproduces the A2 domain contrast and matches 2B-E0's R1
   (memoryless-outcome) vs.\ path-dependent regimes: energy's clearing
   function does not read carried state, so cloned and matched-schedule
   branches coincide.
2. **The departure grows with horizon (epidemic).** Normalised $AE$ medians
   rise monotonically: $H{=}1\!\to\!0.199$, $H{=}3\!\to\!0.277$,
   $H{=}5\!\to\!0.345$. This is the multi-step result E2 exists to produce
   and that A2 (one-step only) could not show.
3. **Correction (implementation only):** the initial G2 gate was a
   tautology (`... or True`); replaced with a real determinism check ---
   rebuilding the schedule from identical inputs must yield byte-identical
   digests. No design change.
4. **Correction (reporting only):** the pooled median is dominated by the
   structurally-zero domain and reads as $0$; per-domain endpoints were
   added so the path-dependent result is visible. No design change.

Neither correction alters the confirmatory matrix, estimands, gates, or
endpoints; both were plumbing/reporting fixes, exactly what the pilot is
for. The confirmatory design (§6) is unchanged and frozen.

## 10. Claim boundary

Supports: a real-domain, multi-step measurement of how far MT and RS depart
from the cloned-state local reference CL, with every branch pair gate-checked
for checkpoint, schedule, policy, and isolation identity. Does not establish:
how often each regime occurs across the full structural space (2B-E3), whether
the departures change a scientific decision (2B-E4), or any behavioural
validity of the domains. E2 is the empirical multi-step reference that E0
anchors in closed form.
