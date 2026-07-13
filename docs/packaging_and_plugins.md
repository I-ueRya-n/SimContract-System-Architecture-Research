# Packaging and plugin discovery

## Terms (used consistently)

- **Source repository**: this Git repo (`SimContract/`).
- **Distribution**: the installable artifact — `pip install simcontract`.
- **Import package**: `src/simcontract/` (`import simcontract`).
- **Subpackage**: `simcontract.contracts`, `.engine`, … logical layers.
- **Domain plugin**: one self-contained domain behind the contracts
  (`reference_stub`, `energy_market_v1`, `epidemic_policy_v1`).
- **Runtime registry**: in-memory id → adapter-factory mapping (not PyPI).
- **Package registry**: PyPI or equivalent (future external adapters).
- **Composition root**: `composition.py`, the only concrete-import site.

There is deliberately no top-level `package/` directory: `src/simcontract/`
is the import package and `pyproject.toml` defines the distribution.

## Phase 1: one distribution

One wheel contains contracts, engine, controllers, plugins, evidence,
analysis, llm, built-in domains, application facade, and CLI. Logical layer
separation is machine-enforced inside the single wheel; a single distribution
does not invalidate layer independence.

## Registry rules (see ADR 0005)

Duplicate ids rejected · contract-version compatibility checked ·
substitution guard (factory must produce the registered `domain_id`) ·
deterministic listing · origin recorded · load failures are structured
`PluginLoadError`s and never partially register.

## Future external discovery (defined, dormant)

```toml
[project.entry-points."simcontract.domains"]
external_model_v1 = "their_package.module:create_adapter"
```

Flow: installed distribution → entry-point metadata → factory loaded →
manifest checked → contract compatibility checked → registry registration.
Composition does not invoke discovery until external adapters are specified.

## When to split packages

Only after: contracts v1 stable · two built-in domains pass compliance ·
a third-party adapter is planned · external contributors need
contracts-only installs. Target monorepo shape then:
`packages/simcontract-contracts`, `-core`, `-domain-*`, meta-package,
`apps/api`, `apps/web` — all adapters around the same scientific core.
