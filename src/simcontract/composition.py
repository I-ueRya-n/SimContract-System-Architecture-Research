"""Composition root (ADR 0001/0005).

The single module that imports concrete implementations across layers and
wires them together. Nothing imports this module except entry points (CLI,
experiments).
"""
from __future__ import annotations

import os
from pathlib import Path

from simcontract.analysis import default_registry as _default_analyzers
from simcontract.application import Application
from simcontract.llm import LlmClient
from simcontract.plugins import AdapterRegistry


def load_dotenv(path: str | Path = ".env") -> None:
    """Load ``KEY=VALUE`` lines from a ``.env`` file into the environment.

    Entry-point convenience only (no third-party dependency): existing
    environment variables always win, so a value already exported is never
    overwritten. The ``.env`` file is git-ignored; secrets never enter the
    repository. Missing file is a no-op.
    """
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


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


def create_application(load_env: bool = True) -> Application:
    # Entry points may enable an OpenAI-compatible endpoint via SIMCONTRACT_LLM_*
    # (a git-ignored .env, see .env.example). Explicit CLI flags still override
    # the environment. When nothing is configured the LLM client stays disabled
    # and LLM controllers degrade observably (SC-I3).
    if load_env:
        load_dotenv()
    return Application(
        registry=create_registry(),
        assets_for=domain_assets,
        analyzers=_default_analyzers(),
        llm_factory=lambda base_url=None, model=None: LlmClient.from_env(base_url, model),
    )
