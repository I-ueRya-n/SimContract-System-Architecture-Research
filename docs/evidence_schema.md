# Evidence schema (v1)

`EVIDENCE_SCHEMA_VERSION = "1.0.0"`. Evidence is a versioned public
interface; removing or changing the meaning of a stable field is a breaking
change. Analyzers and replay consume `BundleView` only.

## Bundle layout

| File | Content | Stability |
|---|---|---|
| `manifest.json` | run/domain/contract/adapter/evidence-schema versions, seeds, rounds, conditions, personas, config digest, `content_hash`, `file_hashes` | stable |
| `config.snapshot.json` | resolved run configuration as executed | stable |
| `domain_manifest.json` | serialized `DomainManifest` of the active domain | stable |
| `rounds.json` | per-round: `round_no`, `round_seed`, `exogenous_digest`, `system_metrics`, `branches.authoritative/applied`, `resolution` (returned truth), `resolved_actions` | stable |
| `decisions.jsonl` | one `DecisionRecord`/line: round, role, slot, condition, persona, candidate digests, scores, selected digest, source tag, rationale, state digest (SC-I6) | stable |
| `fallback_events.jsonl` | one `FailureRecord`/line: round, slot, stage, family, reason, detail (SC-I3) | stable |
| `llm_invocations.jsonl` | one `InvocationRecord`/line: model id, prompt version + digest, temperature, tokens, latency, retries, response digest | stable |
| `register.json` | failure families × reasons with explicit denominators (SC-I7) | stable |
| `metrics.csv` | long form: `round,branch,metric,value` | stable |
| `report.html` | human-readable summary | informative |

## Canonical identity

`content_hash` = SHA-256 over canonical JSON (sorted keys, compact
separators) of manifest + rounds + decisions + events + invocations +
register, with `content_hash`, `file_hashes`, and `created_at` nulled before
hashing. Per-file SHA-256 hashes are recorded separately in the manifest.
Wall-clock timestamps never enter the canonical identity.

## Replay modes

1. **rerun** — execute again from configuration + seed; LLM-off runs must be
   bit-identical (same `content_hash`).
2. **decision replay** — re-execute recorded `resolved_actions` through the
   model via the engine path; assert metric and branch equality per round.
3. **bundle verification** — recompute file hashes + content hash without
   executing.
4. **analysis replay** — rerun analyzers against frozen bundles; lineage
   records tie every output row to input bundle hashes.
