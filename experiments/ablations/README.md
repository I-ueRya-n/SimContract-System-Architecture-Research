# Architecture ablations

Each ablation disables exactly one mechanism, re-runs a fixed-seed protocol, and
records the resulting failure signature. The purpose is to show *why* a
mechanism matters, not merely that it exists.

Candidates (one file per ablation):

- `no_resolution_report.py` — engine infers provenance instead of the adapter
  returning it; expected: provenance becomes inference, source tags unverifiable.
- `no_branch_separation.py` — drop the authoritative counterfactual branch;
  expected: divergence no longer attributable to the decision rather than sampling.
- `no_semantic_validation.py` — skip adapter-tier validation; expected: invalid
  actions reach `step()`.
- `no_replay_verification.py` — skip replay equality assertion; expected: silent
  divergence goes undetected.

Every ablation must report: what was disabled, the fixed seed, the observed
failure, and what the intact mechanism prevents.
