"""Time-series analyzer: KPI trajectories and branch divergence per round."""
from __future__ import annotations

from simcontract.contracts import BundleView

from .base import AnalysisResult, AnalyzerSpec, make_lineage


class TimeSeriesAnalyzer:
    spec = AnalyzerSpec("timeseries", "1.0", "*", ("rounds",))

    def run(self, bundles: list[BundleView], parameters=None) -> AnalysisResult:
        result = AnalysisResult(spec=self.spec,
                                lineage=make_lineage(self.spec, bundles, parameters))
        trajectory, divergence = [], []
        for b in bundles:
            for r in b.rounds:
                base = {"run_id": b.manifest.run_id, "domain": b.manifest.domain_id,
                        "round": r.round_no}
                for key, value in r.system_metrics.items():
                    trajectory.append({**base, "metric": key, "value": value})
                auth = r.branches.get("authoritative", {})
                appl = r.branches.get("applied", {})
                for key in appl:
                    if key in auth:
                        divergence.append({**base, "metric": key,
                                           "applied": appl[key],
                                           "authoritative": auth[key],
                                           "divergence": round(appl[key] - auth[key], 6)})
        result.tables["kpi_trajectory"] = trajectory
        result.tables["branch_divergence"] = divergence
        return result
