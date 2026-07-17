# A2 pilot notes (exploratory; not reported in Paper 2)

Two pilot passes were run, both excluded from any confirmatory result.

## Pass 1 — energy_market_v1 only (protocol-scoped pilot: 1 domain, 2
scenarios, 2 conditions, 5 seeds, 6 rounds)

All 6 gates passed. Result: **attribution error exactly 0.0 for every one of
720 records**, at every round including round 2 onward. This is more than
"small" — it is exact, which demanded investigation before trusting it as a
real null result rather than a bug.

**Root cause (source-verified, not assumed):** `EnergyMarketAdapter._clear()`
reads only the submitted `actions`, the round's `exogenous`, and the
per-run-constant `state["generators"]` table. It never reads
`state["market"]` (`last_clearing_price`, `last_demand`, `eps`). Because
`rule` always submits the domain's default action (verified by gate 2 —
`RuleController` is constructed with `adapter.default_action_provider`, the
exact object `step()` calls internally for the authoritative branch), and
because the default action itself does not depend on `state` (regulator/
generator/retailer defaults are pure persona-keyed lookup tables), the
authoritative branch of *any* submitted run equals the rule run's applied
branch **exactly**, at every round, regardless of how far the two
trajectories' states have diverged. Energy's outcome function is
structurally memoryless with respect to the state fields that could carry
trajectory history.

**Action:** extended the pilot to a second domain before drawing conclusions.

## Pass 2 — both domains (exploratory extension, `--tag bothdomains`)

Same config, `epidemic_policy_v1` added. Result: energy unchanged (exact
zero); epidemic shows round 1 = 0.0 (expected: identical shared initial
state) then **monotonically increasing** normalized attribution error
(0 -> 0.105 -> 0.272 -> 0.443 -> 0.610 -> 0.786 across rounds 1-6). Root
cause: `EpidemicPolicyAdapter._simulate()` reads `state["regions"]` (the SEIR
compartments) directly, and those compartments evolve from *applied*
dynamics each round, so submitted and rule trajectories genuinely diverge
after round 1. This is precisely the path-dependence effect A2 is designed
to detect, and its absence in energy is a legitimate, source-explained
structural-limitation result (protocol S7), not a defect in either the
domain or the analysis.

**Aggregation gap found:** the original aggregate pooled both domains into
one set of numbers, which would have hidden this exactly-explained
asymmetry inside a misleading average. **Fixed:** aggregate now reports
`overall` and `by_domain` separately; the by-domain split is load-bearing
for this experiment and must be reported in Paper 2, not just the pooled
figure.

## Pass 3 — corrected state-field vectors (`--tag corrected`)

Manual review of `normalization_scales.json` after Pass 2 found that
`policy.*` fields (both domains) and `market.*` fields (energy) were flagged
`constant_unnormalized`, i.e. zero variance in the rule population. Source
check confirmed why: `state["policy"]` is **never read** by either adapter
(grep-verified, zero occurrences outside the `state_next` assignment) — it
is write-only bookkeeping, and it is trivially constant under `rule` because
`rule` always submits the same default action. Including it in
`trajectory_history_distance` would have mixed a meaningless, unnormalized
raw-scale quantity into a otherwise-normalized mean distance.

**Fix applied to `STATE_FIELDS`:** dropped `policy.*` from both domains and
`market.*` from energy (source-verified reasons recorded as a code comment
in `analyze_branch_separation.py`). Energy's field vector is now
deliberately **empty** — `state_distance()` returns `None` (not `0.0`) so
"no carried state exists" is never conflated with "carried state happened to
match." Epidemic's field vector is now `summary.total_infected`,
`summary.total_deaths`, `summary.total_vaccinated` only — the documented
low-dimensional aggregate of the one field (`state["regions"]`) that is
mechanistically read back.

Re-running with the corrected vectors: attribution-error numbers are
**unchanged** (they never depended on the state vector), confirming the fix
only affected `trajectory_history_distance`, as intended. New result:
`history_distance_defined = False` for energy (correctly "not applicable"),
`True` for epidemic, with a **Pearson correlation of 0.625** between
`trajectory_history_distance` and normalized attribution error in epidemic —
a substantial, honestly-computed link between state divergence and
attribution error, exactly the descriptive relationship the protocol asked
for (support, not proof, of the causal story).

## Gate results (final, corrected pass)

All 6 pre-registered gates passed: pairing completeness, rule equivalence
(0 violations), exogenous equality (100% match), metric compatibility (0
mismatches), no duplicate keys, round alignment. See `pairing_audit.json`.

## Remaining known limitation, carried forward honestly

`unserved_energy` (energy), `equity_gap` and `overflow_days` (epidemic) show
zero variance in the rule population at pilot scale (5 seeds x 2 scenarios)
and fall back to the `constant_unnormalized` path. This may be a genuine
domain characteristic (rule's default policy may never bind these
constraints in either scenario) or a small-sample artifact. The
confirmatory run (30 seeds) will show whether this persists; if it does, it
is reported as a data characteristic in Paper 2, not treated as an error.

## Protocol revision required before freezing v1.0

Update the state-field-vector definition in
`p2_ablation_no_branch_separation.md` to state the corrected, source-verified
vectors and the read-back criterion, and add the aggregate reporting
requirement (`overall` + `by_domain`, never pooled-only).
