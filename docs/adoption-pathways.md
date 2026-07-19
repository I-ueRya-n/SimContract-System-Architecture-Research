# Adoption pathways

There are several distinct ways to reuse SimContract, in increasing order of
investment. They are genuinely different kinds of reuse — keeping them separate
avoids conflating "I reran the benchmark" with "I integrated a new model."

## 1. Reproduction (no code)

Reproduce a published result: install the release, run the deterministic
benchmark, and confirm the content hash, `verify`, and `replay`.

```bash
pip install -e ".[dev]"
python -m pytest -q
python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 \
    --seed 73 --rounds 5 --controllers all=rule --out results/demo
python -m simcontract.cli verify --bundle results/demo
python -m simcontract.cli replay --bundle results/demo
```

See `reproduction/` for the independent-reproduction protocol.

## 2. Configuration reuse (no code)

Vary an existing study without writing code: choose a different `--scenario`,
`--seed`, `--rounds`, or `--controllers` assignment, or add a new scenario YAML
for an existing domain. The engine, evidence pipeline, and analyzers are
unchanged.

## 3. Extension reuse (small, bundle-only code)

Add a **bundle-only analyzer** that reads frozen evidence and registers through
the analyzer registry — no engine or domain change. A complete, tested example
is in `examples/analyzer_extension/` (see also `docs/evidence_schema.md` for
the `BundleView` surface).

You can likewise add a **controller** (a new decision policy) that passes
through the same validation path as the built-in controllers.

## 4. Model integration / scientific adoption (a new adapter)

Bring your own simulation model by implementing the `SimulationAdapter`
contract, so your model runs behind the same governed, replayable, verifiable
pipeline. This is the deepest form of reuse and is what makes one maintained
platform serve many studies. Follow `docs/adapter-checklist.md`.

Wrapping an **external** simulator (e.g. Mesa/GAMA/SUMO) behind the adapter is
the same pathway, but note it is a **prospective** integration: no external
adapter ships or is evaluated in this release, and the plugin registry defines
(but does not yet activate) third-party domain distribution.

## Summary

| Pathway | Investment | Touches |
|---|---|---|
| Reproduction | none | run the CLI |
| Configuration reuse | none | scenario YAML / CLI flags |
| Extension reuse | small | a bundle-only analyzer or a controller |
| Model integration | larger | a new `SimulationAdapter` |

Each pathway keeps the core invariants (SC-I1..SC-I7) and the evidence
guarantees intact.
