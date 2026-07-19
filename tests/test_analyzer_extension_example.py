"""The bundle-only analyzer example runs against a frozen bundle through the
public seam, with no engine or domain dependency.

Loads the example from ``examples/analyzer_extension/`` (not an installed
package) and runs it over the frozen benchmark bundle using only the public
``BundleView`` and ``AnalyzerRegistry`` API, so it also passes from a
wheel-installed SimContract.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from simcontract.analysis.registry import AnalyzerRegistry
from simcontract.contracts import BundleView

_ROOT = Path(__file__).resolve().parents[1]
_EX = _ROOT / "examples" / "analyzer_extension" / "controller_source_summary.py"
_BENCH = _ROOT / "benchmark" / "energy_baseline_v1_seed73"

_spec = importlib.util.spec_from_file_location("controller_source_summary", _EX)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["controller_source_summary"] = _mod
_spec.loader.exec_module(_mod)


def test_example_analyzer_runs_bundle_only():
    reg = AnalyzerRegistry()
    reg.register(_mod.ControllerSourceSummary())
    assert reg.ids() == ["controller_source_summary"]

    bundle = BundleView.load(_BENCH)
    result = reg.get("controller_source_summary").run([bundle])

    rows = result.tables["controller_source_summary"]
    assert len(rows) == 1
    row = rows[0]
    assert row["domain"] == "energy_market_v1"
    assert row["decisions"] == row["expected_decisions"]
    assert row["complete"] is True
    assert sum(row["source_tags"].values()) == row["decisions"]

    # lineage binds the result to the exact input bundle content hash
    assert result.lineage["analysis_id"] == "controller_source_summary"
    assert result.lineage["input_bundle_hashes"] == [bundle.manifest.content_hash]


def test_example_analyzer_is_domain_neutral():
    assert _mod.ControllerSourceSummary().spec.supported_domains == "*"
