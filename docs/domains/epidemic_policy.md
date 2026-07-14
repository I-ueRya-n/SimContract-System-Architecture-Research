# epidemic_policy_v1

Controlled, literature-informed regional epidemic-policy testbed (SEIR
compartments after Kermack–McKendrick). **Not** a calibrated forecasting
model.

Roles/stages: stage 1 `health_authority` (restriction level, mask mandate,
vaccine budget); stage 2 `region_manager` ×3 (budget shares across testing,
vaccination, hospital capacity; shares must sum ≈ 1 — the canonical semantic
rejection case).

Dynamics: 7 daily SEIR substeps per weekly round across 3 heterogeneous
regions (population, density, initial infections); restriction and masking
multiply transmission; vaccination moves S → R under budget and capacity;
hospital overflow when severe cases exceed capacity.

Exogenous per round (sampled once, shared by both branches): imported-case
draw; compliance drift.

Metrics: `new_infections`, `cumulative_deaths`, `overflow_days`, `econ_cost`,
`vaccination_coverage`, `equity_gap` (max−min regional coverage).

Default policies: proportional-need budget split (managers), moderate
instruments (authority). Personas: `health_first`, `economy_balanced`
(authority); `equity_first`, `efficiency_first` (managers).

Scenarios: `seed_outbreak` (single-region seed), `second_wave` (broad
low-level seeding, higher import rate).

## Provenance matrix (consolidated spec §7.3)

Every component is classified; equations were implemented independently from
the public SEIR formulation, and every exact parameter value is **synthetic**
(pedagogical), not paper-estimated. "Based on a classical epidemic model" is
insufficient on its own, so the table separates literature structure from
SimContract mechanisms and synthetic values.

| Component | Source / status | SimContract adaptation | Verification |
|---|---|---|---|
| S–E–I–R compartment structure | literature-derived | four compartments + deaths | conservation-style checks; compliance suite |
| Infection / incubation / recovery transitions (β·S·I/N, σ·E, γ·I) | literature-derived equations | discrete daily Euler substeps | hand fixture; rerun identity |
| σ=1/4, γ=1/7, IFR=0.008, severe-fraction=0.05, vaccine-efficacy=0.85 | **synthetic** literature-bounded values (`model.py`) | fixed constants | documented in `model.py` |
| Three heterogeneous regions (pop, β₀, capacity) | controlled SimContract design | three contrasting regions | scenario-load test |
| Seven daily substeps per weekly round | numerical implementation choice | fixed substep count | determinism test |
| Restriction / mask transmission multipliers | **synthetic** illustrative (labelled) | multiply β per level | range/rejection tests on policy fields |
| Vaccination budget allocation (shares over testing/vaccination/capacity) | SimContract decision mechanism | shares MUST sum ≈ 1 | semantic-rejection test (`shares_not_normalised`) |
| Imported cases / compliance drift (exogenous) | synthetic process | fixed-seed, `shock_sigma` per scenario | rerun identity (E2) |
| Initial infection rates / prior immunity | **synthetic** scenario values | `scenarios/*.yaml` | scenario-load test |
| Default (rule) policy | SimContract design | domain `DefaultActionProvider` | SC-I2 completion test |

Parameter classification: all exact numeric values are **synthetic** or
literature-bounded; none are empirically calibrated or expert-elicited. The
mask/restriction multipliers are explicitly **illustrative**. Foundational
SEIR citations are flagged verify-before-camera-ready and do not validate the
parameter values or the policy-mechanic extensions.
