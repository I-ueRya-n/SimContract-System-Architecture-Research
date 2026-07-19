"""A minimal, bundle-only analyzer extension.

This demonstrates the supported *extension reuse* seam: a third-party analyzer
that reads only a frozen evidence ``BundleView``, produces lineage metadata,
and requires no change to the engine, the domains, or the evidence schema. It
uses only the public, installed API
(``simcontract.contracts`` and ``simcontract.analysis.base``), so it works
against a wheel-installed SimContract.

Register it through the existing ``AnalyzerRegistry`` and run it over any bundle
produced by ``simcontract run ... --out <bundle>``:

    from simcontract.analysis.registry import AnalyzerRegistry
    from simcontract.contracts import BundleView
    from controller_source_summary import ControllerSourceSummary

    reg = AnalyzerRegistry()
    reg.register(ControllerSourceSummary())
    result = reg.get("controller_source_summary").run([BundleView.load("bundle")])
    print(result.tables["controller_source_summary"])
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from simcontract.analysis.base import AnalysisResult, AnalyzerSpec, make_lineage
from simcontract.contracts import BundleView


class ControllerSourceSummary:
    """Summarise per-run decision provenance and bundle completeness.

    For each bundle it reports how decisions were sourced (the ``source_tag``
    on each decision record, e.g. a controller condition or ``domain_default``
    completion), the number of recorded fallback events, and whether the number
    of decisions matches the expected ``rounds x role-slots`` (bundle
    completeness). It is domain-neutral (``supported_domains="*"``).
    """

    spec = AnalyzerSpec("controller_source_summary", "1.0", "*", ("decisions",))

    def run(self, bundles: list[BundleView],
            parameters: dict[str, Any] | None = None) -> AnalysisResult:
        result = AnalysisResult(
            spec=self.spec,
            lineage=make_lineage(self.spec, bundles, parameters),
        )
        rows: list[dict[str, Any]] = []
        for b in bundles:
            sources = Counter(d.source_tag for d in b.decisions)
            expected = b.manifest.rounds * len(b.manifest.conditions)
            rows.append({
                "run_id": b.manifest.run_id,
                "domain": b.manifest.domain_id,
                "decisions": len(b.decisions),
                "expected_decisions": expected,
                "complete": len(b.decisions) == expected,
                "fallback_events": len(b.events),
                "source_tags": dict(sorted(sources.items())),
            })
        result.tables["controller_source_summary"] = rows
        return result
