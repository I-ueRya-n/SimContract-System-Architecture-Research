# Example: a bundle-only analyzer extension

`controller_source_summary.py` is a minimal, self-contained example of the
**extension reuse** seam: a third-party analyzer that reads only a frozen
evidence bundle and plugs in through the existing analyzer registry, with no
change to the engine, the domains, or the evidence schema.

For each bundle it reports decision provenance (the `source_tag` on each
decision — a controller condition or `domain_default` completion), the number
of recorded fallback events, and whether the decision count matches the
expected `rounds x role-slots` (bundle completeness).

## What it demonstrates (and its boundaries)

- Reads a frozen `BundleView` **only** — it never runs or mutates a simulation.
- Uses only the public installed API (`simcontract.contracts`,
  `simcontract.analysis.base`, `simcontract.analysis.registry`), so it works
  from a wheel-installed SimContract.
- Registers through `AnalyzerRegistry` — adding it touches no engine or domain
  code.
- Emits lineage (`make_lineage`) binding the result to the exact input bundle
  content hash.

This is *extension reuse*, distinct from integrating a new simulation model
(see `docs/adapter-checklist.md`) — no new adapter, controller, or contract is
involved.

## Run it

```bash
# produce a bundle
simcontract run --domain energy_market_v1 --scenario baseline_v1 \
    --seed 73 --rounds 5 --controllers all=rule --out /tmp/bundle

# run the example analyzer over it
PYTHONPATH=examples/analyzer_extension python - <<'PY'
from simcontract.analysis.registry import AnalyzerRegistry
from simcontract.contracts import BundleView
from controller_source_summary import ControllerSourceSummary

reg = AnalyzerRegistry()
reg.register(ControllerSourceSummary())
result = reg.get("controller_source_summary").run([BundleView.load("/tmp/bundle")])
print(result.tables["controller_source_summary"])
print("lineage:", result.lineage)
PY
```

Regression test: `tests/test_analyzer_extension_example.py`.
