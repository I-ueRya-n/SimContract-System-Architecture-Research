# Paper 2A phase-level overhead — result package (confirmatory)

Controlled instrumentation (not staged feature disabling): every phase is
measured by wrapping real, unmodified production objects in timing proxies
that delegate unchanged. 360 runs (2 domains x 2 scenarios x 3 conditions x
30 seeds x 6 rounds); semantic transparency verified (instrumented run
produces the same content hash as production `Application.run_session`);
feasibility probe and its two corrections documented in the protocol
(`docs/protocols/p2a_phase_overhead.md`, S4a/S5a).

Regenerate: `PYTHONPATH=src python3 experiments/overhead/phase_overhead.py`
Probe:      `PYTHONPATH=src python3 experiments/overhead/phase_overhead.py --probe`

Headline: at this workload scale (~30ms per 6-round run), `T_candidate_generation`
(action_space + preview per candidate) is the largest attributed phase
(37-54% of wall-clock across domains/runs), ahead of resolution, hashing,
and validation combined (each under 4%). The residual (`T_branch_recording`:
RoundRecord packaging, seed/rng derivation, metric-catalog validation, and
proxy dispatch overhead) is 39-56% and is reported as an explicit, named
bucket rather than concealed. The instrumentation tax itself, measured on a
counterbalanced 20-pair subsample after a real order-confound and a
non-comparable-call-path confound were found and fixed (protocol S4a/S5a),
is +0.94ms median against a 3.83ms noise floor -- not confidently
distinguishable from zero at this scale. Replay and verify (measured
separately, not summed into T_total) are both sub-40ms per bundle; see
`replay_verify.csv`.
