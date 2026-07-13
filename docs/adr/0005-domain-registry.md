# ADR 0005 — Domain registry rules and dormant entry-point discovery

Date: 2026-07-14 · Status: accepted

## Context

Phase 1 registers built-in domains manually in the composition root. Future
phases may load third-party adapters from installed distributions. The
registry must already behave like a plugin boundary so that externalisation
is additive.

## Decision

`plugins/registry.py` implements the `DomainRegistry` protocol with hard
rules:

- duplicate domain ids are rejected (no silent override mode in Phase 1);
- contract-version compatibility is checked against `CONTRACT_VERSION`
  (same major version) at creation time using the adapter manifest;
- a factory that yields an adapter whose `domain_id` differs from the
  registered alias raises (substitution guard);
- listing order is deterministic (sorted);
- registration records plugin origin (`builtin` vs distribution name).

`plugins/discovery.py` defines the entry-point discovery flow
(`simcontract.domains` group → factory → manifest check → compatibility check
→ registration) with structured `PluginLoadError` isolation, but the
composition root does not invoke it until external adapters are specified
(consolidated spec §13.4); a load failure must never partially register a
domain.

## Consequences

Adding a built-in domain touches `domains/<new>/**` and one composition line.
Adding an external domain later touches no core code at all.
