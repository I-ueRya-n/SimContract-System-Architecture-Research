# ADR 0003 — Final Phase-1 structure: controllers/ and plugins/ as first-class layers

Date: 2026-07-14 · Status: accepted

## Context

The consolidated architecture/packaging specification separates four questions
(repository layout, installable distribution, runtime plugin registration,
interaction phases) and prescribes a normative Phase-1 tree in which concrete
controllers and the runtime registry are their own layers rather than engine
submodules. Our v0.1.0 tree kept both inside `engine/`.

## Decision

Adopt the consolidated layout:

- concrete controllers move from `engine/controllers.py` to a
  `controllers/` package (one module per experimental condition); the engine
  retains only the `RoleController` protocol dependency (contracts);
- the registry moves from `engine/registry.py` to `plugins/registry.py`,
  implementing the `DomainRegistry` protocol (contracts); entry-point
  discovery lives in `plugins/discovery.py` but stays dormant until external
  adapters are specified;
- a use-case facade `application.py` fronts the engine for all entry points.

## Deviations from the illustrative layout (accepted here)

1. **ADR numbering** is append-only in this repository; the consolidated
   spec's illustrative filenames (0002-contract-boundaries etc.) are not
   retro-fitted. ADR 0002 remains "shared exogenous inputs".
2. **`metrics.csv`** is used instead of `metrics.parquet` (stdlib-only
   dependency policy for Phase 1; the spec allows either).
3. **Interactive `human`** (CLI play) is kept alongside the required
   `human_script` scripted condition; both implement the same protocol.

## Consequences

Engine no longer exports controller classes; composition wires controllers.
The AST dependency audit gains layers (`controllers`, `plugins`,
`application`) and a domain-token leakage check for all core layers.
