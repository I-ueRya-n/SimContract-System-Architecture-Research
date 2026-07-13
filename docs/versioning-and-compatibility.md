# Versioning and compatibility

## Independently versioned

| Thing | Where |
|---|---|
| contract version | `contracts/versioning.py` (`CONTRACT_VERSION`) |
| evidence schema version | `contracts/versioning.py` (`EVIDENCE_SCHEMA_VERSION`) |
| core/engine version | distribution version (`pyproject.toml`) |
| domain version | each `DomainManifest.domain_version` |
| action/metric/observation schema versions | domain YAML `schema_version` fields |
| scenario version | scenario files under `domains/*/scenarios/` |
| controller/prompt version | controller `PROMPT_VERSION` constants, recorded per invocation |
| analyzer version | each `AnalyzerSpec.version` |
| external upstream model version | `UpstreamModelProvenance` in the manifest |

## Rules

- A domain manifest declares its supported contract version; the registry
  accepts it only when the major version matches `CONTRACT_VERSION`
  (`is_compatible()` in `contracts/versioning.py`).
- Breaking contract changes ⇒ major bump. Adding optional manifest fields is
  backward compatible. Removing/repurposing a stable evidence field is
  breaking (bump `EVIDENCE_SCHEMA_VERSION` major).
- Every bundle manifest snapshots the versions needed to identify its
  execution environment (contract, adapter, evidence schema, prompt versions
  via invocation records).
- CI gate: compliance suite runs every registered domain against the current
  contracts on every build; when external plugins exist, supported plugin
  versions are matrix-tested against each supported contracts release.
