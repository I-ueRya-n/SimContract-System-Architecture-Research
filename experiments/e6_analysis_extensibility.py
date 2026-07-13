"""E6: analysis-interface extensibility — built-in analyzers over heterogeneous
bundles, plus a new analyzer registered at runtime with zero core changes.

Usage: PYTHONPATH=src python3 experiments/e6_analysis_extensibility.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from simcontract.analysis import (
    AnalysisResult,
    AnalyzerSpec,
    default_registry,
    make_lineage,
    write_report,
)
from simcontract.composition import create_application
from simcontract.contracts import BundleView

ROOT = Path(__file__).resolve().parents[1]


class SourceMixAnalyzer:
    """The plug-in analyzer: decision-source mix per bundle. Registered at
    runtime; its existence requires no engine or domain change (the audit and
    test suite prove that statically)."""

    spec = AnalyzerSpec(analysis_id="source_mix", version="1.0.0",
                        supported_domains="*", requires_records=("rounds",))

    def run(self, bundles: list[BundleView]) -> AnalysisResult:
        rows = []
        for b in bundles:
            mix: dict[str, int] = {}
            for r in b.rounds:
                for tag in r.resolution["sources"].values():
                    mix[tag] = mix.get(tag, 0) + 1
            rows.append({"bundle": b.manifest.run_id,
                         "domain": b.manifest.domain_id, **mix})
        return AnalysisResult(spec=self.spec, tables={"source_mix": rows},
                              lineage=make_lineage(self.spec, bundles))


def main() -> int:
    app = create_application()
    tmp = ROOT / "results" / "e6"
    bundles = []
    for d in app.list_domains():
        run = app.run_session(domain=d["domain_id"], scenario=d["scenarios"][0],
                              seed=99, rounds=3, conditions={"all": "rule"},
                              personas={}, out_dir=tmp / d["domain_id"])
        bundles.append(run["bundle"])
    views = [BundleView.load(b) for b in bundles]

    registry = default_registry()
    before = registry.ids()
    registry.register(SourceMixAnalyzer())
    results = [registry.get(a).run(views) for a in registry.ids()]
    report = write_report(results, tmp / "report")

    print(f"[E6] built-in analyzers: {before}")
    print(f"[E6] after runtime registration: {registry.ids()}")
    print(f"[E6] {len(views)} heterogeneous bundles analyzed -> {report}")
    lineages = [r.lineage["input_bundle_hashes"] for r in results]
    ok = (len(registry.ids()) == len(before) + 1
          and all(len(l) == len(views) for l in lineages))
    print(f"[E6] analysis extensibility: {'PASS' if ok else 'FAIL'} "
          "(zero engine/domain changes; lineage complete)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
