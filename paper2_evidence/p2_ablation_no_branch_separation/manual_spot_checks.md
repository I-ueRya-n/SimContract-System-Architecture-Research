# A2 manual spot checks (pilot, corrected pass)

## Row 1 — epidemic_policy_v1, second_wave_v1, seed 1, round 3, random_valid, new_infections

From `per_metric_round.csv`:
```
d_local = -880.77
d_trajectory = -3173.13
attribution_error = 2292.3600000000006
attribution_error_normalized = 0.45813435498037947
sign_disagreement = False
```

Hand check:
- `attribution_error = |d_trajectory - d_local| = |-3173.13 - (-880.77)| = |-2292.36| = 2292.36` — matches (floating-point tail is expected).
- `sign_disagreement`: `d_local * d_trajectory = (-880.77) * (-3173.13) > 0` — both negative, same sign, so `False` — matches.
- `attribution_error_normalized = 2292.36 / scale`. Solving: `scale = 2292.36 / 0.45813435... = 5003.65`, consistent with `normalization_scales.json`'s `state:new_infections` scale of `5004` (rounding). Also consistent in order of magnitude with the `new_infections` values already published in Paper 1's demonstration table (thousands-scale infection counts), an independent cross-check that the pipeline reads the right metric and units.

## Row 2 — epidemic_policy_v1, round 4

```
trajectory_history_distance = 0.3255126769626268
attribution_error_normalized = 0.26038952983500807
```
Both nonzero and finite, consistent with the domain's genuine path-dependence (`state["regions"]` carried forward). Round-4 individual value differing from the round-4 *mean* (0.443 in the aggregate) is expected — the aggregate averages over multiple (scenario, seed, condition, metric) combinations; this is one of them.

## Row 3 — energy_market_v1, round 1

```
d_local = 58.6232
d_trajectory = 58.6232
trajectory_history_distance = "" (empty / None)
```
`d_local == d_trajectory` exactly at round 1, as theoretically required
(shared initial state, shared exogenous, rule submits the same default
action the authoritative branch would use) — matches the source-verified
explanation. `trajectory_history_distance` is blank because
`STATE_FIELDS["energy_market_v1"]` is empty by design (no mechanistically
carried state); confirms `state_distance()` returns `None`, not a
misleading `0.0`.

## Gate cross-check

`pairing_audit.json` reports `all_gates_pass: true` with 0 violations on
`rule_equivalence` and 100% match on `exogenous_equality`, independently
confirming the two design facts (`rule` applied==authoritative; shared
exogenous schedule) that the hand checks above assume.

**Conclusion: no arithmetic or pairing defects found.** The pipeline is
trusted for the confirmatory run.
