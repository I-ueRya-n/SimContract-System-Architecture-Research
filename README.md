# SimContract

A contract-bounded, **validation-aware** research framework for multi-agent
simulation. Heterogeneous simulation domains run behind one adapter contract;
human, rule-based, random, and LLM-assisted controllers pass through the same
validation and execution path; every run produces a hashed, replayable evidence
bundle.

**Author:** Ryan Lin (ORCID 0009-0001-9698-6999) · MIT License · see `CITATION.cff`

## Claim boundary

SimContract's domain models (`energy_market_v1`, `epidemic_policy_v1`) are
**controlled, literature-informed testbeds** for evaluating architecture and
controller mechanisms — structurally different on purpose. They are *not*
externally validated forecasting models, and no real-world energy or
public-health conclusion is claimed. The `reference_stub` domain exists only
for contract testing and is not a research model.

## Five-minute reproduction

```bash
pip install -e .              # or: PYTHONPATH=src with PyYAML installed
python -m pytest -q           # 38 tests: contracts, invariants, compliance, replay

# list domains discovered through their manifests
python -m simcontract.cli domains

# run a session -> hashed evidence bundle
python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 \
    --rounds 5 --seed 73 --controllers all=rule --out results/demo --verbose

# re-execute the bundle and verify equivalence
python -m simcontract.cli replay --bundle results/demo

# play one role yourself (all other roles rule-controlled)
python -m simcontract.cli play --domain energy_market_v1 --scenario baseline_v1 \
    --role regulator_1 --rounds 3

# offline analysis (time-series, groups, events) -> CSV + markdown report
python -m simcontract.cli analyze --bundles results/demo --out results/analysis

# experiments
python experiments/e2_reproducibility.py energy_market_v1
python experiments/e3_contract_swap.py
```

LLM-assisted controllers (`bounded_llm`, `free_llm`) are optional and disabled
by default; point `--llm-base-url/--llm-model` at any OpenAI-compatible local
endpoint to enable them. All degradation is recorded as structured events.

## Architecture (docs/spec.md is the source of truth)

```text
contracts   adapter protocol · action schemas · metric catalog · observation
            policy · domain manifest · STABLE evidence schema
engine      registry · controller chain (rule/random/top/bounded_llm/free_llm/
            human) · two-tier validation · seeded sessions · replay
evidence    hashed bundles (content hash + file hashes) · failure register
analysis    offline analyzers over bundles only (timeseries/groups/events) +
            plug-in registry with lineage records
domains     reference_stub · energy_market_v1 · epidemic_policy_v1
composition the single module wiring domains into the registry (ADR 0001)
```

Execution invariants SC-I1..SC-I7 (dual counterfactual branches from shared
exogenous inputs, domain completion of missing actions, observable degradation,
ordered stages, provenance completeness, selection auditability, failure
accounting) are specified in `docs/spec.md` §2 and enforced by the test suite.

## Dependency rules (test-enforced)

`contracts` imports nothing internal · `domains`/`engine`/`evidence`/`analysis`
import contracts only · `composition.py` is the single wiring exception. See
`tests/test_dependency_rules.py`.
