"""Offline analysis layer. Depends on the stable evidence schema only."""
from .base import AnalysisResult, AnalyzerSpec, make_lineage, supports
from .events import EventAnalyzer
from .registry import AnalyzerRegistry
from .groups import GroupComparisonAnalyzer
from .report import write_report
from .timeseries import TimeSeriesAnalyzer


def default_registry() -> AnalyzerRegistry:
    registry = AnalyzerRegistry()
    registry.register(TimeSeriesAnalyzer())
    registry.register(GroupComparisonAnalyzer())
    registry.register(EventAnalyzer())
    return registry


__all__ = ["AnalysisResult", "AnalyzerRegistry", "AnalyzerSpec", "EventAnalyzer",
           "GroupComparisonAnalyzer", "TimeSeriesAnalyzer", "default_registry",
           "make_lineage", "supports", "write_report"]
