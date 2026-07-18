# Paper 2B-E5 — counterfactual-integrity checker + portable audit manifest

Protocol: `docs/protocols/p2b_e5_integrity_checker.md` v1.0 (SHA-256 prefix
`cda077504299faf6`; checker code frozen at
`docs/protocols/p2b_e5_checker_code.sha256`). Script:
`experiments/paper2b/e5_integrity_checker.py`. Regression tests:
`tests/unit/test_p2b_e5_checker.py`. Development (pilot) run under `pilot/`,
held-out under `heldout/`.

## What E5 contributes

E0--E4 diagnose the estimand mismatch; E5 turns Paper 2B into a reusable
**method**. Given an artifact and a *declared* estimand, a portable checker
returns `PASS / WARN / FAIL / UNSUPPORTED`, and on `FAIL` reports the
estimand the evidence actually supports plus a safe claim wording. The
checker (`check`) is pure-stdlib and imports nothing from SimContract — it
reads a portable audit manifest — so it is reusable on external artifacts
(RO-Crate-style portability; Open Provenance Model identity sections;
reflexion-model declared-vs-actual conformance).

## Evaluation (three layers, anti-circularity)

Corpus: 80 intact manifests (2 domains × 5 seeds × 2 rounds × 4 estimand
types) built from **real cloned-continuation identity hashes**.

- **Layer 1 (development, structural mutations):** used while building the
  checker; the pilot exposed a non-estimand-aware oracle (fixed), after
  which development precision/recall/F1 = 1.0. The checker was then **frozen**
  (code hash recorded) before Layer 2.
- **Layer 2 (held-out, semantic mutations):** eight *valid-looking but wrong*
  families, frozen by the protocol hash and executed **once** against the
  frozen checker. Each family is applied to all four estimand types with an
  **estimand-aware oracle** — a defect must be flagged on the types where the
  identity is required and must stay `PASS` where it is not — so the result
  measures specificity, not only recall.
- **Layer 3 (external manifests):** deferred to 2B-E6, where
  independently-sourced manifests exercise the checker.

## Held-out result

| Measure | Value |
|---|---|
| Precision | 1.00 |
| Recall | 1.00 |
| F1 | 1.00 |
| Exact-verdict-class accuracy | 1.00 |
| False-positive rate on intact manifests | 0.00 |
| Held-out semantic families detected | 8 / 8 |

All eight semantic families (`schedule_covers_H-1`,
`continuation_policy_hash_differs`, `divergence_before_decision`,
`shared_branch_id`, `metric_unit_changed`, `mixed_model_versions`,
`resampled_declared_matched`, `inconsistent_lineage`) are detected with the
correct verdict class and correct specificity (no over-flagging on estimand
types where the mutated identity is not required).

## Honest framing (do not over-read the 1.00)

The checker is **specification-driven**: it encodes the SR/CL/MT/RS
claim-compatibility rules, and both mutation layers were authored alongside
it. A perfect held-out score therefore reflects **specification coverage for
the SR/CL/MT/RS classes** — the frozen checker generalises from structural
(development) to semantic (held-out) defects within its specification — not
proof of a universally correct checker. The decisive independent test is
Layer 3 (externally-authored manifests), deferred to E6. Per the
mutation-testing discipline, the checker was not edited and re-run after the
held-out set; had held-out revealed a defect, this run would have become
development evidence and a fresh held-out set defined.

**Known scope limitation (disclosed, not fixed post-freeze):** the schedule
`covered_rounds` requirement is enforced strictly for local estimands
(SR/CL), where it is most critical; the MT/RS coverage check is looser.
Tightening MT/RS coverage strictness is future work and would be a
manifest-schema/checker v1.1 change, not a silent edit to the frozen v1.0.

## Files

- `heldout/e5_records.jsonl` — one record per (manifest, mutation): expected
  and actual verdict, supported estimand, reason.
- `heldout/aggregate_results.json` — precision/recall/F1, exact-verdict-class
  accuracy, false-positive rate, per-family accuracy.
- `pilot/` — the development-mutation run; not the headline.

## Claim boundary

Supports: a portable, specification-driven integrity checker that classifies
a recorded counterfactual comparison against its declared estimand,
evaluated by development and held-out mutation families with precision and
false-positive reporting and correct specificity. Does not establish:
performance on independently-authored external manifests (Layer 3, E6), nor
completeness of the claim-compatibility specification beyond SR/CL/MT/RS.
