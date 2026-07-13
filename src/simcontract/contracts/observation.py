"""Observation policy: which top-level state keys each role may observe."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ObservationPolicy:
    def __init__(self, spec: dict[str, list[str]]):
        self.spec = spec

    @classmethod
    def from_file(cls, path: str | Path) -> "ObservationPolicy":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh))

    def view(self, state: dict[str, Any], role: str) -> dict[str, Any]:
        allowed = self.spec.get(role, [])
        if "*" in allowed:
            return dict(state)
        return {k: state[k] for k in allowed if k in state}
