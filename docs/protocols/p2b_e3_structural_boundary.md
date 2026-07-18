# Paper 2B-E3 — Structural Boundary Study

**Protocol version:** 1.0 (frozen 2026-07-18; pilot findings §9 are
implementation/reporting only and do not change the confirmatory design)
**Experiment type:** Parameterized structural sweep (fractional-factorial)
mapping when the matched-schedule contrast (MT) is an exact, approximate, or
misleading substitute for the cloned-state local reference (CL).
**Primary paper:** Paper 2B. **Implementation:**
`experiments/paper2b/e3_structural_boundary.py`.
**Depends on:** 2B-E0 (closed-form regimes) and 2B-E2 (real-domain
multi-step reference). E3 does NOT claim MT always fails; it produces a
boundary map with positive (exact/approximate) and negative (divergent)
regions.

## 1. Question

Under which structural conditions is a matched-exogenous trajectory an
exact, a useful approximate, or a misleading substitute for a cloned-state
local continuation? The two real domains anchor two corners with executed
2B-E2 evidence --- `energy_market_v1` (exact regime, state-independent
outcome) and `epidemic_policy_v1` (divergent regime, path-dependent) --- and
E3 fills the interior by varying structure continuously in a parameterized
generalisation of the 2B-E0 micro-model.

## 2. Literature gate (narrow; done before this freeze)

Per the standing rule (a narrow literature gate before each protocol
freeze, no result-fishing after), seven sources were web-verified on
2026-07-18 and used to ground the factor definitions and the design choice,
not as Related-Work decoration:

| Source | Structural mechanism / method | Use in E3 |
|---|---|---|
| Arthur 1989 (Econ. J. 99(394):116-131) | increasing returns, lock-in, path dependence | irreversibility=lockin factor; why history matters |
| Page 2006 (QJPS 1(1):87-115) | typology of path dependence vs state persistence | separates persistence (rho) from history-dependence (timing) |
| Dixit \& Pindyck 1994 (Princeton) | irreversibility / hysteresis under uncertainty | irreversibility (ratchet/lockin) and volatility factors |
| Sterman 2000 (McGraw-Hill) | endogenous feedback / system dynamics | feedback factor (phi) |
| Kleijnen 2015 (Springer, doi 10.1007/978-3-319-18087-8) | fractional-factorial / screening designs for simulation | the 2^(7-2) design (§5) |
| Sanchez, Sanchez \& Wan 2020 (WSC) | efficient high-dimensional simulation experiments; interactions | why not full Cartesian; preserved interactions |
| Saltelli et al. 2008 (Wiley) | variance-based sensitivity / factor importance | boundary-map factor-effect reading |

## 3. Model

Extends 2B-E0's `x_{t+1} = rho*x_t + load + u` with structural factors:

```text
x_{t+1} = irrev( rho*x_t + phi*tanh(x_t) + load_t + sigma*u_t )
outcome  = benefit_decision - w_x * x_final          (delayed cost)
irrev = reversible : identity
        ratchet    : max(x_t, .)                     partially irreversible
        lockin     : threshold-triggered near-full persistence (increasing returns)
```

Actions are `(benefit, load)` scaled by magnitude; the default is `(0,0)`;
the continuation policy is the default action every round. The SR/CL/MT/RS
estimands and the injected-shared-schedule discipline are identical to
2B-E2, run here on the parameterized model so every factor can vary.

## 4. Factors and levels

```text
rho        persistence           lo 0.2   hi 0.9
phi        feedback strength     lo 0.0   hi 0.6   (on tanh(x))
irrev      irreversibility       lo reversible     hi lockin
w_x        delayed-cost weight   lo 0.0   hi 1.0
sigma      exogenous volatility  lo 0.3   hi 1.5
timing     intervention round    lo 2     hi 5     (>=2 so history diverges)
magnitude  intervention size     lo small hi large
horizon H  outcome horizon       {1, 3, 5}  (crossed fully within every cell)
```

## 5. Confirmatory design

**A 2^(7-2) resolution-IV fractional factorial** on the seven structural
factors (32 cells), generators `F = A*B*C` (timing = rho*phi*irrev) and
`G = A*D*E` (magnitude = rho*w_x*sigma) in +-1 coding; main effects clear of
two-factor interactions. Not a full Cartesian product (which would be
2^7 = 128 structural cells before horizons/seeds/candidates), per Kleijnen
2015 / Sanchez et al. 2020. Horizon (3 levels) and candidate (2:
aggressive, efficient) are crossed fully within every cell, so all
factor x horizon interactions --- feedback x horizon, persistence x horizon,
delayed x horizon --- are estimable regardless of the fraction. Seeds: 40
paired seeds (the pilot's factor effects are large and clean; 40 gives
stable regime-prevalence estimates without excess compute).

## 6. Regime classification (preregistered)

Per (cell, seed, candidate, horizon):

```text
relative_error = |MT - CL| / (|CL| + 1e-6)
exact       :  |MT - CL| <= 1e-6                     (MT reproduces CL)
divergent   :  sign(CL) != sign(MT)  (both nonzero)  (sign reversal)
            OR relative_error > TOL_REL              (magnitude beyond tolerance)
approximate :  otherwise                             (biased, conclusion-stable)
```

**Preregistered tolerance `TOL_REL = 0.10`** (MT within 10% of the local
effect `|CL|`). This is a NEW E3 threshold on a relative quantity, distinct
from 2B-E2's IQR-based 0.05 (the IQR-of-default scale is degenerate in the
micro-model because default-action variation is tiny relative to
intervention effects). The E2 IQR-normalised AE is still recorded as a
secondary quantity. The tolerance is frozen here and is NOT re-chosen from
confirmatory results; a sensitivity analysis over `TOL_REL in {0.05, 0.10,
0.20}` accompanies the confirmatory report.

## 7. Primary and secondary endpoints

Primary: regime prevalence (exact / approximate / divergent) and the
**boundary map** --- divergent-share by factor level. Secondary: sign
disagreement rate; ranking disagreement rate (aggressive vs efficient);
absolute `|MT-CL|` by horizon among non-exact cells; and the relationship of
divergence to pre-decision state-distance `|S_t^F - S_t^D|`.

## 8. Success criteria and stop rule

E3 succeeds if it produces a boundary map with all three regimes located in
factor space --- an exact region, an approximation region, and a divergent
region --- not if MT fails everywhere. A model in which no factor setting
produces divergence, or one in which every setting does, would be a failure
to separate the regimes and would be reported as such. No production `src/`
change; the micro-model is a standalone Paper 2B artifact.

## 9. Pilot findings (implementation/reporting only; design unchanged)

Pilot: 11 corner/edge cells (all-lo, all-hi, each single-factor-hi, two
mixed corners) x 15 seeds x 2 candidates x 3 horizons = 990 records.
Findings:

1. **All three regimes appear** (exact 0.73, approximate 0.06, divergent
   0.21); the exact regime is anchored by `w_x=0` (no delayed cost) and low
   persistence, exactly as 2B-E0 predicts.
2. **Boundary map is well-separated.** Divergent share rises sharply with
   the delayed-cost weight (`w_x` lo 0.00 -> hi 0.78), persistence (`rho`
   0.04 -> 0.67), and late intervention timing (0.04 -> 0.67); moderately
   with magnitude (0.15 -> 0.50); weakly with feedback, irreversibility, and
   volatility (0.17 -> 0.33). This matches the path-dependence theory in the
   §2 sources: divergence needs memory, a delayed consequence, and
   accumulated history.
3. **Ranking reversal is rare** (0% in the pilot cells) --- the strongest
   divergence form; the confirmatory fractional factorial tests more factor
   combinations for it.
4. **Bounded feedback saturates the horizon effect.** With `tanh` feedback
   and lock-in ceilings the absolute `|MT-CL|` does not grow monotonically
   with the horizon (it can saturate), unlike 2B-E2's unbounded epidemic ---
   a genuine structural nuance, reported, not corrected.
5. **Correction (reporting/normalisation only):** classification switched
   from the E2 IQR scale (degenerate here) to a preregistered relative-error
   tolerance (§6); horizon trend reported as absolute `|MT-CL|` (its relative
   form has a horizon-growing denominator). No design change.

## 10. Claim boundary

Supports: a structural boundary map locating where MT is exact, an
acceptable approximation, or misleading, as a function of persistence,
feedback, irreversibility, delayed cost, volatility, timing, and magnitude,
in a parameterized micro-model, with two real-domain corners anchored by
2B-E2. Does not establish: the prevalence of each regime in any specific
real model beyond the two anchors, whether the divergences change a
scientific decision (2B-E4), or behavioural validity of any domain.
