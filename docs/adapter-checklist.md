# Adapter checklist: integrating a model

To run your own model behind SimContract's governed, replayable pipeline you
implement the `SimulationAdapter` contract
(`src/simcontract/contracts/adapter.py`, spec §5.2/5.3). The reference stub in
`src/simcontract/domains/reference_stub/` is the minimal working example; the
`energy_market_v1` and `epidemic_policy_v1` domains are fuller ones.

This checklist makes the requirements explicit. It describes the existing
contract; it does not claim any external model has been validated against it.

## Required attributes

- [ ] `domain_id: str` — unique domain identifier.
- [ ] `contract_version: str` — adapter contract version implemented.
- [ ] `roles: list[RoleSpec]` — the stakeholder role slots.

## Required methods

- [ ] `manifest` (property) → `DomainManifest` — declares roles, scenarios,
      metric catalog, observation policy, and action schema.
- [ ] `initial_state(scenario_id, seed)` → state — deterministic given the
      scenario and seed.
- [ ] `sample_exogenous(state, rng)` → `dict` — the shared exogenous inputs for
      the round, drawn from the provided RNG (feeds SC-I1: both counterfactual
      branches share these).
- [ ] `action_space(state, role_slot, rng, n)` → `list[Action]` — candidate
      actions offered to a controller.
- [ ] `preview(state, action, ctx)` → `Preview` — a non-committing look-ahead
      used during selection.
- [ ] `validate_semantic(state, action)` → `RejectionInfo | None` — domain-tier
      (semantic) validation; return `None` to accept.
- [ ] `step(state, actions, ctx)` → `Outcome` — advance the model; must be
      deterministic given `(state, actions, ctx)` and the seeded exogenous
      inputs.
- [ ] `default_action_provider` (property) → `DefaultActionProvider` with
      `action_for(state, role_slot, persona, ctx)` — the rule policy used for
      missing-action completion (SC-I2) and delegated to by the `rule`
      controller.

## Manifest and schema

- [ ] Domain manifest lists roles, scenarios, and personas.
- [ ] Metric catalog declares every metric the model emits (metrics not in the
      catalog are rejected).
- [ ] Observation policy defines what each role can see.
- [ ] Action schema defines the typed action envelope (drives engine-tier
      syntactic validation).

## Determinism and replay

- [ ] Given a fixed seed, `initial_state`, `sample_exogenous`, and `step` are
      reproducible (no wall-clock, no unseeded RNG, no network or external I/O
      inside `step`).
- [ ] The resolved action set is fully recorded so decision replay can
      re-execute the engine path and assert round-by-round equality
      (`REPLAY EQUIVALENT`).

## Invariants and compliance

- [ ] The adapter upholds execution invariants SC-I1..SC-I7 (dual branches from
      shared exogenous inputs, domain completion of missing actions, observable
      degradation, ordered stages, provenance completeness, selection
      auditability, failure accounting — see `docs/spec.md` §2).
- [ ] Runs the compliance suite green:

      ```bash
      python -m pytest tests/compliance -q
      ```

- [ ] A run produces a hashed bundle that `verify` and `replay` accept.

## Poor-fit model characteristics

An adapter is a poor fit for models that are nondeterministic or unseedable,
have no well-defined discrete `step`, require real-time or external I/O during
a step, or are inseparable from a GUI. Such models need adaptation (e.g. a
deterministic replay-to-branch reconstruction) before they can meet the replay
guarantee.
