"""Registry hard rules (ADR 0005): duplicates, substitution, compatibility."""
from __future__ import annotations

import pytest

from simcontract.composition import create_registry
from simcontract.contracts import PluginLoadError
from simcontract.plugins import AdapterRegistry, UnknownDomainError


def test_duplicate_id_rejected():
    registry = create_registry()
    alias = registry.aliases()[0]
    with pytest.raises(PluginLoadError) as err:
        registry.register(alias, lambda: None)
    assert err.value.error_type == "duplicate_id"


def test_unknown_domain_error():
    registry = AdapterRegistry()
    with pytest.raises(UnknownDomainError):
        registry.create("no_such_domain")


def test_substitution_guard():
    registry = create_registry()
    stub_factory = registry._factories["reference_stub"]
    registry.register("impostor_alias", stub_factory)
    with pytest.raises(PluginLoadError) as err:
        registry.create("impostor_alias")
    assert err.value.error_type == "substitution"


def test_incompatible_contract_rejected():
    class _BadManifest:
        contract_version = "999.0.0"

    class _BadAdapter:
        domain_id = "bad_domain"
        manifest = _BadManifest()

    registry = AdapterRegistry()
    registry.register("bad_domain", _BadAdapter)
    with pytest.raises(PluginLoadError) as err:
        registry.create("bad_domain")
    assert err.value.error_type == "incompatible_contract"


def test_deterministic_listing_and_origin():
    registry = create_registry()
    assert registry.aliases() == sorted(registry.aliases())
    for alias in registry.aliases():
        assert registry.origin_of(alias) == "builtin"


def test_manifests_serialisable():
    registry = create_registry()
    for manifest in registry.manifests():
        d = manifest.to_dict()
        assert d["domain_id"] and d["contract_version"]
