# SimContract

A contract-governed, **validation-aware** research framework for
simulation-based decision experiments. Heterogeneous simulation domains run
behind one adapter contract; human, rule-based, random, ranked, and
LLM-assisted controllers pass through the same two-tier validation and
execution path; every run produces a hashed, replayable evidence bundle
consumed by swappable offline analyzers.

**Author:** Ryan Lin (ORCID 0009-0001-9698-6999) · MIT License · see `CITATION.cff`

## Claim boundary

SimContract's research domains (`energy_market_v1`, `epidemic_policy_v1`) are
**controlled, literature-informed testbeds** for evaluating architecture and
controller mechanisms — structurally different on purpose. They are *not*
externally validated forecasting models, and no real-world energy or
public-health conclusion is claimed. The `reference_stub` domain exists only
for contract testing and is not a research model. See
`docs/claim_boundary.md`.

## Five-minute reproduction

```bash
pip install -e .              # or: PYTHONPATH=src with PyYAML installed
python -m pytest -q           # 60 tests: contracts, invariants, compliance,
                              # dependency + token-leakage audit, rejection
                              # paths, replay, verification, analysis

# list domains discovered through their manifests
python -m simcontract.cli domains

# run a session -> hashed evidence bundle (jsonl traces, metrics.csv, report.html)
python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 \
    --rounds 5 --seed 73 --controllers all=rule --out results/demo --verbose

# decision replay: re-execute the bundle through the engine and compare
python -m simcontract.cli replay --bundle results/demo

# bundle verification: recompute hashes without executing
python -m simcontract.cli verify --bundle results/demo

# play one role yourself (all other roles rule-controlled)
python -m simcontract.cli play --domain energy_market_v1 --scenario baseline_v1 \
    --role regulator_1 --rounds 3

# offline analysis (time-series, groups, events) -> CSV + markdown report
python -m simcontract.cli analyze --bundles results/demo --out results/analysis

# evidence programme E1-E6
PYTHONPATH=src python3 experiments/e1_boundary_audit.py
PYTHONPATH=src python3 experiments/e2_reproducibility.py energy_market_v1
PYTHONPATH=src python3 experiments/e3_cross_domain.py
PYTHONPATH=src python3 experiments/e4_controller_comparison.py
PYTHONPATH=src python3 experiments/e5_invariant_suite.py
PYTHONPATH=src python3 experiments/e6_analysis_extensibility.py
```

LLM-assisted controllers (`bounded_llm`, `free_llm`) are optional and disabled
by default. Configure an OpenAI-compatible endpoint (local LM Studio / Ollama
/ llama.cpp, or a hosted provider) in one of two ways:

```bash
# 1. env / .env file (copy .env.example -> .env; .env is git-ignored)
cp .env.example .env    # then set SIMCONTRACT_LLM_BASE_URL / _MODEL / _API_KEY
python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 \
    --controllers all=bounded_llm --out results/llm_demo

# 2. explicit flags (override the environment)
python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 \
    --controllers all=bounded_llm --llm-base-url http://localhost:1234/v1 \
    --llm-model your-model-id --out results/llm_demo
```

API keys are read from the environment only and never committed. When no
endpoint is configured the LLM controllers degrade observably
(`llm_disabled`); when configured but unreachable they degrade with
`endpoint_unreachable` — all recorded as structured events with denominators.

## Architecture (docs/spec.md is the source of truth)

```text
contracts    adapter + controller + registry + evidence-sink protocols ·
             action envelope/schemas · metric catalog · observation policy ·
             domain manifest · STABLE versioned evidence schema · seeding
engine       session lifecycle · engine-tier (syntactic/envelope) validation ·
             preview requests · seed discipline · decision replay executor
controllers  rule · random_valid · top_score · human_script · bounded_llm ·
             free_llm (experiment-only) · interactive human (CLI play)
plugins      runtime registry (duplicate/compat/substitution guards) ·
             dormant entry-point discovery for external domains
domains      reference_stub · energy_market_v1 · epidemic_policy_v1
             (manifest, model, typed actions, defaults, personas, scenarios)
evidence     BundleEvidenceWriter (EvidenceSink) · canonical content hash +
             file hashes · jsonl traces · metrics.csv · report.html ·
             bundle verification
analysis     offline analyzers over bundles only (timeseries/groups/events) +
             plug-in registry with lineage records
application  use-case facade for CLI, experiments, and any future API
composition  the single module wiring concrete implementations (ADR 0001/0005)
```

Execution invariants SC-I1..SC-I7 (dual counterfactual branches from shared
exogenous inputs, domain completion of missing actions, observable
degradation, ordered stages, provenance completeness, selection auditability,
failure accounting) are specified in `docs/spec.md` §2, enforced by the test
suite, and audited over every produced bundle by `experiments/e5`.

## Dependency rules (machine-enforced)

`contracts` imports nothing internal · `engine`/`controllers`/`plugins`/
`domains`/`evidence`/`analysis`/`llm` import contracts only (controllers may
use the LLM port) · `application` fronts platform layers but never concrete
domains · `composition.py` is the single wiring exception, imported only by
entry points. Core layers carry zero domain vocabulary (token-leakage test).
See `docs/dependency-rules.md` and `tests/dependency/`.

## Documentation

`docs/spec.md` (normative) · `docs/architecture.md` ·
`docs/dependency-rules.md` · `docs/evidence_schema.md` ·
`docs/packaging_and_plugins.md` · `docs/versioning-and-compatibility.md` ·
`docs/experiment_protocol.md` · `docs/claim_boundary.md` ·
`docs/domains/*.md` · `docs/adr/0001-0006`.
