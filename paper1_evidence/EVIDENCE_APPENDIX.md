# Paper-1 evidence appendix (regenerable)

Produced by `experiments/paper1_evidence_pack.py` from executed runs of SimContract. All tables are machine-generated; the CSV/JSON siblings are the citable artifacts.

Test suite: `60 passed in 0.81s`

### E-1 Contract-compliance matrix (per domain)

| domain | protocol_satisfied | manifest_valid | candidates_syntactic_valid | candidates_semantic_valid | both_branches_emitted | resolution_report_complete | metrics_in_catalog | replay_equivalent | default_action_completion |
|---|---|---|---|---|---|---|---|---|---|
| reference_stub | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| energy_market_v1 | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| epidemic_policy_v1 | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |


### E-2 Determinism: per-item semantic hash identity (two independent runs, same seed)

| domain | item | run_A | run_B | identical |
|---|---|---|---|---|
| energy_market_v1 | content_hash | a94da2108f80470c | a94da2108f80470c | Yes |
| energy_market_v1 | candidate_pool_digest | 8c7f57d3b0e0f32e | 8c7f57d3b0e0f32e | Yes |
| energy_market_v1 | exogenous_digest | a002f37cf1727a87 | a002f37cf1727a87 | Yes |
| energy_market_v1 | metrics_digest | a440d82397c1da1b | a440d82397c1da1b | Yes |
| energy_market_v1 | branches_digest | a62080d3fbe7acf6 | a62080d3fbe7acf6 | Yes |
| epidemic_policy_v1 | content_hash | 828a50e73d4de617 | 828a50e73d4de617 | Yes |
| epidemic_policy_v1 | candidate_pool_digest | dfb1494ddd0722fc | dfb1494ddd0722fc | Yes |
| epidemic_policy_v1 | exogenous_digest | 45b3604cc30b7c24 | 45b3604cc30b7c24 | Yes |
| epidemic_policy_v1 | metrics_digest | 1b915aa0257eec4e | 1b915aa0257eec4e | Yes |
| epidemic_policy_v1 | branches_digest | 8f42cf01a7b629f8 | 8f42cf01a7b629f8 | Yes |


### E-3 Replay equivalence + bundle verification

| domain | rounds_compared | equal_rounds | replay_equivalent | hash_verified | files_verified |
|---|---|---|---|---|---|
| energy_market_v1 | 5 | 5 | Yes | Yes | Yes |
| epidemic_policy_v1 | 5 | 5 | Yes | Yes | Yes |


### E-4 Failure containment (injected)

| case | rejected | rejection_tier | completed_by_default | run_completed |
|---|---|---|---|---|
| invalid_action (out of range) | Yes | engine_syntactic | Yes | Yes |
| semantic_invalid (shares!=1) | Yes | adapter_semantic | Yes | Yes |
| missing_controller (unassigned) | n/a | n/a | Yes | Yes |


### E-5 Dual-branch divergence (energy, mixed conditions)

| round | authoritative_clearing_price | applied_clearing_price | renewable_share_auth | renewable_share_applied | regulator_source |
|---|---|---|---|---|---|
| 1 | 84.0 | 92.938 | 0.4148 | 0.4148 | top_score |
| 2 | 84.0 | 110.197 | 0.2394 | 0.2394 | top_score |
| 3 | 84.0 | 95.032 | 0.4408 | 0.4408 | top_score |
| 4 | 84.0 | 92.675 | 0.4039 | 0.4039 | top_score |
| 5 | 84.0 | 104.869 | 0.4994 | 0.4994 | top_score |


> Claim boundary: all values are architecture / reproducibility evidence and model-relative branch comparison. No external behavioural or predictive validity is claimed.