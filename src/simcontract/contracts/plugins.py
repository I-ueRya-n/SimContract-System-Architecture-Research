"""Plugin contracts (ADR 0005): registry protocol, factory type, load errors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from .adapter import SimulationAdapter
from .domain_manifest import DomainManifest

AdapterFactory = Callable[[], SimulationAdapter]


@dataclass(frozen=True)
class PluginLoadError(Exception):
    """Structured discovery/registration failure; never partially registers."""

    plugin_id: str
    origin: str          # "builtin" or the distribution name
    error_type: str      # duplicate_id | incompatible_contract | substitution | load_failed
    detail: str

    def __str__(self) -> str:  # pragma: no cover - repr convenience
        return f"[{self.error_type}] {self.plugin_id} ({self.origin}): {self.detail}"


@runtime_checkable
class DomainRegistry(Protocol):
    def register(self, domain_id: str, factory: AdapterFactory,
                 origin: str = "builtin") -> None: ...

    def create(self, domain_id: str) -> SimulationAdapter: ...

    def aliases(self) -> list[str]: ...

    def manifests(self) -> list[DomainManifest]: ...
