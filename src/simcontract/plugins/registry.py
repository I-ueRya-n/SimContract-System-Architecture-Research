"""Runtime domain registry (ADR 0005). Knows factories and manifests only.

Hard rules: duplicate ids rejected · contract compatibility checked ·
substitution guarded · deterministic listing · origin recorded. Never
imports a concrete domain module.
"""
from __future__ import annotations

from simcontract.contracts import (
    CONTRACT_VERSION,
    AdapterFactory,
    DomainManifest,
    PluginLoadError,
    SimulationAdapter,
    is_compatible,
)


class UnknownDomainError(KeyError):
    pass


class AdapterRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}
        self._origins: dict[str, str] = {}

    def register(self, domain_id: str, factory: AdapterFactory,
                 origin: str = "builtin") -> None:
        if domain_id in self._factories:
            raise PluginLoadError(domain_id, origin, "duplicate_id",
                                  f"domain id {domain_id!r} already registered "
                                  f"(origin {self._origins[domain_id]!r})")
        self._factories[domain_id] = factory
        self._origins[domain_id] = origin

    def create(self, domain_id: str) -> SimulationAdapter:
        try:
            factory = self._factories[domain_id]
        except KeyError as exc:
            raise UnknownDomainError(
                f"unknown domain id {domain_id!r}; known: {sorted(self._factories)}"
            ) from exc
        adapter = factory()
        origin = self._origins[domain_id]
        if adapter.domain_id != domain_id:
            # substitution guard: a factory must not silently deliver another domain
            raise PluginLoadError(domain_id, origin, "substitution",
                                  f"factory produced adapter {adapter.domain_id!r}")
        declared = adapter.manifest.contract_version
        if not is_compatible(declared, CONTRACT_VERSION):
            raise PluginLoadError(domain_id, origin, "incompatible_contract",
                                  f"declares contract {declared!r}, "
                                  f"platform is {CONTRACT_VERSION!r}")
        return adapter

    def aliases(self) -> list[str]:
        return sorted(self._factories)

    def origin_of(self, domain_id: str) -> str:
        return self._origins[domain_id]

    def manifests(self) -> list[DomainManifest]:
        return [self.create(a).manifest for a in self.aliases()]
