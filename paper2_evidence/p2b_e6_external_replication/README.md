# Paper 2B-E6 — external integrity replication (SUMO) + E5 Layer-3

Protocol: `docs/protocols/p2b_e6_external_replication.md` v1.0 (SHA-256
prefix `a37a133684555527`). Script:
`experiments/paper2b/e6_external_replication.py`. Regression tests:
`tests/unit/test_p2b_e6_external.py` (6 tests). Feasibility spike under
`feasibility_spike/`, pilot under `pilot/`, confirmatory under
`confirmatory/`.

## What E6 closes

Two deliverables complete Paper 2B's required programme:
1. **Does the CL--MT distinction transfer to an independently developed
   imperative traffic simulator (Eclipse SUMO)?**
2. **Does the frozen E5 integrity checker transfer to independently
   generated external manifests (Layer 3)?**

## Construction: deterministic replay-to-branch, not saveState

The Paper 2A probe showed SUMO `saveState` is repeatable but not a complete
continuous-state oracle. E6 reconstructs pre-decision states by
**deterministic replay from origin**. A feasibility spike (5 gates) confirmed
this is exact: two independent replays of the same history reach a
byte-identical observable pre-state, no-intervention continuations are
bit-identical, reconstruction is reproducible, a different intervention
changes the outcome (default 258 vs EW-priority 164 vehicle-seconds), and
default vs candidate histories reach different pre-states. Mirroring 2B-E4:
CL scores every candidate from the SAME reconstructed default-history clone;
MT scores each candidate from its OWN standing-policy history; the primary
metric is normalised **cumulative** waiting (instantaneous waiting washes out
the history by the horizon). All 480 confirmatory cells passed the
clone-reconstruction check.

## Result 1: the distinction transfers, more strongly than internally

Confirmatory: grid scenario × 2 demand configs × 10 seeds × 2 rounds × 4
candidate signal programmes × H∈{1,3,5} = **480 estimand cells**.

| Measure | Value |
|---|---|
| External boundary | **external_divergent** |
| Normalised AE median | 0.107 (above the 0.10 tolerance) |
| Normalised AE max | 1.095 |
| AE by horizon (H=1/3/5) | 0.143 / 0.112 / 0.088 |
| Sign disagreement (d_cl vs d_mt) | 44.0% |
| Top-1 ranking disagreement (tie-aware) | **40.0%** (120 eligible, 0 tied) |

The CL--MT estimand distinction **transfers to SUMO and is more pronounced
than in the internal epidemic domain**: E4's internal top-1 ranking
disagreement was 2.36%, while here 40% of decision sets rank a different
signal programme best under the matched-history contrast than under the
cloned-state reference. The reason is the cumulative-waiting metric, which
retains the signal-control history a matched-history comparison folds into
the contrast. (Observed: normalised AE *decreases* with the horizon here,
the reverse of E2's growth — a metric/normalisation property, since the
shared continuation and the baseline IQR both grow with the horizon while
the historical-accumulation difference does not; not independently
attributed to a mechanism.)

## Result 2: the checker transfers to external manifests (E5 Layer 3)

A SUMO-specific `export_manifest` (which imports nothing from the checker,
consults no checker diagnostics, and reuses no E5 mutation generator) built
96 external audit manifests; the **frozen E5 checker** was run once against a
prospectively-defined oracle:

| Measure | Value |
|---|---|
| Status accuracy | 1.00 |
| False-positive rate on intact SUMO manifests | 0.00 |
| Negative-case detection | 1.00 |

This is the Layer-3 external test the E5 held-out score could not itself
provide. One honest outcome from the pilot strengthened the result: the
initial oracle over-expected FAIL on the `saveState_not_continuous` case for
MT/RS manifests, but MT/RS legitimately allow different pre-states, so the
frozen checker's PASS is correct — the checker was *more* correct than the
first oracle, which was corrected (the checker was not touched).

## Files

- `feasibility_spike/` — the replay-to-branch spike (5 gates) and its output.
- `confirmatory/e6_estimand_rows.jsonl` — CL/MT values, effects, AE per cell.
- `confirmatory/e6_layer3_records.jsonl` — every external manifest case:
  declared type, kind, expected and actual verdict.
- `confirmatory/aggregate_results.json` — boundary, AE, disagreement rates,
  Layer-3 scores. Byte-deterministic across re-runs (fixed SUMO seeds).
- `pilot/` — the plumbing run; not the headline.

## Claim boundary

Supports: the CL--MT distinction and the portable checker transfer to an
external imperative traffic simulator, with an external-divergent boundary
under cumulative waiting and a perfect Layer-3 checker result on
independently-exported manifests. Does not establish: real-world
traffic-policy correctness (uncalibrated, model-relative), generality beyond
the grid scenario and the cumulative-waiting metric (a public/upstream SUMO
scenario is the next external-realism step), or checker completeness on
manifests from sources other than this exporter.
