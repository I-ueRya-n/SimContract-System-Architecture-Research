"""Analysis layer: analyzers consume bundles only; extensibility (RQ5)."""
from __future__ import annotations

from simcontract.analysis import (
    AnalysisResult,
    AnalyzerSpec,
    default_registry,
    make_lineage,
)
from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import BundleView
from simcontract.controllers import RuleController
from simcontract.engine import SessionRunner
from simcontract.evidence import write_bundle


def _bundle(tmp_path, seed=13):
    adapter = create_registry().create("reference_stub")
    schema, observation, catalog, _ = domain_assets("reference_stub")
    runner = SessionRunner(adapter, schema, observation, catalog)
    controllers = {"agent_1": RuleController(adapter.default_action_provider, None)}
    result = runner.run(scenario_id="default", run_seed=seed, rounds=3,
                        controllers=controllers, personas={})
    return BundleView.load(write_bundle(result, tmp_path / f"b{seed}"))


def test_builtin_analyzers_run(tmp_path):
    bundles = [_bundle(tmp_path, 13), _bundle(tmp_path, 14)]
    registry = default_registry()
    for analysis_id in registry.ids():
        result = registry.get(analysis_id).run(bundles)
        assert result.tables, analysis_id
        assert result.lineage["input_bundle_hashes"][0] is not None


def test_branch_divergence_zero_for_rule_runs(tmp_path):
    bundle = _bundle(tmp_path, 15)
    rows = default_registry().get("timeseries").run([bundle]).tables["branch_divergence"]
    assert rows and all(r["divergence"] == 0.0 for r in rows)


class _ToyAnalyzer:
    """E6: a fourth analyzer registers with zero engine/domain changes."""
    spec = AnalyzerSpec("toy_count", "0.1", "*", ("rounds",))

    def run(self, bundles, parameters=None):
        result = AnalysisResult(spec=self.spec,
                                lineage=make_lineage(self.spec, bundles, parameters))
        result.tables["counts"] = [{"run_id": b.manifest.run_id,
                                    "rounds": len(b.rounds)} for b in bundles]
        return result


def test_fourth_analyzer_plugs_in(tmp_path):
    registry = default_registry()
    registry.register(_ToyAnalyzer())
    result = registry.get("toy_count").run([_bundle(tmp_path, 16)])
    assert result.tables["counts"][0]["rounds"] == 3
