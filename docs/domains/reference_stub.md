# reference_stub

Deterministic contract and resilience testbed — **not a research domain**.

One role (`operator`), one stage. State: a single bounded scalar
(`value ∈ [−100, 100]`). Action: `delta ∈ [−10, 10]`. Transition:
`value' = clamp(value + delta + drift)` with a seeded drift as the exogenous
input. Metrics: `value`, `value_abs`.

Purpose: exercising every contract seam (schemas, candidates, preview,
semantic validation, branches, resolution report, default policy) with a
transition simple enough that expected outputs are hand-computable; failure
injection and negative tests target this stub first.

Provenance: designed for this repository; no upstream model.
