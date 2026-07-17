# Paper 2 Architecture Ablation A2 — Replacing Same-Resolution Branch Separation with a Separate Default Trajectory

**Protocol version:** 0.1 (draft; to be frozen as 1.0 after an exploratory pilot)
**Experiment type:** Controlled architecture ablation (paired, cross-run)
**Primary paper:** Paper 2 — Cross-Domain Contract Portability
**Implementation (planned):** `experiments/ablations/no_branch_separation.py` (explicit wrapper; no production code modified). No experiment code is written before this draft exists; the pilot may revise it; v1.0 is hashed before the confirmatory run.

## 1. Objective and proposition

Tests proposition P3: computing the authoritative (all-default) and applied
outcomes **in the same resolution, from the same current state and the same
realized exogenous inputs**, measures a *local decision effect* that cannot
be replaced by comparing two independently evolving trajectories.

The corrected core claim (recorded deliberately): the substitute is **not**
wrong because it resamples randomness — the seeding design keeps the shock
schedule matched — but because after the first intervention a separate
all-default trajectory begins later rounds from a different state history,
so its difference mixes the current decision effect with accumulated
effects of earlier decisions.

## 2. Definitions

For round $t$ and catalogued metric $m$:

- **Local divergence (intact mechanism, already recorded in every bundle):**
  $D^{local}_{t,m} = M_m(\text{applied branch}_t) - M_m(\text{authoritative branch}_t)$,
  both computed inside one `step()` from the same $S_t$ and same $X_t$.
- **Trajectory substitute (ablated estimate):**
  $D^{traj}_{t,m} = M_m(\text{submitted-run round } t) - M_m(\text{default-run round } t)$,
  where the default run is a separate execution of the same
  (domain, scenario, seed) under the `rule` condition — `rule` delegates to
  the domain default policy, and its applied branch equals its authoritative
  branch (verified in E4), so it *is* the all-default trajectory.
- **Primary endpoint — local attribution error:**
  $E_{t,m} = | D^{traj}_{t,m} - D^{local}_{t,m} |$.

## 3. Design facts this protocol depends on (verified against the code)

1. **Matched exogenous.** Round seeds derive from the run seed only;
   energy's AR(1) demand chain reads previous *exogenous* state, not
   action-dependent state, and epidemic shocks are pure RNG draws. The
   realized shock schedule is therefore identical across the submitted and
   default trajectories under one seed. This is *verified empirically*, not
   assumed: `exogenous_digest` is recorded per round in both bundles and
   compared (`exogenous_match_rate`, expected 100%; any mismatch is
   reported and investigated before results are interpreted).
2. **The intact mechanism needs no new instrumentation:** both branches are
   already in every round record; the ablated estimate is computed offline
   from two bundles. The experiment is therefore bundle-only analysis over
   paired runs — production code untouched by construction.

## 4. Run matrix

Reuses the strong-matrix configuration and seed schedule:

2 domains × 2 scenarios × **2 submitted conditions** (`random_valid`,
`top_score`) × 30 seeds × 6 rounds, each paired with the `rule` run of the
same (domain, scenario, seed) as the default trajectory
= 240 submitted runs + 120 shared default runs.

`rule` is excluded as a submitted condition (its local divergence is
identically zero; it serves as the trajectory baseline). LLM conditions are
excluded (Paper 3). Unit of analysis: (round × metric) pairs, reported per
domain, scenario, condition, metric, and round index.

## 5. Outcomes

**Primary:** distribution of the local attribution error $E_{t,m}$ after
per-metric normalization (see §6): median, IQR, p95, by round index.
**Secondary:**
- `sign_disagreement_rate` — share of (t, m) where $D^{traj}$ and $D^{local}$
  disagree in sign (both nonzero under tolerance);
- `rank_disagreement_rate` — share of adjacent-round pairs ranked
  differently by the two estimators;
- `error_growth_by_round` — normalized error by round index (round 1 is
  expected to show near-zero error: histories have not diverged; growth
  across rounds is the state-history signature);
- `trajectory_history_distance` — normalized distance between the submitted
  and default trajectories' *pre-decision* states by round, connecting error
  growth to state divergence rather than only reporting disagreement;
- `exogenous_match_rate` — validity check per §3.

**Reporting:** descriptive statistics with per-domain breakdowns; no NHST.
The relationship between history distance and attribution error is shown,
not asserted.

## 6. Normalization (preregistered)

Metrics are heterogeneous in scale. Each metric is normalized by the
interquartile range of its per-round values across the 120 default (`rule`)
runs of the same domain and scenario; metrics with zero IQR in the default
population are reported unnormalized and flagged. The normalization
population is fixed before the confirmatory run.

## 7. Outcome space (all results reportable)

- **Strong support:** attribution error grows with round index and with
  trajectory history distance.
- **Partial support:** growth appears in one domain or under specific
  scenarios/conditions only.
- **Weakening result:** the separate trajectory closely approximates local
  divergence under all tested conditions; reported as evidence that branch
  separation was unnecessary *for these domains*.
- **Structural limitation:** a near-memoryless model shows little history
  effect; reported as the sharper claim that branch separation matters for
  path-dependent models specifically.

## 8. Claim boundary

Supports at most: same-resolution branch separation is necessary to measure
local decision effects **in the evaluated domains, scenarios, and
conditions**; the separate-trajectory estimate answers a different
(cumulative) question there. Does not establish: universality across
simulation models, anything about controller decision quality, or external
validity of the domains.

## 9. Execution sequence

Draft v0.1 (this document) → implement wrapper → one-domain exploratory
pilot (excluded from confirmatory results) → record any protocol changes →
freeze v1.0 → hash protocol + configuration → confirmatory matrix →
verified machine-readable package under
`paper2_evidence/p2_ablation_no_branch_separation/` → Paper 2 table and
discussion.
