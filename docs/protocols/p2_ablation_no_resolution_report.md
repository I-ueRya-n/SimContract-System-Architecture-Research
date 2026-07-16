# Paper 2 Architecture Ablation A1 — Withholding the Adapter-Returned ResolutionReport

**Protocol version:** 1.0 (frozen 2026-07-16; pilot on energy seeds 1-3 required no changes)
**Experiment type:** Controlled architecture ablation (paired, within-run)
**Primary paper:** Paper 2 — Cross-Domain Contract Portability
**Implementation:** `experiments/ablations/no_resolution_report.py` (explicit wrapper; no production code is modified)

## 1. Objective and proposition

Tests whether complete final decision provenance can be reconstructed when the
evidence path does not receive the adapter-returned `ResolutionReport`. The
architectural proposition: the adapter must return the final account of
resolution because only the adapter observes domain-default completion (its
default policy evaluated against current state inside `step()`), the final
applied action for non-accepted slots, and the final source classification.

Out of scope: controller decision quality; real-world model validity.

## 2. Research question and hypotheses

**RQ.** Can the final applied action and its provenance be reconstructed
accurately from engine-visible records alone (controller submissions,
two-tier validation results, fallback events, slot roster) when the
`ResolutionReport` is withheld?

**H0.** No measurable loss under the tested domains and injected cases.
**H1.** Measurable loss in at least one of: final applied action, final
source tag, completion status, completion reason, provenance completeness.
A result supporting H0 must be reported as evidence the report fields were
redundant under the evaluated architecture; partial results are reported
field by field, never as one binary conclusion.

## 3. Design

Paired within-run: every resolved role-decision slot yields (a) the intact
report (oracle) and (b) an ablated reconstruction computed from an
engine-visible view only. Both observe identical state, seeds, exogenous
inputs, submissions, and validation results, so the only difference is
access to adapter-returned resolution truth. Unit of analysis: the resolved
role-decision slot `(domain, scenario, run, round, role_slot)`; run-level
summaries are secondary.

**Ablated view may access:** controller condition per slot, submitted action
digests, engine-tier and adapter-tier intake rejections (both are returned
to the engine at intake), structured failure events, candidate digests, the
slot roster from the domain manifest.
**Ablated view must not access:** the `ResolutionReport`, `resolved_actions`
in `Outcome.meta`, adapter default policies, or branch outputs. A negative
access test asserts the ablated view contains none of these keys.

## 4. Injected cases (deviations from the generic draft are recorded here)

Per-slot deterministic schedules cycle the cases each role supports:

| case_id | Mechanism | Roles |
|---|---|---|
| `valid_action` | schema-valid, semantically legal submission | all |
| `missing_submission` | controller returns no action (`controller_absent`) | all |
| `controller_failure` | controller returns structured failure (`controller_exception`) | all |
| `syntactic_rejection` | field beyond schema range (engine tier) | all |
| `semantic_rejection` | energy: `maintenance_conflict` (generator; chosen because generator caps can equal the schema maximum, making `capacity_exceeded` unreachable for every slot); epidemic: `shares_not_normalised` (region_manager) | generator / region_manager |
| `domain_completion` | one deterministic slot per run left unassigned | rotating slot |

**Adaptations from the draft protocol, per repository reality:**
- `stale_action` is **not applicable**: adapters perform no re-rejection
  inside `step()`; accepted actions are applied as accepted.
- A raised controller exception is not contained by the engine (failure-as-
  data is the architectural pattern), so `controller_failure` is a scripted
  structured failure, not a raised exception.
- `accepted_submission` merged into `valid_action` (identical path).
- Each domain has two scenarios, not three; the seed count is raised to
  keep 120 confirmatory runs.

## 5. Run matrix and controlled factors

2 domains × 2 scenarios × 30 seeds (1..30) × 6 rounds = **120 runs**;
denominators are decision slots, reported overall and per domain, scenario,
case, and source tag. The `reference_stub` is excluded from primary results.
Held identical between conditions: repository commit, domain versions,
scenario files, seed policy, controller schedule, exogenous inputs,
evidence-schema version. LLM endpoints are not used.

## 6. Outcomes

**Primary:** complete provenance exact-match rate — a slot counts only if
*all* applicable fields match the oracle: final applied action, final source
tag, completion status, completion reason, rejection stage. An unresolved
field counts as a non-match.
**Secondary:** per-field accuracy (final action, source tag, completion
precision/recall, completion-reason accuracy, rejection-stage accuracy),
provenance completeness rate, unresolved-field rate, source-tag confusion
matrix, per-case breakdowns.
**Reporting:** counts, proportions, 95% Wilson intervals; absolute
percentage-point differences from the intact reference. No NHST.

## 7. Outputs

`results/p2_ablation_no_resolution_report/`: `protocol.sha256`,
`experiment_config.yaml` + `.sha256`, `environment.json`,
`per_slot_results.jsonl`, `aggregate_results.json`,
`source_tag_confusion.csv`, `case_breakdown.csv`, `domain_breakdown.csv`,
`run_manifest.json`, `README.md`. The wrapper's `--verify` mode recomputes
all aggregates from the per-slot records and asserts equality.

## 8. Claim boundary

Supports at most: adapter-returned resolution truth improves or is necessary
for complete decision provenance **under the evaluated SimContract domains,
scenarios, and failure conditions**. Does not establish: that every
simulation architecture requires such a report, that the schema is optimal,
domain external validity, controller quality, or generality beyond the
tested framework.

## 9. Execution sequence

Draft v0.1 → wrapper → one-domain pilot (excluded from confirmatory results)
→ record any protocol changes → freeze v1.0 → hash protocol + config →
120-run confirmatory matrix → verified result package → Paper 2 table and
discussion. The branch-separation ablation (A2) is formalised separately
afterwards.
