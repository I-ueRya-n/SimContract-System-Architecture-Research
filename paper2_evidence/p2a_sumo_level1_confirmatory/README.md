# SUMO Level-1 confirmatory transfer study

Protocol: `docs/protocols/p2a_sumo_level1_transfer.md` Sec. 10-14. Script:
`experiments/sumo_transfer/confirmatory_study.py`. 60 canonical runs: 1
synthetic network x 2 demand configurations (`grid3x3_moderate_v1`, 20
vehicles/60s; `grid3x3_dense_v1`, 60 vehicles/60s) x 3 deterministic
conditions (`rule`, `fixed_valid_intervention_A` = force phase 2
EW-priority, `fixed_valid_intervention_B` = force phase 1 all-stop) x 10
paired seeds (101-110), 10 rounds x 5 simulated seconds each.

## Result: GO (all Sec. 13 stop conditions avoided; Sec. 14 decision rule satisfied)

| Measure | Result |
|---|---:|
| Runs completed | 60 / 60 |
| Run-level replay pass rate | 1.0 (60/60) |
| Evidence mismatch count | 0 |
| Process-cleanup failure count | 0 (`pgrep -fc sumo`: 2 before, 2 after the entire matrix -- those 2 pre-existing processes are unrelated to this run and unchanged by it) |
| Contract-compliance (`verify_bundle`) pass rate | 1.0 (60/60) |
| Generic-analyzer pass rate | 1.0 (60/60) |
| Distinct configuration/input digests | 60/60 (no accidental duplicate cells) |
| Total bundle size (60 runs) | 1,458,200 bytes (~1.4 MB) |
| Mean wall-clock time per run | 12.5 s |

## A correction made before this result (kept, not hidden)

The first confirmatory pass used phase 1 vs. phase 3 as the two fixed
interventions. All 60 runs passed every gate, but `fixed_valid_intervention_A`
and `_B` produced bit-identical `waiting_time` on every one of the 10
seeds, in both demand configurations. Source-inspection of `net.xml`'s
`tlLogic` (not assumption) found the cause: phases 1 and 3 are both short
(3s), all-restrictive yellow transitions -- locking either one for a full
5s round blocks the junction equivalently regardless of which approach's
yellow it nominally is. Corrected to phase 2 (EW-priority, meaningfully
asymmetric to `rule`'s phase-0 NS-priority) and phase 1 (all-stop,
meaningfully distinct from both). The degenerate first pass is preserved
at `paper2_evidence/p2a_sumo_level1_confirmatory_superseded_phase1_vs_phase3/`
rather than deleted, and is not reported as evidence.

## Distinguishability (round-10 `waiting_time`, mean over 10 seeds)

| Condition | `grid3x3_moderate_v1` | `grid3x3_dense_v1` |
|---|---:|---:|
| `rule` (phase 0, NS-priority) | 68.6 | 214.2 |
| `fixed_valid_intervention_A` (phase 2, EW-priority) | 78.9 | 224.6 |
| `fixed_valid_intervention_B` (phase 1, all-stop) | 122.0 | 358.8 |

Consistent ordering (`rule` < `fixed_A` < `fixed_B`) holds across every
individual seed in both demand configurations, not just in the mean --
matches the mechanistic expectation (all-stop is the most disruptive,
the two green-priority conditions are closer to each other but still
distinct).

## Precise integration footprint (do not write "zero common-core changes")

```text
contracts/  changed   0
engine/     changed   0
analysis/   changed   0
evidence/   changed   0
composition root changed   1 file / 12 lines
```

*No frozen contract, engine, evidence, replay, or generic-analysis
implementation was modified. Integration required one 12-line
composition-root registration change using the same existing seam as the
built-in domains* -- the same shape and size `energy_market_v1` and
`epidemic_policy_v1` each already required.

## Explicit cleanup (protocol Sec. 12)

The confirmatory runner constructs the adapter and `SessionRunner`
directly (mirroring `Application.run_session()`'s own construction path)
specifically so it can call `SumoTransferAdapter.close()` -- an
adapter-owned, non-contract method -- in a `finally` block around both the
original run and the replay rerun, for all 120 adapter instantiations (60
runs x 2, original + replay). `__del__` is a safety net only. Zero leaked
processes confirmed by an external `pgrep` check before/after the entire
matrix, not merely per-run.

## `preview()` limitation (protocol Sec. 8/13)

None of the three confirmatory conditions (`rule`, `fixed_valid_intervention_A`,
`fixed_valid_intervention_B`) uses `preview()` for its decision: `rule`
delegates to the default-action provider directly, and the two fixed
interventions return a constant action regardless of candidates/previews.
Preview compatibility was implemented only as an approximate adapter
capability (constant, last-observed metric, not a forward simulation) and
is not used as evidence for controller-quality or scientific-outcome
claims anywhere in this study.

## Claim boundary

Supports: frozen SimContract contracts and evidence interfaces
(`contracts/`, `engine/`, `analysis/`, `evidence/replay_bundle.py`,
`engine/replay_executor.py`) wrap an external, non-co-designed,
imperative/stateful simulator across a small deterministic matrix (60
runs, 2 demand configurations, 3 distinguishable legal conditions, 10
paired seeds), with a single 12-line, same-shape-as-precedent addition to
the composition root, zero leaked processes, and 100% replay/verification/
generic-analysis pass rates. Does not establish: realistic traffic
behaviour, calibration validity, scaling to a real network or a larger
signal network, checkpoint-continuation fidelity beyond what Sec. 4a
discloses, or generality to other stateful external simulators beyond
SUMO.
