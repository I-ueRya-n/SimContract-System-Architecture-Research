"""Core value types of the SimContract contract layer (spec section 5.1/5.4)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SourceTag = Literal[
    "human", "rule", "random_valid", "top_score",
    "bounded_llm", "free_llm", "domain_default",
]

SOURCE_TAGS: tuple[str, ...] = (
    "human", "rule", "random_valid", "top_score",
    "bounded_llm", "free_llm", "domain_default",
)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RoleSpec:
    role: str
    count: int
    stage: int

    def slots(self) -> list[str]:
        return [f"{self.role}_{i + 1}" for i in range(self.count)]


@dataclass(frozen=True)
class Action:
    role: str
    slot: str
    fields: dict[str, Any]

    def digest(self) -> str:
        return digest({"role": self.role, "slot": self.slot, "fields": self.fields})


@dataclass
class StepContext:
    round_no: int
    round_seed: int
    exogenous: dict[str, Any]
    scenario_id: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Preview:
    projected_metrics: dict[str, float]


REJECTION_STAGES: tuple[str, ...] = (
    "engine_syntactic", "adapter_semantic",
    # reserved for later phases:
    "state_stale", "role_unauthorized", "resource_infeasible",
)


@dataclass(frozen=True)
class RejectionInfo:
    stage: str  # one of REJECTION_STAGES; canonical tiers are the first two
    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ResolutionReport:
    """Adapter-returned completion truth (SC-I5). The engine never infers provenance."""

    submitted: dict[str, str] = field(default_factory=dict)
    accepted: dict[str, str] = field(default_factory=dict)
    completed: dict[str, str] = field(default_factory=dict)
    rejected: dict[str, dict[str, str]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    completion_reasons: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Outcome:
    role_outcomes: dict[str, dict[str, Any]]
    system_metrics: dict[str, float]
    state_next: Any
    branches: dict[str, dict[str, float]]  # {"authoritative": ..., "applied": ...}
    resolution: ResolutionReport
    meta: dict[str, Any] = field(default_factory=dict)
