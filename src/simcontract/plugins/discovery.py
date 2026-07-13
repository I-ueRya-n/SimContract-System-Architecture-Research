"""Entry-point discovery for external domain plugins (defined, dormant).

Flow (consolidated spec 13.4): installed distribution → entry-point metadata
(group ``simcontract.domains``) → factory loaded → manifest checked →
contract compatibility checked → registry registration. Composition does not
invoke this in Phase 1; a load failure never partially registers a domain.
"""
from __future__ import annotations

from importlib import metadata

from simcontract.contracts import PluginLoadError

from .registry import AdapterRegistry

ENTRY_POINT_GROUP = "simcontract.domains"


def discover_entry_points(registry: AdapterRegistry,
                          group: str = ENTRY_POINT_GROUP) -> list[PluginLoadError]:
    """Register every discoverable external domain; return structured failures."""
    failures: list[PluginLoadError] = []
    try:
        entry_points = metadata.entry_points(group=group)
    except TypeError:  # pragma: no cover - older importlib.metadata API
        entry_points = metadata.entry_points().get(group, [])

    for ep in entry_points:
        origin = getattr(getattr(ep, "dist", None), "name", "unknown-distribution")
        try:
            factory = ep.load()
            registry.register(ep.name, factory, origin=origin)
            registry.create(ep.name)  # manifest + compatibility + substitution checks
        except PluginLoadError as exc:
            registry._factories.pop(ep.name, None)   # never partially register
            registry._origins.pop(ep.name, None)
            failures.append(exc)
        except Exception as exc:  # noqa: BLE001 - isolate arbitrary plugin failures
            registry._factories.pop(ep.name, None)
            registry._origins.pop(ep.name, None)
            failures.append(PluginLoadError(ep.name, origin, "load_failed", repr(exc)))
    return failures
