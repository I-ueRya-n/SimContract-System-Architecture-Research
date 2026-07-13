"""Engine + stub adapter: invariants SC-I1..I7 at the unit level."""
from __future__ import annotations

from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import Action
from simcontract.engine import (
    RandomValidController,
    RuleController,
    SessionRunner,
)


def _runner():
    adapter = create_registry().create("reference_stub")
    schema, observation, catalog, _ = domain_assets("reference_stub")
    return adapter, SessionRunner(adapter, schema, observation, catalog)


def _rule_controllers(adapter):
    return {slot: RuleController(adapter.default_action_provider, None)
            for role in adapter.roles for slot in role.slots()}


def test_all_rule_branches_identical():
    """SC-I1: with all-default decisions, applied == authoritative every round."""
    adapter, runner = _runner()
    result = runner.run(scenario_id="default", run_seed=11, rounds=6,
                        controllers=_rule_controllers(adapter), personas={})
    assert len(result.rounds) == 6
    for r in result.rounds:
        assert r.branches["applied"] == r.branches["authoritative"]
        assert r.resolution["sources"]["agent_1"] == "rule"          # SC-I5


def test_missing_controller_completed_by_domain():
    """SC-I2: unassigned slot -> domain default, reported by the adapter."""
    adapter, runner = _runner()
    result = runner.run(scenario_id="default", run_seed=11, rounds=3,
                        controllers={}, personas={})
    for r in result.rounds:
        assert r.resolution["sources"]["agent_1"] == "domain_default"
        assert r.resolution["completed"], "completion must be reported"
        assert r.resolution["completion_reasons"]["agent_1"] == "no_accepted_action"


class _NoneController:
    condition = "rule"

    def act(self, view, slot, candidates, previews, ctx):
        from simcontract.engine.controllers import ControllerResult
        return ControllerResult(action=None, fallback_reason="human_absent")


def test_controller_failure_is_recorded_and_completed():
    """SC-I3: failure emits a structured event; adapter still completes."""
    adapter, runner = _runner()
    result = runner.run(scenario_id="default", run_seed=5, rounds=2,
                        controllers={"agent_1": _NoneController()}, personas={})
    assert len(result.events) == 2
    assert {e.reason for e in result.events} == {"human_absent"}
    for r in result.rounds:
        assert r.resolution["sources"]["agent_1"] == "domain_default"


class _InvalidController:
    condition = "rule"

    def act(self, view, slot, candidates, previews, ctx):
        from simcontract.engine.controllers import ControllerResult
        return ControllerResult(action=Action("agent", slot, {"delta": 99}))


def test_engine_syntactic_rejection():
    """Two-tier validation: out-of-range action rejected at the engine tier."""
    adapter, runner = _runner()
    result = runner.run(scenario_id="default", run_seed=5, rounds=1,
                        controllers={"agent_1": _InvalidController()}, personas={})
    rejected = result.rounds[0].resolution["rejected"]["agent_1"]
    assert rejected["stage"] == "engine_syntactic"
    assert rejected["code"] == "range_error"
    assert result.rounds[0].resolution["sources"]["agent_1"] == "domain_default"


def test_adapter_semantic_rejection_direct():
    adapter, _ = _runner()
    rejection = adapter.validate_semantic({"value": 98}, Action("agent", "agent_1", {"delta": 5}))
    assert rejection is not None and rejection.stage == "adapter_semantic"


def test_determinism_same_seed_same_records():
    """SC + RQ4: fixed seed, stochastic controller -> identical outputs."""
    adapter, runner = _runner()
    controllers = {"agent_1": RandomValidController()}
    a = runner.run(scenario_id="default", run_seed=42, rounds=5,
                   controllers=controllers, personas={})
    adapter2 = create_registry().create("reference_stub")
    schema, observation, catalog, _ = domain_assets("reference_stub")
    b = SessionRunner(adapter2, schema, observation, catalog).run(
        scenario_id="default", run_seed=42, rounds=5,
        controllers={"agent_1": RandomValidController()}, personas={})
    assert [r.system_metrics for r in a.rounds] == [r.system_metrics for r in b.rounds]
    assert [r.branches for r in a.rounds] == [r.branches for r in b.rounds]
