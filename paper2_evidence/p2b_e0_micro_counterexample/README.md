# Paper 2B-E0 — minimal hand-computable counterexample

Protocol: `docs/protocols/p2b_e0_micro_counterexample.md` v1.0 (SHA-256
prefix `2865e75da2abeacb`). Script:
`experiments/paper2b/e0_micro_counterexample.py`. Regression test:
`tests/unit/test_p2b_e0_micro_counterexample.py` (7 tests, all pass).

## Result: all four regimes demonstrated; simulation == closed form everywhere

A one-state, delayed-cost micro-model (`x_{t+1} = rho*x_t + load_t + u_t`,
outcome `Y = benefit - w_x*x_final`) exhibits, in closed form and under an
**identical shared exogenous schedule**, every way a matched-schedule
historical contrast (MT) can depart from a cloned-state continuation (CL):

| Regime | Config | CL | MT | AE | Finding |
|---|---|---:|---:|---:|---|
| R1 equivalence | rho=0, w_x=0.5 | +3.000 | +3.000 | 0.000 | memoryless: MT == CL |
| R2 magnitude error | rho=0.5, w_x=0.5 | +2.250 | +1.875 | 0.375 | same sign, MT understates ~17% |
| R3 sign reversal | rho=0.9, w_x=1.0 | +0.300 | −2.130 | 2.430 | CL: intervention helps; MT: it hurts |
| R4 ranking reversal | rho=0.8, w_x=0.5 | A +1.800 / E +1.600 | A +0.840 / E +1.280 | — | CL prefers aggressive; MT prefers efficient |

The simulator reproduces every closed-form value to 1e-9: the
implementation provides machine-checkable verification of the closed-form
derivation (protocol §3) and reproduces all hand-computed values (protocol
§4 gives the full round-by-round table for R3). The proof is the algebraic
derivation; the code verifies the implementation agrees with it.

## Why it matters

The attribution error has an exact closed form,
`AE_MT = w_x * rho^H * |load_i - load_d|`, which is **zero iff**
`w_x = 0` **or** `rho^H = 0` **or** `load_i = load_d`; over this study's
domain (`w_x >= 0`, `0 <= rho <= 1`, `H >= 1`) that reads as no delayed
cost, memoryless dynamics (`rho = 0`), or no historical-state divergence.
This
is the formal statement of Paper 2B's thesis: identical exogenous randomness
is necessary but not sufficient; once pre-intervention endogenous states
diverge, MT and CL are different estimands. The energy/epidemic A2 result
(exact-zero vs growing error) is the same fact observed in complex domains;
E0 is its theoretical anchor.

## Files

- `e0_results.json` — per-regime simulated and closed-form estimands, regime
  classification, the R4 ranking check, and an exhaustive `rho x w_x` sweep
  showing the sign-reversal region is a contiguous structural family, not a
  cherry-picked point.
- `e0_fixtures.json` + `e0_fixtures.sha256` — machine-readable expected
  values with a content hash; the hash is deterministic across re-runs
  (gate G6, verified) and is what the regression test and any external
  reproduction check against.

## Gates (protocol §5)

G1 simulation == closed form (≤1e-9): PASS. G2 R1 equivalence: PASS. G3 R2
magnitude error: PASS. G4 R3 sign reversal: PASS. G5 R4 ranking reversal:
PASS. G6 fixtures hash deterministic on re-run: PASS.

## Claim boundary

Supports: the SR/CL/MT/RS estimand distinction is real and structural under
identical exogenous input — all four regimes exist in closed form. Does not
establish: how often each regime occurs in real models (2B-E3 structural
boundary, 2B-E4 conclusion impact), nor any behavioural validity. E0 is a
deliberate toy and is labelled as one.
