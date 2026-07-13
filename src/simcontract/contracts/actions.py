"""Action schemas: declarative legal decision surfaces per role (spec 3/5.5).

Schema file format (``action_schema.yaml``)::

    role_name:
      field_name:
        type: float | int | choice | bool
        min: <number>        # float/int
        max: <number>        # float/int
        choices: [..]        # choice

Engine-tier (syntactic) validation lives here: shape, required fields, types,
enum membership, numeric ranges (spec 5.5).
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from .core import Action, RejectionInfo


class ActionSchema:
    def __init__(self, spec: dict[str, dict[str, dict[str, Any]]]):
        self.spec = spec

    @classmethod
    def from_file(cls, path: str | Path) -> "ActionSchema":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh))

    def fields_for(self, role: str) -> dict[str, dict[str, Any]]:
        if role not in self.spec:
            raise KeyError(f"no action schema for role {role!r}")
        return self.spec[role]

    # ---- syntactic validation (engine tier) --------------------------------
    def validate_syntactic(self, action: Action) -> RejectionInfo | None:
        try:
            fields = self.fields_for(action.role)
        except KeyError:
            return RejectionInfo("engine_syntactic", "unknown_role",
                                 f"role {action.role!r} not in schema")
        for name, rule in fields.items():
            if name not in action.fields:
                return RejectionInfo("engine_syntactic", "missing_field",
                                     f"{action.role}.{name} missing")
            value = action.fields[name]
            ftype = rule.get("type")
            if ftype == "float":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    return RejectionInfo("engine_syntactic", "type_error",
                                         f"{name} expected float, got {type(value).__name__}")
                if not (rule["min"] <= float(value) <= rule["max"]):
                    return RejectionInfo("engine_syntactic", "range_error",
                                         f"{name}={value} outside [{rule['min']}, {rule['max']}]")
            elif ftype == "int":
                if not isinstance(value, int) or isinstance(value, bool):
                    return RejectionInfo("engine_syntactic", "type_error",
                                         f"{name} expected int, got {type(value).__name__}")
                if not (rule["min"] <= value <= rule["max"]):
                    return RejectionInfo("engine_syntactic", "range_error",
                                         f"{name}={value} outside [{rule['min']}, {rule['max']}]")
            elif ftype == "choice":
                if value not in rule["choices"]:
                    return RejectionInfo("engine_syntactic", "enum_error",
                                         f"{name}={value!r} not in {rule['choices']}")
            elif ftype == "bool":
                if not isinstance(value, bool):
                    return RejectionInfo("engine_syntactic", "type_error",
                                         f"{name} expected bool")
            else:  # pragma: no cover - schema authoring error
                return RejectionInfo("engine_syntactic", "schema_error",
                                     f"unknown field type {ftype!r} for {name}")
        extra = set(action.fields) - set(fields)
        if extra:
            return RejectionInfo("engine_syntactic", "unknown_field",
                                 f"unexpected fields: {sorted(extra)}")
        return None

    # ---- candidate sampling --------------------------------------------------
    def sample_candidates(self, role: str, slot: str, rng: random.Random,
                          n: int) -> list[Action]:
        """Sample ``n`` schema-valid candidate actions (valid by construction)."""
        fields = self.fields_for(role)
        out: list[Action] = []
        for _ in range(n):
            values: dict[str, Any] = {}
            for name, rule in fields.items():
                ftype = rule.get("type")
                if ftype == "float":
                    values[name] = round(rng.uniform(rule["min"], rule["max"]), 4)
                elif ftype == "int":
                    values[name] = rng.randint(rule["min"], rule["max"])
                elif ftype == "choice":
                    values[name] = rng.choice(rule["choices"])
                elif ftype == "bool":
                    values[name] = rng.random() < 0.5
            out.append(Action(role=role, slot=slot, fields=values))
        return out
