# ADR 0006 — Headless core first; interaction is a controller mode

Date: 2026-07-14 · Status: accepted

## Context

The research questions of Papers 1–3 (contract portability, reproducibility,
bounded-AI validity) are answerable without a frontend, HTTP server,
database, or WebSocket. Human interaction only becomes a requirement when a
research question depends on human participation.

## Decision

- The scientific execution core runs headless: CLI and experiment scripts are
  the only Phase-1 entry points, both through the `application.py` facade.
- Human participation is a controller mode behind the same `RoleController`
  protocol: `human_script` (scripted, reproducible, used in experiments) and
  interactive `human` (CLI play). Neither bypasses the two validation tiers.
- A future API/UI must call the same application facade and must not
  implement a second simulation lifecycle.
- Human-participant *research data* collection is out of scope until the
  data-governance requirements of the consolidated spec §25 are satisfied;
  demo logging carries no participant analytics.

## Consequences

Papers describe the system as a simulation-based decision experiment
architecture that is human-ready, not as a validated serious game. Phase-2+
layers (API, UI shell, domain UI plugins) are adapters around this core.
