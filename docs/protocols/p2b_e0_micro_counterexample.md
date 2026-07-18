# Paper 2B-E0 — Minimal Hand-Computable Counterexample

**Protocol version:** 1.0 (frozen 2026-07-18)
**Experiment type:** Closed-form micro-model; every number is hand-computable
and independently reproduced by simulation.
**Primary paper:** Paper 2B (counterfactual-estimand integrity).
**Implementation:** `experiments/paper2b/e0_micro_counterexample.py`
**Status:** executed; all four regimes demonstrated; simulation matches the
closed form everywhere to 1e-9.

## 1. Objective

Lift Paper 2B's central claim from "a phenomenon observed inside a complex
simulator" (the energy/epidemic A2 result) to a fact anyone can verify by
hand:

> Even when the exogenous input schedule is **identical** across compared
> branches, if the branches begin from **different pre-intervention
> endogenous states**, a matched-schedule historical contrast (MT) can
> estimate a different quantity than a cloned-state continuation (CL) ---
> differing in magnitude, in sign, or in the ranking of interventions.

Success is not "MT is always wrong." Success is exhibiting all four
structural regimes in closed form, including the regime where MT and CL
agree.

## 2. Model

One persistent endogenous state `x`, one shared exogenous shock `u`, and an
action with two fields: an immediate `benefit` `b` and an accumulating
`load` `l` (its delayed footprint on the state).

```text
state transition:   x_{t+1} = rho * x_t + load_t + u_t
outcome (delayed):  Y = b_decision - w_x * x_final
```

`rho in [0,1)` is state persistence; `w_x >= 0` weights the delayed state
cost. The **delayed consequence**: a decision's `load` raises the state at
the outcome horizon and is penalised through `-w_x * x_final`, while its
`benefit` is collected immediately. This is an immediate-benefit /
delayed-cost trade-off, the minimal structure that makes history matter.

### 2.1 Rounds and horizon

```text
round 1  pre-decision   -- where submitted history and default history diverge
round 2  decision       -- intervention a vs default d is chosen here
round 3..(2+H-1)        -- continuation under the default policy
outcome read at         -- x_{2+H}   (H = horizon after the decision)
```

### 2.2 State-transition diagram

```text
                 factual history (load l_i)            default history (load l_d)
   x0 --round1--> x2^F = rho*x0 + l_i + u1      x0 --round1--> x2^D = rho*x0 + l_d + u1
                    |                                            |
        clone x2^F for CL (both branches share it)   (MT branch D keeps its own x2^D)
                    |                                            |
     +--------------+--------------+                             |
     | decision a (load l_i)       | decision d (load l_d)       | decision d (load l_d)
     v                             v                             v
   x3^A = rho*x2^F + l_i + u2    x3^B = rho*x2^F + l_d + u2    x3^D = rho*x2^D + l_d + u2
     | continuation (load l_d)     | continuation (load l_d)     | continuation (load l_d)
     v                             v                             v
   x4^A                          x4^B                          x4^D
     \___ Y^A = b_i - w_x x4^A     \___ Y^B = b_d - w_x x4^B     \___ Y^D = b_d - w_x x4^D

   Delta_CL = Y^A - Y^B      (both branches from the SAME clone x2^F)
   Delta_MT = Y^F - Y^D      (Y^F == Y^A; branch D starts from a DIFFERENT state x2^D)
```

The only difference between CL and MT is the pre-decision state of the
default branch: CL clones `x2^F`, MT uses the separately evolved `x2^D`.
The exogenous schedule `u1,u2,...` is identical in every branch.

## 3. Closed forms

With default `d = (b_d, l_d)`, candidate `i = (b_i, l_i)`, `db = b_i-b_d`,
`dl = l_i-l_d`, horizon `H`:

```text
Delta_SR_i      = db - w_x                     * dl        # one-step (H=1)
Delta_CL_{i,H}  = db - w_x*rho^{H-1}           * dl        # cloned continuation
Delta_MT_{i,H}  = db - w_x*(rho^H + rho^{H-1}) * dl        # matched-schedule history
AE_MT_{i,H}     = | Delta_MT - Delta_CL | = w_x * rho^H * |dl|
```

The exact statement is

```text
AE_MT_{i,H} = 0   <=>   w_x = 0   OR   rho^H = 0   OR   dl = 0
```

Over the parameter domain of this study --- `w_x >= 0`, `0 <= rho <= 1`,
`H >= 1` integer --- `rho^H = 0` holds exactly when `rho = 0`, so the three
disjuncts read as: no delayed-cost weighting (`w_x=0`); memoryless dynamics
(`rho=0`); or no historical-state divergence (`dl=0`). The shared exogenous
schedule cancels in every difference and never appears in a closed form.
This is the formal content of "same noise, different question."

## 4. The four regimes (hand-calculated)

Canonical actions: default `d=(b=0, l=0)`; aggressive `A=(b=3, l=3)`;
efficient `E=(b=2, l=1)`. Initial state `x0=1.0`; shared exogenous
`u=[0.3, -0.7, 0.5, ...]`.

### R1 --- equivalence (memoryless). `rho=0, w_x=0.5, H=2`, candidate A.
`rho=0` erases carried state, so `x2^F = x2^D` in outcome terms and both
estimands equal `db = 3`. `Delta_CL = Delta_MT = 3.0`, `AE = 0`.

### R2 --- magnitude error (correct sign). `rho=0.5, w_x=0.5, H=2`, candidate A.
```text
Delta_CL = 3 - 0.5*0.5*3      = 3 - 0.75  = 2.250
Delta_MT = 3 - 0.5*(0.25+0.5)*3 = 3 - 1.125 = 1.875
AE       = 0.5*0.25*3         = 0.375
```
Both positive; MT understates the local effect by ~17 %.

### R3 --- sign reversal. `rho=0.9, w_x=1.0, H=2`, candidate A. Full round table:
```text
x2^F = 0.9*1.0 + 3 + 0.3   = 4.20      x2^D = 0.9*1.0 + 0 + 0.3 = 1.20
CL branch A: x3 = 0.9*4.20 + 3 - 0.7 = 6.08 ;  x4 = 0.9*6.08 + 0 + 0.5 = 5.972
CL branch B: x3 = 0.9*4.20 + 0 - 0.7 = 3.08 ;  x4 = 0.9*3.08 + 0 + 0.5 = 3.272
Y^A = 3 - 1.0*5.972 = -2.972 ;  Y^B = 0 - 1.0*3.272 = -3.272
Delta_CL = -2.972 - (-3.272) = +0.300           (intervention HELPS, decision-local)
MT branch D: x3 = 0.9*1.20 + 0 - 0.7 = 0.38 ;  x4 = 0.9*0.38 + 0 + 0.5 = 0.842
Y^F = -2.972 (== Y^A) ;  Y^D = 0 - 1.0*0.842 = -0.842
Delta_MT = -2.972 - (-0.842) = -2.130           (intervention HURTS, matched-history)
AE = |-2.130 - 0.300| = 2.430
```
The cloned decision-local effect says the intervention **helps** (`+0.30`);
the naive matched-history comparison says it **hurts** (`-2.13`), because
the accumulated delayed cost of the intervention's *own history* is folded
into the contrast. This is the paper's cleanest anchor.

### R4 --- ranking reversal. `rho=0.8, w_x=0.5, H=2`, candidates A and E.
```text
Delta_CL(A) = 3 - 0.5*0.8*3     = 1.800     Delta_CL(E) = 2 - 0.5*0.8*1 = 1.600
  CL ranking: A > E   (aggressive preferred)
Delta_MT(A) = 3 - 0.5*(0.64+0.8)*3 = 0.840  Delta_MT(E) = 2 - 0.5*1.44*1 = 1.280
  MT ranking: E > A   (efficient preferred)   ---> RANKING REVERSAL
```
The efficient intervention has a smaller historical footprint, so MT's
extra `rho^H` history penalty hurts the aggressive one more, flipping the
top-1 choice. Ranking reversal needs two interventions whose immediate
benefit and delayed load are not proportional --- exactly the (benefit,
load) two-field action here.

## 5. Feasibility gates (all must pass)

```text
G1  simulation reproduces every closed form to <= 1e-9
G2  R1 shows equivalence (AE == 0)
G3  R2 shows magnitude error (same sign, MT != CL)
G4  R3 shows sign reversal (Delta_CL > 0, Delta_MT < 0)
G5  R4 shows ranking reversal (CL top-1 != MT top-1)
G6  fixtures serialise deterministically and hash-match on re-run
```

## 6. Outputs

`paper2_evidence/p2b_e0_micro_counterexample/`: `e0_results.json` (per-regime
simulated and closed-form estimands, regime classification, ranking check,
and the exhaustive `rho x w_x` sweep), `e0_fixtures.json` +
`e0_fixtures.sha256` (machine-readable expected values with a content hash
for regression), and `README.md`. Regression test:
`tests/test_p2b_e0_micro_counterexample.py`.

## 7. Claim boundary

Supports: the SR/CL/MT/RS estimand distinction is real and structural, not
an artefact of any complex domain --- all four regimes exist in closed form
under identical exogenous input. Does not establish: the frequency of each
regime in real models (that is 2B-E3 structural boundary and 2B-E4
conclusion impact), nor any behavioural validity claim. E0 is the
theoretical anchor; it is deliberately a toy, and is labelled as one.
