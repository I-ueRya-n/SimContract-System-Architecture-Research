"""Composition root (ADR 0001/0005).

The single module that imports concrete implementations across layers and
wires them together. Nothing imports this module except entry points (CLI,
experiments).
"""
from __future__ import annotations

from simcontract.analysis import default_registry as _default_analyzers
from simcontract.application import Application
from simcontract.llm import LlmClient
from simcontract.plugins import AdapterRegistry


def create_registry() -> AdapterRegistry:
    registry = AdapterRegistry()

    from simcontract.domains.reference_stub import ReferenceStubAdapter
    registry.register("reference_stub", ReferenceStubAdapter, origin="builtin")

    # Research domains are registered as they are implemented (architecture
    # first, models second — see docs/spec.md section 7).
    try:
        from simcontract.domains.energy_market import EnergyMarketAdapter
        registry.register("energy_market_v1", EnergyMarketAdapter, origin="builtin")
    except ImportError:  # pragma: no cover - domain not yet present
        pass
    try:
        from simcontract.domains.epidemic_policy import EpidemicPolicyAdapter
        registry.register("epidemic_policy_v1", EpidemicPolicyAdapter, origin="builtin")
    except ImportError:  # pragma: no cover - domain not yet present
        pass

    # External entry-point discovery stays dormant in Phase 1 (ADR 0005).
    return registry


def domain_assets(alias: str):
    """Return (schema, observation, catalog, personas_weights_for) for an alias."""
    if alias == "reference_stub":
        from simcontract.domains import reference_stub as d
        return d.schema(), d.observation(), d.catalog(), lambda role, persona: {"value_abs": -1.0}
    if alias == "energy_market_v1":
        from simcontract.domains import energy_market as d
        return d.schema(), d.observation(), d.catalog(), d.weights_for
    if alias == "epidemic_policy_v1":
        from simcontract.domains import epidemic_policy as d
        return d.schema(), d.observation(), d.catalog(), d.weights_for
    raise KeyError(f"unknown domain alias {alias!r}")


def create_application() -> Application:
    return Application(
        registry=create_registry(),
        assets_for=domain_assets,
        analyzers=_default_analyzers(),
        llm_factory=lambda base_url=None, model=None: LlmClient(base_url, model),
    )
