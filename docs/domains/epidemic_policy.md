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
low-level seeding, higher import rate). Provenance: equations implemented
independently from the public SEIR formulation; parameters pedagogical,
documented in `defaults.py`.
