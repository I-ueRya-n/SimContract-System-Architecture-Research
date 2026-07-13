"""Typed action payloads (consolidated spec 9.1: payloads become typed inside
the domain). Semantic validation reasons over these, not raw dicts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RegulatorPolicy:
    carbon_price: float
    price_cap: float
    renewable_subsidy: float

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> "RegulatorPolicy":
        return cls(float(fields["carbon_price"]), float(fields["price_cap"]),
                   float(fields["renewable_subsidy"]))


@dataclass(frozen=True)
class GeneratorBid:
    price_bid: float
    capacity_offered: float
    maintenance: bool

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> "GeneratorBid":
        return cls(float(fields["price_bid"]), float(fields["capacity_offered"]),
                   bool(fields.get("maintenance", False)))


@dataclass(frozen=True)
class RetailerDemand:
    demand_bid: float
    max_price: float

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> "RetailerDemand":
        return cls(float(fields["demand_bid"]), float(fields["max_price"]))
