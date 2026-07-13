# Dependency rules (machine-enforced)

Enforced by `tests/dependency/test_dependency_rules.py` (AST audit) and
`tests/dependency/test_token_leakage.py`. A forbidden edge fails the build.

| Layer | MAY import | MUST NOT import |
|---|---|---|
| `contracts` | stdlib only | any other `simcontract.*` layer |
| `engine` | `contracts`, engine-internal | domains, controllers, plugins, evidence impl, analysis, llm, application, composition |
| `controllers` | `contracts`, `llm` port, controller-internal | domains, engine, evidence impl, analysis |
| `plugins` | `contracts` | concrete domains, engine internals |
| `domains.*` | `contracts`, own package, stdlib+PyYAML | engine, other domains, evidence impl, analysis, llm |
| `evidence` | `contracts`, stdlib | domains, engine, analysis |
| `analysis` | `contracts`, stdlib | engine, domains, evidence writer internals |
| `llm` | `contracts`, stdlib | everything else |
| `application` | engine public, plugins, evidence, analysis, contracts | concrete domain classes |
| `composition` | everything concrete | — (nothing imports it except entry points) |
| `cli` / `experiments` | `application`, `composition`, contracts | engine privates, domain formulas |

## Token leakage rule

Core layers (`contracts`, `engine`, `controllers`, `plugins`, `evidence`,
`analysis`, `llm`, `application`) must contain no domain vocabulary
(generator/carbon/renewable/epidemic/vaccin/seir/infection/...). A new domain
must never require adding a domain field name or conditional to core code.

## Composition-root exception

`composition.py` alone imports concrete domains; the audit whitelists exactly
this module. Entry points (`cli.py`, `experiments/*`) import the facade or
the composition entry function, never domain modules.
