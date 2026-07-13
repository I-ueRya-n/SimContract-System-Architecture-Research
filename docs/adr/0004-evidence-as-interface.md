# ADR 0004 — Evidence as a versioned interface behind an injected sink

Date: 2026-07-14 · Status: accepted

## Context

Evidence records are consumed by replay and analysis; they are a public
interface, not incidental logging. v0.1.0 had the engine return a
`SessionResult` and entry points call `write_bundle` directly, which coupled
entry points to the writer implementation.

## Decision

- Contracts define an `EvidenceSink` protocol (`record_round`,
  `record_decision`, `record_event`, `record_invocation`,
  `finalise(manifest, register)`); the engine emits to an injected sink while
  still returning the in-memory `SessionResult` for programmatic use.
- The concrete `BundleEvidenceWriter` (evidence layer) implements the sink
  and owns canonical hashing, per-file hashes, JSONL trace files,
  `metrics.csv`, and `report.html`.
- The evidence schema is versioned (`EVIDENCE_SCHEMA_VERSION`); removing or
  changing the meaning of a stable field is a breaking change.
- Canonical content identity excludes volatile fields (timestamps); file
  hashes are recorded separately.

## Consequences

Composition injects the writer; the engine never instantiates it. Analyzers
and replay consume `BundleView` (contracts) only. Four replay modes are
distinguished: rerun, decision replay, bundle verification, analysis replay.
