"""Group-comparison analyzer: cohorts by condition/persona/domain."""
from __future__ import annotations

import statistics

from simcontract.contracts import BundleView

from .base import AnalysisResult, AnalyzerSpec, make_lineage


def _condition_summary(manifest) -> str:
    return "|".join(sorted(set(manifest.conditions.values()))) or "preset"


class GroupComparisonAnalyzer:
    spec = AnalyzerSpec("groups", "1.0", "*", ("rounds",))

    def run(self, bundles: list[BundleView], parameters=None) -> AnalysisResult:
        result = AnalysisResult(spec=self.spec,
                                lineage=make_lineage(self.spec, bundles, parameters))
        groups: dict[tuple[str, str, str], list[float]] = {}
        for b in bundles:
            cohort = (b.manifest.domain_id, _condition_summary(b.manifest), "final_round")
            for key, value in b.rounds[-1].system_metrics.items():
                groups.setdefault((*cohort[:2], key), []).append(value)
        rows = []
        for (domain, cohort, metric), values in sorted(groups.items()):
            rows.append({
                "domain": domain, "cohort": cohort, "metric": metric,
                "n": len(values),
                "mean": round(statistics.fmean(values), 6),
                "sd": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
                "min": min(values), "max": max(values),
            })
        result.tables["group_summary"] = rows
        return result
