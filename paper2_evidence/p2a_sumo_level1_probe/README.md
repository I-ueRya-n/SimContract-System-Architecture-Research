# SUMO Level-1 feasibility probe (exploratory; not confirmatory)

Protocol: `docs/protocols/p2a_sumo_level1_transfer.md` v1.0-pre. This probe
answers three questions asked *before* any SimContract adapter code was
written, to decide whether building one is worthwhile at all.

## Result: GO

| Question | Finding |
|---|---|
| Q1: checkpoint+reload == continuous execution? | No, diverges 6s after the split (waiting-time metric: 23.0 continuous vs 26.0 reload at t+30s). Vehicle *set* is identical throughout in both branches -- divergence is not from missing/extra vehicles. Most likely mechanism: the traffic light's phase-elapsed timer is not preserved by `saveState`/`loadState`. Not root-caused to SUMO source, unlike this project's own A1/A2 findings. |
| Q2: does a forced action change the outcome? | Yes, strongly. Default program: 26.0. Forced phase 0: 110.0. Forced phase 2: 48.0. |
| Q3: is checkpoint+reload deterministic across repeats? | Yes, exactly. `[26.0, 26.0, 26.0]` (default) and `[127.0, 127.0, 127.0]` (forced phase 1), three repeats each. |

Q1's finding does **not** block feasibility: SimContract's contract needs
`step()` to be deterministic given a state (Q3, holds) and actions to have
a real effect (Q2, holds). It never requires a checkpoint-based
continuation to match a hypothetical uninterrupted run. See protocol
Sec. 4a for the full reasoning and the resulting adapter-design
consequence (state is defined as the checkpoint itself, not as "what a
continuous run would have produced").

## Files

- `spike_checkpoint_determinism.py` -- Q1/Q2/Q3, run against `net_tls.xml`
  + `routes.rou.xml`.
- `spike_vehicle_set_diagnostic.py` -- follow-up check ruling out
  vehicle-insertion/removal as the Q1 divergence mechanism.
- `net_tls.xml`, `routes.rou.xml` -- the exact generated network/demand
  used (regenerable from `environment.json`'s recorded commands).
- `probe_stdout.log` -- raw run output.
- `environment.json` -- SUMO version/packages/licence, generation commands,
  software commit, probe configuration.

## Claim boundary

Supports: a GO decision to build a minimal `SumoTransferAdapter`, with the
Q1 boundary condition disclosed up front rather than discovered later.
Does not establish: adapter feasibility itself (no adapter code exists
yet), replay compatibility with SimContract's `BundleView`/`verify_bundle`,
or integration-effort figures. Those are the next step (protocol Sec. 8),
not yet run.
