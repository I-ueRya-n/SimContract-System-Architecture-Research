# Paper 2 Ablation A2 — result package (confirmatory)

Offline analysis (not a wrapper): compares same-resolution branch separation
against a separate `rule`-baseline trajectory. 120 (domain, scenario, seed)
pairing keys x 2 submitted conditions = 240 submitted runs + 120 shared
default runs, 6 rounds each, 8640 (round x metric) records.

Regenerate: `PYTHONPATH=src python3 experiments/ablations/analyze_branch_separation.py`
Pilot (exploratory, excluded from this result): `pilot_notes.md`, `manual_spot_checks.md`.

Headline: energy_market_v1 shows attribution error exactly 0.0 at every
round -- source-verified structural finding (`_clear()` never reads carried
state; `rule`'s applied action is state-independent, so the trajectory
substitute is mathematically identical to the local divergence). epidemic_
policy_v1 shows 0.0 at round 1 (shared initial state) then monotonically
increasing normalized attribution error across rounds 2-6 (0.110 -> 0.249 ->
0.394 -> 0.557 -> 0.730), with a 0.643 Pearson correlation between
trajectory_history_distance and attribution error -- consistent with
`_simulate()` genuinely reading back the carried SEIR compartment state.
All 6 pre-registered gates pass (0 pairing/rule/exogenous/metric/round
violations across 120 pairing keys). Re-run verified bit-identical.
