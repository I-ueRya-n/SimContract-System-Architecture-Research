# Positioning

SimContract is **not** a modelling library and does not compete with
agent-based modelling frameworks. It sits at a different layer: it governs how
controllers (human, rule-based, or LLM-assisted) make decisions against a
simulator held authoritative behind an enforced adapter contract, and it turns
every run into a hashed, replayable, verifiable evidence bundle.

## Complementary frameworks

- **[Mesa](https://github.com/projectmesa/mesa)** — a Python agent-based
  modelling framework: model/agent primitives, schedulers, grid/network space,
  data collection, and browser visualization. Excellent for *building* an ABM.
- **[GAMA](https://gama-platform.org/)** — a spatially explicit ABM platform
  (GAML): strong GIS support, large populations, and rich visualization.

These are modelling toolkits. SimContract is a **decision-governance and
evidence layer** for simulation-based *experiments*. The two are complementary:
a model authored in Mesa, GAMA, an imperative traffic simulator, or plain
Python can in principle be placed behind the SimContract adapter contract to
gain governed controllers, two-tier validation, provenance, replay, and
verification.

## What SimContract adds

Capabilities that, in a general modelling framework, are usually assembled
per-project — SimContract composes them into a single tested, mechanically
enforced *execution-and-evidence contract*:

- **Controller governance** — human, rule, ranked, and LLM controllers pass
  through the same two-tier (syntactic + semantic) validation path; invalid
  actions are rejected or completed by a domain default, never silently
  applied.
- **Simulator authority** — the domain model, not the controller or the LLM,
  is the source of truth for outcomes.
- **Provenance and replay** — every run emits a content-hashed evidence bundle;
  decisions replay through the engine and are asserted equal round by round.
- **Verification and lineage** — bundle hashes are re-checkable without
  re-execution, and offline analyzers carry lineage back to the exact input
  bundle.

The point is not that Mesa or GAMA "cannot do" these things — they can be built
there — but that SimContract provides them as a reusable, audited contract
rather than as bespoke per-study scaffolding.

## Honest boundary

SimContract does **not** provide spatial/GIS primitives, agent-scheduling
libraries, real-time execution, distributed simulation, or visualization. Its
two research domains are controlled, literature-informed testbeds, not
externally validated forecasting models (see `docs/claim_boundary.md`).
Integration of an external simulator (e.g. Mesa/GAMA/SUMO) behind the adapter
contract is a **prospective adoption path**, not a capability implemented or
evaluated in this release.
