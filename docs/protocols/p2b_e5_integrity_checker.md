# Paper 2B-E5 — Counterfactual-Integrity Checker + Portable Audit Manifest

**Protocol version:** 1.0 (frozen 2026-07-18; pilot findings §8 are
implementation-only. The checker rules and the held-out mutation families
are frozen by this document's hash BEFORE the held-out set is executed.)
**Experiment type:** Reusable static checker + mutation-based evaluation.
**Primary paper:** Paper 2B. **Implementation:**
`experiments/paper2b/e5_integrity_checker.py`.
**Depends on:** E0--E4 (the estimand distinction the checker audits).

## 1. Objective

Turn Paper 2B from a diagnosis into a reusable research-software method:
given an artifact and a **declared** estimand, decide what estimand the
evidence actually supports, whether the required identities are present and
consistent, what is missing or contradictory, and what claim wording is
defensible. Output is one of `PASS`, `WARN`, `FAIL`, `UNSUPPORTED`.

## 2. Literature gate (narrow; classic + recent, done before this freeze)

Six sources web-verified 2026-07-18, each grounding a design decision:

| Source | Grounds |
|---|---|
| Moreau et al.\ 2011, Open Provenance Model (classic) | the manifest's provenance/identity sections |
| Soiland-Reyes et al.\ 2022, RO-Crate (recent) | a PORTABLE (non-bundle-specific) manifest |
| Murphy, Notkin \& Sullivan 2001, reflexion models (classic) | declared-vs-actual conformance = the checker's core analogy |
| DeMillo, Lipton \& Sayward 1978, mutation testing (classic) | fault-seeding evaluation |
| Papadakis et al.\ 2019, mutation survey (recent) | development / held-out family split, best practices |
| Sadowski et al.\ 2018, static analysis at Google (recent) | report precision + false-positive rate, not just recall |

## 3. Portable audit manifest v1.0

Schema version `p2b-audit-manifest/1.0`. Sections (all required):
`declared_estimand` (type, decision_point, horizon), `model_identity`
(simulator, factual/alternative model + metric-catalogue hashes),
`state_identity` (factual/alternative pre-decision state hashes, shared
parent checkpoint hash), `exogenous_identity` (schedule_hash, covered_rounds,
resampled), `branch_identity` (factual/alternative branch ids, divergence
round, ancestry hashes, factual/alternative continuation-policy hashes),
`provenance` (proposed/final actions, source tag, continuation-policy hash,
completion reason). The manifest is canonical-JSON serialisable and
content-hashed. The checker (`check`) is **pure-stdlib and imports nothing
from \sys{}** --- it reads a manifest dict --- so it is reusable on external
artifacts; only the intact-corpus generator touches \sys{} to capture real
identity hashes.

## 4. Claim-compatibility rules (what each declared estimand requires)

| Declared estimand | Required identities |
|---|---|
| `one_step_local` (SR) | shared clone (factual = alternative = parent), schedule hash, not resampled, coverage = 1 |
| `cloned_local_h_step` (CL) | shared clone, schedule hash, not resampled, coverage = H, identical continuation policy across branches |
| `matched_history_contrast` (MT) | different pre-states allowed, schedule identity declared (hash present, not resampled), identical continuation policy |
| `resampled_contrast` (RS) | separate streams (resampled = true) |

Across all types the checker also requires model and metric-catalogue
identity between branches, distinct factual/alternative branch ids,
divergence not earlier than the declared decision, and consistent combined
lineage.

## 5. Output semantics (frozen)

- **PASS** — every mandatory identity for the declared estimand is present,
  consistent, and non-contradictory, and recommended provenance is present.
- **WARN** — mandatory support present, but a recommended (non-critical)
  provenance field is missing (`proposed_action`, `final_applied_action`,
  `source_tag`). WARN never masks a missing parent state or a mismatched
  schedule.
- **FAIL** — the artifact and estimand are recognised but a mandatory
  identity is missing, contradictory, covers the wrong horizon, has
  inconsistent branch ancestry, a differing continuation policy, or a
  differing model/metric identity. On FAIL the checker also reports the
  **supported** estimand (e.g. a local claim whose branches are not a shared
  clone actually supports a matched-history contrast) and a **safe wording**.
- **UNSUPPORTED** — the checker cannot evaluate: unknown schema version,
  unknown estimand type, or missing top-level sections. UNSUPPORTED is not a
  false negative.

## 6. Three-layer evaluation (anti-circularity)

Per Papadakis best-practices and the programme's own discipline:

- **Layer 1 --- development mutations** (structural: dropped/flipped fields).
  Used while building the checker; NOT a headline number. The checker is
  frozen after Layer 1 passes.
- **Layer 2 --- held-out mutations** (semantic: valid-looking but wrong),
  frozen by this protocol's hash and executed ONCE against the frozen
  checker. If Layer 2 reveals a checker defect, the checker is NOT edited and
  re-run as held-out; Layer 2 v1 becomes development evidence and a fresh
  held-out v2 would be defined --- this run is reported as-is.
- **Layer 3 --- external / independently authored manifests.** Deferred to
  2B-E6 (external simulator replication), where manifests from a different
  source exercise the checker.

Both mutation layers use an **estimand-aware oracle**: a mutation that breaks
a required identity for the manifest's declared estimand must be flagged, but
on an estimand type where that field is not required it must stay PASS ---
this measures specificity (no over-flagging, Sadowski), not only recall.

## 7. Frozen held-out mutation families (Layer 2)

Eight semantic families, each applied to every intact manifest with the
estimand-aware oracle: `ho_schedule_covers_H_minus_1`,
`ho_continuation_policy_hash_differs`, `ho_divergence_before_decision`,
`ho_shared_branch_id`, `ho_metric_unit_changed`, `ho_mixed_model_versions`,
`ho_resampled_declared_matched`, `ho_inconsistent_lineage`. The generator,
its applicability map, and the expected-verdict oracle are frozen with this
document.

## 8. Development pilot findings (implementation-only; checker then frozen)

Intact corpus: 80 manifests (2 domains x 5 seeds x 2 rounds x 4 estimand
types) built from real cloned-continuation identity hashes. Development
mutations (7 families x 80): the pilot's first pass exposed a
non-estimand-aware oracle (it expected FAIL for a mutation on an estimand
type where the mutated field is not required). Corrected to the estimand-
aware oracle above; after the correction, development precision, recall, F1,
exact-verdict-class accuracy, and UNSUPPORTED accuracy are all 1.0 with 0%
false positives on intact manifests. The checker is frozen at this point;
the held-out set (§7) is executed once against it.

## 9. Primary metrics

Reported for the held-out set (Layer 2), not Layer 1: defect-detection
precision, recall, F1; exact-verdict-class accuracy (did the verdict match
the expected class?); false-positive rate on intact manifests;
UNSUPPORTED-detection accuracy; and per-family accuracy. A checker that
always returns FAIL is explicitly excluded by requiring a low false-positive
rate on intact manifests alongside recall.

## 10. Claim boundary

Supports: a portable, specification-driven checker that classifies a
recorded counterfactual comparison against its declared estimand, evaluated
by development and held-out mutation families with precision and
false-positive reporting. Does not establish: performance on
independently-authored external manifests (Layer 3, deferred to E6), nor
that the claim-compatibility specification is complete for estimand classes
beyond SR/CL/MT/RS.
