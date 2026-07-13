"""Adapter registry: alias -> factory. Knows no concrete domain (ADR 0001)."""
from __future__ import annotations

from typing import Callable

from simcontract.contracts import SimulationAdapter

AdapterFactory = Callable[[], SimulationAdapter]


class UnknownDomainError(KeyError):
    pass


class AdapterRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}

    def register(self, alias: str, factory: AdapterFactory) -> None:
        if alias in self._factories:
            raise ValueError(f"alias {alias!r} already registered")
        self._factories[alias] = factory

    def create(self, alias: str) -> SimulationAdapter:
        try:
            factory = self._factories[alias]
        except KeyError as exc:
            raise UnknownDomainError(
                f"unknown domain alias {alias!r}; known: {sorted(self._factories)}"
            ) from exc
        adapter = factory()
        if adapter.domain_id != alias:
            # substitution guard: a factory must not silently deliver another domain
            raise ValueError(
                f"registry alias {alias!r} produced adapter {adapter.domain_id!r}"
            )
        return adapter

    def aliases(self) -> list[str]:
        return sorted(self._factories)
