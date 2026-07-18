# SUMO Level-1 adapter compliance / evidence-generation smoke test

Protocol: `docs/protocols/p2a_sumo_level1_transfer.md` Sec. 8. Script:
`experiments/sumo_transfer/smoke_test.py`. This is the adapter feasibility
gate list, run once the adapter existed, before any confirmatory matrix.

## Result: ALL GATES PASS

| Gate | Result |
|---|---|
| Registered via the sanctioned seam (`composition.py`) | PASS |
| Starts and terminates cleanly (3-round `rule` run) | PASS |
| Distinguishable authoritative vs. applied outcomes | PASS -- `random_valid`, 10 rounds, seed 2: authoritative `[0,0,0,0,3,8,2,15,20,35]` vs. applied `[0,0,0,0,3,0,6,18,20,36]` (waiting-time seconds). `rule` alone cannot show this (applied == authoritative by construction, the same invariant A2 relies on for the other two domains), so this gate deliberately uses `random_valid`. |
| `replay_run` reproduces recorded evidence | PASS -- `engine/replay_executor.py`'s existing full fresh rerun (round 1 onward, recorded resolved actions, **zero code changes**) exactly reproduced the 3-round `rule` run: 3/3 rounds equal, 0 mismatches. This is the core Level-1 claim. |
| `verify_bundle` unmodified | PASS -- content hash and file hashes both verified, zero code changes. |
| Generic analyzer unmodified | PASS -- `Application.analyse_bundles` produced a report from the SUMO bundle with zero `analysis/` changes. |

## Integration effort (recorded prospectively, protocol Sec. 8/9)

| Measure | Result |
|---|---:|
| Upstream simulator | Eclipse SUMO 1.27.1 (EPL-2.0), installed from PyPI |
| Adapter-specific files | 7 (`__init__.py`, `adapter.py`, `defaults.py`, `manifest.py`, 3 contract YAML files) + 2 scenario assets (`net.xml`, `routes.rou.xml`, both `netgenerate`/`randomTrips.py`-generated, not hand-authored) |
| Adapter-specific LOC (`.py` only) | 307 |
| Experiment/smoke-test LOC | 110 (`experiments/sumo_transfer/smoke_test.py`) |
| Common-core files touched | 1 (`src/simcontract/composition.py`) |
| Common-core lines changed | 12 (one `try/except` registration block + one `domain_assets` branch) |
| `contracts/`, `engine/`, `analysis/` files changed | 0 |
| Contract exceptions | See "What is genuinely different" below |
| Deterministic/controlled runs | Passed (seed-controlled `traci.start(..., seed=N)`) |
| Evidence generation | Passed |
| Generic verification (`verify_bundle`) | Passed |
| Generic analysis | Passed |
| Replay | Passed via full fresh rerun; **not** via mid-run `saveState`/`loadState` (protocol Sec. 4a discloses this explicitly rather than claiming exact checkpoint replay) |

`composition.py`'s 12 changed lines are the same shape and size as what
`energy_market_v1` and `epidemic_policy_v1` each already required when they
were added -- the protocol (Sec. 2) argues this is the project's own
pre-existing, sanctioned per-domain extension seam (ADR 0001/0005), not a
common-core modification in the sense the claim cares about.

## What is genuinely different from a pure-function domain (disclosed, not hidden)

- **State is not a serializable value carrying full simulation truth.**
  `state`/`state_next` is a lightweight round-tracking token; the live
  SUMO connection is held internally by the adapter instance. This works
  because `AdapterRegistry.create()` constructs a fresh adapter instance
  per `run_session()`/`replay_run()` call and `SessionRunner.run()` always
  executes one full sequential pass -- documented in `adapter.py`'s
  module docstring, not assumed silently.
- **No adapter teardown hook exists in `SimulationAdapter`.** Every
  existing domain is a pure function with nothing to release; SUMO needs
  its connection closed. Handled via `__del__` (object finalization),
  disclosed as a real architectural gap this adapter exposes rather than
  a common-core change to add a lifecycle hook.
- **`preview()` is a disclosed approximation** (last-observed metric, not
  a forward simulation) -- never used for a committed decision by the
  `rule`/`random_valid` conditions this smoke test exercises.
- **`sample_exogenous()` returns `{}` every round** -- SUMO's own arrival
  process is fixed by the seed passed once at `initial_state()`, so there
  is no separate per-round exogenous draw the way `energy_market_v1` and
  `epidemic_policy_v1` have one.
- **The authoritative branch is computed via a local, single-round
  `saveState` fork**, explicitly not used to carry the real run forward
  (protocol Sec. 4a/6) -- because the probe found checkpoint reload
  repeatable but not equivalent to uninterrupted execution beyond ~5
  simulated seconds.

## Claim boundary

Supports: frozen SimContract contracts and evidence interfaces (`engine/`,
`analysis/`, `contracts/`, `evidence/replay_bundle.py`,
`engine/replay_executor.py`) wrap an external, non-co-designed simulator
with a single 12-line, same-shape-as-precedent addition to the composition
root, for one minimal controllable scenario, on this machine. Does not
establish: realistic traffic behaviour, calibration validity, scaling to a
real network, checkpoint-continuation fidelity beyond what the probe
already discloses, or generality to other stateful external simulators.
