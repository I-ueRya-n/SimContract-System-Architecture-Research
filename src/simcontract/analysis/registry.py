"""Analyzer registry: adding an analyzer never touches engine or domains."""
from __future__ import annotations

from typing import Any


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._analyzers: dict[str, Any] = {}

    def register(self, analyzer: Any) -> None:
        self._analyzers[analyzer.spec.analysis_id] = analyzer

    def get(self, analysis_id: str) -> Any:
        return self._analyzers[analysis_id]

    def ids(self) -> list[str]:
        return sorted(self._analyzers)
