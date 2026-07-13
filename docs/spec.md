# SimContract — Specification

**Status:** normative source of truth. All source code in this repository is written
from this specification. Code that needs an undocumented decision must first extend
this document (or an ADR under `docs/adr/`), then implement it.

SimContract is an independently developed research framework for **contract-bounded,
validation-aware multi-agent simulation**. It investigates how evolving simulation
models can be executed behind a fixed contract so that human, scripted, rule-based,
and LLM-assisted decisions remain valid, attributable, comparable, and reproducible.

## 1. Research questions

- **RQ1** Can heterogeneous simulation models be executed behind one adapter contract
  such that replacing the model is a configuration act, not a code change?
- **RQ2** Can AI/LLM participation be bounded so that invalid actions are structurally
  impossible and every decision is individually auditable?
- **RQ3** Can interactive sessions produce evidence sufficient to separate model
  behaviour from interaction effects (counterfactual comparison)?
- **RQ4** Can reproducibility be guaranteed at three levels: seeded rerun identity,
  replay-from-artifact re-execution, and statistical stability of stochastic
  controllers?
- **RQ5** Can analysis methods be added without modifying the runtime (fixed evidence
  interface, swappable analyzers)?

## 2. Execution invariants (SC-I1 .. SC-I7)

| ID | Invariant |
|---|---|
| SC-I1 | **Counterfactual branch completeness.** Every `step()` emits two outcome branches computed in the same resolution: `authoritative` (all roles decided by the domain's default policies) and `applied` (submitted decisions, with defaults completing any missing role). Both branches consume the **same** per-round exogenous inputs (`ctx.exogenous`), sampled exactly once from the round seed. Neither branch may draw additional randomness. |
| SC-I2 | **Missing-action completion.** A role with no accepted action at resolution time is completed inside the adapter by the domain's `DefaultActionProvider`, and reported as such. |
| SC-I3 | **Observable controller degradation.** Every controller failure emits a structured `FallbackEvent` with a reason code from a closed set. Degradation is never silent. |
| SC-I4 | **Ordered role resolution.** Roles resolve in the domain's declared stage order before aggregation. |
| SC-I5 | **Decision provenance completeness.** Every action in the final resolution carries a source tag from the closed set `human / rule / random_valid / top_score / bounded_llm / free_llm / domain_default`. The adapter's `ResolutionReport` is the single source of truth; the engine never infers provenance. |
| SC-I6 | **Selection auditability.** Every controller decision records: candidate set, scores, selection, controller configuration, rationale (if any), and the decision-time observable state digest. |
| SC-I7 | **Run-level failure accounting.** Fallback events aggregate into a per-run register with explicit denominators. |

## 3. Vocabulary (binding)

`step(state, actions, ctx) -> Outcome` · `branches.authoritative / branches.applied` ·
`action_schema.yaml` · `metric_catalog.yaml` · `observation_policy.yaml` ·
domain aliases `energy_market_v1`, `epidemic_policy_v1` · controller conditions
`rule / random_valid / top_score / free_llm / bounded_llm` · resilience adapter
`reference_stub` (not a research model).

## 4. Dependency rules (enforced by tests)

```text
contracts   → imports nothing internal
domains     → contracts only
engine      → contracts only  (never concrete domain packages)
evidence    → contracts only
analysis    → contracts only  (the evidence schema; never writer internals)
composition → the single wiring exception: imports engine + concrete domains,
              registers alias → adapter factory; imported only by entry points
experiments/cli → public orchestration APIs only
```

## 5. Contracts

### 5.1 Core types

- `Action`: `{role: str, slot: str, fields: dict[str, float|int|str|bool]}`
- `StateView`: read-only mapping passed to controllers/providers, filtered per
  `observation_policy.yaml`.
- `StepContext`: `{round_no, round_seed, exogenous: dict, scenario_id, config}`.

### 5.2 SimulationAdapter (Protocol)

```python
class SimulationAdapter(Protocol):
    domain_id: str
    contract_version: str
    roles: list[RoleSpec]                    # id, count, stage
    def initial_state(self, scenario, seed) -> State
    def sample_exogenous(self, state, rng) -> dict        # once per round (SC-I1)
    def action_space(self, state, role_slot) -> list[Action]   # schema-derived candidates
    def preview(self, state, action, ctx) -> Preview      # projected metrics; no mutation
    def validate_semantic(self, state, action) -> None | RejectionInfo
    def step(self, state, actions, ctx) -> Outcome        # authoritative transition
    @property
    def default_action_provider(self) -> DefaultActionProvider
```

### 5.3 DefaultActionProvider (Protocol)

`action_for(state, role_slot, persona, ctx) -> Action` — the domain's rule policy,
persona-parameterised. Used (a) by the adapter for SC-I2 completion (tag
`domain_default`), (b) by the `rule` controller condition (tag `rule`).

### 5.4 Outcome and ResolutionReport

```python
Outcome:
  role_outcomes: dict[slot, dict]
  system_metrics: dict[str, float]          # keys must exist in metric_catalog
  state_next: State
  branches: {"authoritative": {...metrics}, "applied": {...metrics}}   # SC-I1
  resolution: ResolutionReport
  meta: {adapter_version, approximations: list[str], provenance: dict}

ResolutionReport:
  submitted:  {slot: action_digest}
  accepted:   {slot: action_digest}
  completed:  {slot: action_digest}         # defaults filled by the domain (SC-I2)
  rejected:   {slot: RejectionInfo}
  sources:    {slot: source_tag}            # final provenance (SC-I5)
  completion_reasons: {slot: str}

RejectionInfo: {stage: "engine_syntactic"|"adapter_semantic", code: str, detail: str}
```

### 5.5 Validation authority (two tiers, non-overlapping)

- **Engine (syntactic):** schema shape, required fields, types, enum membership,
  numeric ranges, controller output format.
- **Adapter (semantic):** state-dependent legality, capacity/resource feasibility,
  cross-action conflicts.
Neither tier re-implements the other. `RejectionInfo.stage` records the rejecting tier.

### 5.6 Evidence schema (stable; analyzers depend on this only)

`BundleView`, `RunManifest`, `RoundRecord` (round_no, seed, exogenous_digest,
branches, system_metrics, resolution), `DecisionRecord` (SC-I6 fields),
`FailureRecord` (stage, reason, role_slot, round_no), `InvocationRecord`
(model_id, prompt_version, prompt_digest, temperature, tokens, latency_ms,
retry_index, response_digest, status).

## 6. Engine

### 6.1 Session loop

```text
state = adapter.initial_state(scenario, seed)
for round r in 1..N:
    round_seed = derive(run_seed, r)
    ctx.exogenous = adapter.sample_exogenous(state, rng(round_seed))   # ONCE (SC-I1)
    for stage in adapter stage order (SC-I4):
        for role_slot in stage:
            candidates = adapter.action_space(state_view, role_slot)
            action = controller(role_slot).act(state_view, candidates, previews)
            syntactic-validate; on absence/failure/invalid:
                emit FallbackEvent(reason)                             # SC-I3
                leave slot unfilled (adapter will complete, SC-I2)
            record DecisionRecord                                      # SC-I6
    outcome = adapter.step(state, accepted_actions, ctx)
    evidence.record(round_record from outcome; provenance from
                    outcome.resolution — returned truth, never inferred)  # SC-I5
    state = outcome.state_next
```

### 6.2 Seeding

Run seed → per-round seed by stable derivation (sha256 of run_seed‖round_no).
Stochastic controllers (`random_valid`, softmax tie-breaks) derive their seeds from
(round_seed, role_slot). With `free_llm`/`bounded_llm` disabled, a fixed run seed
must reproduce a bit-identical bundle content hash.

### 6.3 Controllers (conditions)

- `rule` — delegates to `adapter.default_action_provider` (tag `rule`).
- `random_valid` — uniform over the candidate set.
- `top_score` — argmax persona-weighted preview score.
- `bounded_llm` — LLM selects an index from the ranked candidate shortlist under a
  persona prompt; deterministic seeded-softmax fallback for tie/parse issues;
  endpoint unavailable → FallbackEvent(`llm_unreachable`) → `rule`.
- `free_llm` — experiment-only; LLM emits an action payload directly; post-hoc
  two-tier validation; never available in interactive play.

## 7. Domains

### 7.1 `energy_market_v1` — merit-order electricity auction

Roles/stages: `regulator`×1 (stage 1) → `generator`×3 (stage 2) → `retailer`×2 (stage 3).

Actions: regulator `{carbon_price∈[0,100], price_cap∈[60,400], renewable_subsidy∈[0,30]}`;
generator g `{price_bid∈[cost_g, 350], capacity_offered∈[0, cap_g], maintenance∈{0,1}}`;
retailer `{demand_bid∈[50,400], max_price∈[60,400]}`.

Generator parameters (scenario `baseline_v1`): coal `{cap 400, intensity 0.90, cost 45}`,
gas `{cap 300, intensity 0.45, cost 60}`, wind `{cap 250, intensity 0.0, cost 15}`.

Exogenous (once/round): demand shock `ε ~ AR(1): ε_t = 0.6 ε_{t-1} + N(0, 25)`;
wind availability `a_w ∈ [0.4, 1.0]` (uniform from round rng).

Clearing: for each non-maintenance generator, effective offer
`o_g = bid_g + carbon_price·intensity_g − subsidy·[intensity_g = 0]`, clipped to
`price_cap`; available capacity `q_g = capacity_offered_g · (a_w if wind else 1)`.
Total demand `D = clip(Σ demand_bid + ε, 100, 1200)`. Dispatch merit order until D;
clearing price = effective offer of the marginal unit (uniform price), bounded by cap.

Metrics: `clearing_price, total_emissions (Σ dispatch·intensity),
renewable_share, unserved_energy, consumer_cost (price·served),
generator_profit_total (Σ (price − cost_g − carbon·intensity_g + subsidy·[ren])·dispatch_g)`.

Semantic validation: `capacity_offered ≤ cap_g`; `maintenance=1 ⇒ capacity_offered=0`.

Personas: regulator `decarb_first {emissions −1.0, clearing_price −0.2}`,
`price_stability {clearing_price −1.0, unserved −0.8}`; generator `profit_max`,
`green_transition`; retailer `cost_min`, `reliability_first`.

### 7.2 `epidemic_policy_v1` — regional SEIR with policy and allocation

Roles/stages: `health_authority`×1 (stage 1) → `region_manager`×3 (stage 2).

Actions: authority `{restriction∈{0..3}, mask_level∈{0..2}, vaccine_budget∈[0,900]}`;
manager r `{share_testing, share_vaccination, share_capacity ∈ [0,1]}` with semantic
rule `Σ shares = 1 ± 0.01`.

Region parameters (scenario `three_regions_v1`): populations `[900k, 600k, 300k]`,
`β0=[0.32, 0.28, 0.36]`, `σ=1/4`, `γ=1/7`, IFR `0.008`, base hospital capacity
`[1800, 1200, 700]` severe beds, severe fraction `0.05`.

Exogenous (once/round): per-region transmission shock `m_r ~ LogNormal(0, 0.15)`.

Dynamics per round (7 daily sub-steps): effective
`β_r = β0_r · m_r · restr_mult(restriction) · mask_mult(mask) · (1 − 0.25·test_share_r)`
with `restr_mult = [1.0, .8, .6, .45]`, `mask_mult = [1.0, .85, .72]`.
Vaccination flow: `doses_r = vaccine_budget · vacc_share_r · pop_r/Σpop`, efficacy 0.85,
moves S→R. Capacity: `cap_r = base_r · (1 + 0.5·cap_share_r)`.
SEIR updates, deaths from I with IFR; overflow day when severe demand > cap_r.

Metrics: `new_infections, cumulative_deaths, overflow_days, econ_cost
(1500·restriction + 0.9·new_infections per round unit), vaccination_coverage,
equity_gap (max_r coverage − min_r coverage)`.

Personas: authority `health_first`, `economy_balanced`; manager `equity_first`,
`efficiency_first`.

## 8. Evidence

Bundle = one directory: `manifest.json` (versions, seeds, config digest, content hash
computed over canonical JSON with the hash field excluded; file hashes listed
separately), `rounds.json`, `decisions.json`, `events.json`, `register.json`.
Replay executes the engine path from recorded accepted actions + seeds and asserts
metric equality (LLM-off runs: bit-identical).

## 9. Analysis

`Analyzer` protocol over `BundleView`s only: `timeseries` (KPI trajectories; branch
divergence), `groups` (cohorts by condition/persona/source-mix; mean±sd, paired-seed
deltas), `events` (degradation taxonomy, event-aligned windows). Results carry
lineage: analyzer id/version, input bundle hashes, parameter digest.

## 10. Experiments

E1 dependency audit · E2 rerun identity + replay equivalence · E3 cross-domain
contract portability (same config on both domains + compliance suite) ·
E4 five-condition controller study · E5 invariant suite over bundles ·
E6 analysis-interface extensibility/consistency.
