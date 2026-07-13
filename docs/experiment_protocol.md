# Experiment protocol (E1–E6)

Every architectural claim maps to machine-generated evidence. Scripts live in
`experiments/`, read configs from `experiments/configs/`, and write bundles +
summaries under `results/` (git-ignored except `.gitkeep`).

| Id | Question | Script | Output |
|---|---|---|---|
| E1 | Are the boundaries real? | `e1_boundary_audit.py` | import-edge report; token-leakage report; composition-exception listing |
| E2 | Same seed ⇒ same artifact? | `e2_reproducibility.py` | rerun content-hash identity (LLM off), seed-change negative control, decision-replay equivalence per domain |
| E3 | Does one protocol run on all domains? | `e3_cross_domain.py` | same config executed on stub + both research domains, zero engine/analyzer diff, compliance suite pass |
| E4 | What do the controller conditions cost/buy? | `e4_controller_comparison.py` | per condition × domain × paired seed: invalid rate (by tier), fallback rate (by reason), source mix, branch divergence, latency; LLM conditions require a configured endpoint and are skipped (recorded as skipped) otherwise |
| E5 | Do the invariants hold on real bundles? | `e5_invariant_suite.py` | SC-I1..I7 checked over every bundle in a directory; pass/fail per invariant per bundle |
| E6 | Is analysis extension zero-touch? | `e6_analysis_extensibility.py` | built-in analyzers over heterogeneous bundles + registration of an extra analyzer with zero core diff |

Conditions vocabulary: `rule`, `random_valid`, `top_score`, `human_script`,
`bounded_llm`, `free_llm` (experiment-only). Paired seeds: identical
exogenous streams across conditions. Every table row in a paper cites the
`content_hash` of the bundles it was computed from.

Future: E7 external-plugin portability, E8 human interaction (blocked on the
data-governance requirements; see ADR 0006).
