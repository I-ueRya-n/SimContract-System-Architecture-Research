"""Event-based analyzer: degradation taxonomy and rates from structured records."""
from __future__ import annotations

from simcontract.contracts import BundleView

from .base import AnalysisResult, AnalyzerSpec, make_lineage


class EventAnalyzer:
    spec = AnalyzerSpec("events", "1.0", "*", ("events", "decisions"))

    def run(self, bundles: list[BundleView], parameters=None) -> AnalysisResult:
        result = AnalysisResult(spec=self.spec,
                                lineage=make_lineage(self.spec, bundles, parameters))
        rows = []
        for b in bundles:
            counts: dict[tuple[str, str], int] = {}
            for ev in b.events:
                counts[(ev.family, ev.reason)] = counts.get((ev.family, ev.reason), 0) + 1
            denominator = max(len(b.decisions), 1)
            for (family, reason), count in sorted(counts.items()):
                rows.append({"run_id": b.manifest.run_id, "domain": b.manifest.domain_id,
                             "family": family, "reason": reason, "count": count,
                             "rate_per_decision": round(count / denominator, 6)})
            if not counts:
                rows.append({"run_id": b.manifest.run_id, "domain": b.manifest.domain_id,
                             "family": "none", "reason": "not_observed", "count": 0,
                             "rate_per_decision": 0.0})
        result.tables["event_taxonomy"] = rows
        return result
