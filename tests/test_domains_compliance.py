"""Cross-domain contract compliance (E3 core): every registered domain passes
the same suite, exercised through identical engine code paths."""
from __future__ import annotations

import pytest

from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import SimulationAdapter
from simcontract.engine import (
    RandomValidController,
    RuleController,
    SessionRunner,
    rng_for,
)

ALIASES = ["reference_stub", "energy_market_v1", "epidemic_policy_v1"]


def _scenario(adapter) -> str:
    return adapter.manifest.scenario_ids[0]


@pytest.fixture(params=ALIASES)
def domain(request):
    alias = request.param
    adapter = create_registry().create(alias)
    schema, observation, catalog, weights_for = domain_assets(alias)
    return alias, adapter, schema, observation, catalog


def test_protocol_and_manifest(domain):
    alias, adapter, *_ = domain
    assert isinstance(adapter, SimulationAdapter)
    m = adapter.manifest
    assert m.domain_id == alias
    assert m.origin == "self_implemented"
    assert tuple(sorted({r.stage for r in adapter.roles})) == m.stage_order


def test_candidates_pass_both_validation_tiers(domain):
    alias, adapter, schema, observation, catalog = domain
    state = adapter.initial_state(_scenario(adapter), seed=1)
    for role in adapter.roles:
        for slot in role.slots():
            for cand in adapter.action_space(state, slot, rng_for(1, slot), 6):
                assert schema.validate_syntactic(cand) is None, (alias, slot, cand)
                assert adapter.validate_semantic(state, cand) is None, (alias, slot, cand)


def test_step_emits_branches_and_catalog_metrics(domain):
    alias, adapter, schema, observation, catalog = domain
    runner = SessionRunner(adapter, schema, observation, catalog)
    controllers = {slot: RuleController(adapter.default_action_provider, None)
                   for role in adapter.roles for slot in role.slots()}
    result = runner.run(scenario_id=_scenario(adapter), run_seed=9, rounds=3,
                        controllers=controllers, personas={})
    for r in result.rounds:
        assert set(r.branches) == {"authoritative", "applied"}          # SC-I1
        assert catalog.validate_metrics(r.system_metrics) == []
        assert set(r.resolution["sources"]) == {s for role in adapter.roles
                                                for s in role.slots()}   # SC-I5


def test_all_rule_equals_authoritative(domain):
    """rule == domain defaults, so both branches coincide (SC-I1/SC-I2 link)."""
    alias, adapter, schema, observation, catalog = domain
    runner = SessionRunner(adapter, schema, observation, catalog)
    controllers = {slot: RuleController(adapter.default_action_provider, None)
                   for role in adapter.roles for slot in role.slots()}
    result = runner.run(scenario_id=_scenario(adapter), run_seed=17, rounds=2,
                        controllers=controllers, personas={})
    for r in result.rounds:
        assert r.branches["applied"] == r.branches["authoritative"], alias


def test_same_engine_config_runs_on_every_domain(domain):
    """E3: one experiment configuration, zero engine/analyzer changes."""
    alias, adapter, schema, observation, catalog = domain
    runner = SessionRunner(adapter, schema, observation, catalog)
    controllers = {slot: RandomValidController()
                   for role in adapter.roles for slot in role.slots()}
    result = runner.run(scenario_id=_scenario(adapter), run_seed=23, rounds=2,
                        controllers=controllers, personas={})
    assert len(result.rounds) == 2
    assert len(result.decisions) == 2 * sum(r.count for r in adapter.roles)


def test_determinism_per_domain(domain):
    alias, adapter, schema, observation, catalog = domain
    def go():
        a = create_registry().create(alias)
        s, o, c, _ = domain_assets(alias)
        controllers = {slot: RandomValidController()
                       for role in a.roles for slot in role.slots()}
        return SessionRunner(a, s, o, c).run(scenario_id=_scenario(a), run_seed=31,
                                             rounds=2, controllers=controllers,
                                             personas={})
    x, y = go(), go()
    assert [r.system_metrics for r in x.rounds] == [r.system_metrics for r in y.rounds]
