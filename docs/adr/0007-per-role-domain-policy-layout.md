# ADR 0007 — Per-role policy packages and `contract/` layout for research domains

Date: 2026-07-16 · Status: accepted

## Context

The Phase-1 research domains were laid out flat: contract YAML files sat at the
domain root, and every role's deterministic default policy and persona weights
lived in two shared modules (`defaults.py`, `personas.py`). That shape was
adequate while `rule` was the only default policy, but it does not scale to the
planned controller study, which needs per-role reactive NPC policies and
per-role archetype configuration. Concentrating every role's policy in one
module would make those additions collide in a single file and blur which role
owns which behaviour.

The domain/controller/validation specification supersedes the earlier flat
layout wherever the two conflict, and requires that new decisions be recorded in
new ADRs rather than by rewriting prior history. ADR 0003 (final Phase-1
structure) therefore stands as written; this ADR records the revision.

The change had to be provably behaviour-preserving, because the released
v0.3.0 artifact and the Paper 1 evidence depend on exact fixed-seed content
hashes.

## Decision

Research domains use the revised shape:

```text
domains/<domain>/
├── adapter.py, manifest.py, model.py, state.py, actions.py
├── contract/{action_schema,metric_catalog,observation_policy}.yaml
├── scenarios/
└── roles/<role>/{__init__,defaults,archetypes}.py
```

- Contract YAML moves into `contract/`; the adapter loaders and the
  `package-data` globs are updated so a non-editable install still ships them.
- Each role owns `defaults.py` (deterministic default policy, exposing
  `action_fields(state, role_slot, persona, ctx)`) and `archetypes.py`
  (`WEIGHTS`, `DEFAULT`).
- Domain-level `defaults.py` and `personas.py` remain as thin facades that
  dispatch to the role packages. The public API — `EnergyDefaults`,
  `EpidemicDefaults`, `weights_for`, `PERSONA_WEIGHTS`, `DEFAULT_PERSONA` —
  is unchanged, so adapters, `__init__`, and the composition root are untouched.
- `npc.py` is **not** created until reactive-NPC policies are implemented. An
  empty module would advertise a capability that does not exist.
- `reference_stub` stays flat. It exists only for contract testing and has one
  role; imposing per-role packages on it would be structure without semantics.
- The external-model adapter is explicitly **exempt**. It must satisfy the same
  public contract and evidence interfaces, but is not required to adopt this
  internal layout. Forcing every model into one internal template would make
  portability circular: it would demonstrate that models can be rewritten to a
  template, not that heterogeneous models can be integrated.

Migration gate: `engine`, generic `evidence`, generic `analysis`, and
`contracts` must be unchanged, and every fixed-seed content hash must be
identical before and after.

## Consequences

- Both controlled domains now share one final structure, so the controller study
  can add `roles/<role>/npc.py` without further restructuring, and the
  architecture work can add ablations and an external adapter independently.
- Verified behaviour-preserving on migration: 60 tests pass, the boundary audit
  reports zero forbidden imports and zero domain-vocabulary leaks, the energy
  baseline still reproduces `dd73a350…` and the epidemic baseline `efdfd27c…`,
  both replay 5/5 rounds equivalent, and `engine`/`evidence`/`analysis`/
  `contracts` are untouched.
- The released **v0.3.0** artifact keeps the flat layout. It remains the frozen
  Paper 1 artifact and the target of the independent reproduction; its hashes
  stay valid because the archive is immutable. This layout is the baseline for
  the next release onward. Evidence generated under the new layout must not be
  substituted into Paper 1's v0.3.0 numbers unless Paper 1 is itself re-pointed
  at a new release.
- Domain-level `defaults.py`/`personas.py` are now indirection. That is accepted:
  it keeps the adapter contract stable and confines the change to domain
  internals.
