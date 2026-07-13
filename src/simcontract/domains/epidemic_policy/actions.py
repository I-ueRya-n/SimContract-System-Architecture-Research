"""Typed action payloads for the epidemic-policy domain."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HealthPolicy:
    restriction: int
    mask_level: int
    vaccine_budget: float

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> "HealthPolicy":
        return cls(int(fields["restriction"]), int(fields["mask_level"]),
                   float(fields["vaccine_budget"]))


@dataclass(frozen=True)
class RegionalAllocation:
    share_testing: float
    share_vaccination: float
    share_capacity: float

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> "RegionalAllocation":
        return cls(float(fields["share_testing"]), float(fields["share_vaccination"]),
                   float(fields["share_capacity"]))

    @property
    def total(self) -> float:
        return self.share_testing + self.share_vaccination + self.share_capacity
