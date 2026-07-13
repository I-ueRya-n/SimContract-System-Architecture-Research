"""Plugin layer: runtime registry and (dormant) entry-point discovery (ADR 0005)."""
from .discovery import discover_entry_points
from .registry import AdapterRegistry, UnknownDomainError

__all__ = ["AdapterRegistry", "UnknownDomainError", "discover_entry_points"]
