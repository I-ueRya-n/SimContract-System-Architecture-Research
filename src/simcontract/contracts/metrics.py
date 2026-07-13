"""Metric catalog: KPI names, units, and improvement direction (spec 3)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class MetricCatalog:
    def __init__(self, entries: list[dict[str, Any]]):
        self.entries = {e["key"]: e for e in entries}

    @classmethod
    def from_file(cls, path: str | Path) -> "MetricCatalog":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh))

    @property
    def keys(self) -> set[str]:
        return set(self.entries)

    def validate_metrics(self, metrics: dict[str, float]) -> list[str]:
        """Return the list of metric keys not present in the catalog."""
        return sorted(set(metrics) - self.keys)

    def direction(self, key: str) -> str:
        return self.entries[key].get("direction", "min")
