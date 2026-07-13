# SimContract Architecture (Phase-1 final)

One installable distribution, strict logical subpackages, machine-enforced
dependency rules, one composition root, one domain-neutral engine, multiple
contract-compliant domain plugins, stable evidence and replay interfaces,
CLI/experiments as entry points.

## Layers

```text
contracts     stable public boundary: protocols, frozen DTOs, versions
engine        domain-neutral orchestration: session loop, validation tier 1,
              seeding, preview requests, replay execution
controllers   experimental conditions behind RoleController
plugins       runtime registry + (dormant) entry-point discovery
domains       self-contained model plugins (stub + 2 research domains)
evidence      EvidenceSink implementation: hashed, replayable bundles
analysis      offline analyzers over BundleViews with lineage
llm           provider adapter behind the LLM port
application   use-case facade for every entry point
composition   the single wiring exception
cli           argparse front-end over the application facade
```

## Authority

Controllers propose or select; the engine validates syntactically and routes
degradation; only the domain adapter judges semantic admissibility and
produces the authoritative next state, both outcome branches, and the
`ResolutionReport` that evidence records verbatim (returned truth).

## Session lifecycle (normative)

create run → initialise adapter/state → per round: sample exogenous once →
per stage/role slot: observe → candidates → controller → syntactic validation
→ (semantic validation) → fallback events on failure → `adapter.step()` →
record round via the injected sink → finalise bundle → verify hashes →
optional replay → offline analysis.

The same path serves CLI runs, experiments, replay, scripted-human sessions,
and any future API. No second lifecycle may exist.

## Extension points

- new domain: `domains/<name>/**` + one composition line (target diff);
- new controller condition: one module in `controllers/` + composition;
- new analyzer: one module registered in the analysis registry;
- external domain (later): installed distribution + entry point, no core diff.
