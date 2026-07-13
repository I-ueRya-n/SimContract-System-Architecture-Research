"""Negative paths (consolidated spec 27.4): malformed payloads, semantic
violations, unavailable LLMs, script exhaustion — all observable, none fatal."""
from __future__ import annotations

from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import Action, ControllerResult
from simcontract.controllers import BoundedLlmController, ScriptedHumanController
from simcontract.engine import SessionRunner
from simcontract.llm import LlmClient


def _runner(alias: str):
    adapter = create_registry().create(alias)
    schema, observation, catalog, _ = domain_assets(alias)
    return adapter, SessionRunner(adapter, schema, observation, catalog)


class _FixedController:
    condition = "human"

    def __init__(self, fields, role):
        self._fields = fields
        self._role = role

    def act(self, view, slot, candidates, previews, ctx) -> ControllerResult:
        return ControllerResult(action=Action(self._role, slot, dict(self._fields)))


def test_syntactic_rejection_recorded_with_tier():
    adapter, runner = _runner("reference_stub")
    controllers = {"agent_1": _FixedController({"delta": 99}, "agent")}  # out of range
    result = runner.run(scenario_id="default", run_seed=3, rounds=1,
                        controllers=controllers, personas={})
    (event,) = [e for e in result.events if e.stage == "validate"]
    assert event.reason == "range_error"
    rejected = result.rounds[0].resolution["rejected"]["agent_1"]
    assert rejected["stage"] == "engine_syntactic"
    # slot still completed by the domain default (SC-I2)
    assert result.rounds[0].resolution["sources"]["agent_1"] == "domain_default"
    assert result.rounds[0].resolution["completion_reasons"]["agent_1"] == "rejected_upstream"


def test_semantic_rejection_recorded_with_tier():
    adapter, runner = _runner("epidemic_policy_v1")
    bad = {"share_testing": 0.9, "share_vaccination": 0.9, "share_capacity": 0.9}
    controllers = {"region_manager_1": _FixedController(bad, "region_manager")}
    result = runner.run(scenario_id=adapter.manifest.scenario_ids[0], run_seed=3,
                        rounds=1, controllers=controllers, personas={})
    rejected = result.rounds[0].resolution["rejected"]["region_manager_1"]
    assert rejected["stage"] == "adapter_semantic"
    assert rejected["code"] == "shares_not_normalised"


def test_llm_unreachable_degrades_observably():
    adapter, runner = _runner("reference_stub")
    llm = LlmClient(base_url=None)   # disabled client: every call raises
    controllers = {"agent_1": BoundedLlmController(llm, {"value_abs": -1.0}, None)}
    result = runner.run(scenario_id="default", run_seed=5, rounds=2,
                        controllers=controllers, personas={})
    reasons = {e.reason for e in result.events}
    assert "llm_disabled" in reasons or "llm_unreachable" in reasons
    for r in result.rounds:  # run completed with domain defaults (SC-I2)
        assert r.resolution["sources"]["agent_1"] == "domain_default"


def test_script_exhaustion_falls_back():
    adapter, runner = _runner("reference_stub")
    controllers = {"agent_1": ScriptedHumanController({1: {"delta": 1}}, "agent")}
    result = runner.run(scenario_id="default", run_seed=5, rounds=3,
                        controllers=controllers, personas={})
    assert result.rounds[0].resolution["sources"]["agent_1"] == "human_script"
    assert result.rounds[1].resolution["sources"]["agent_1"] == "domain_default"
    assert "script_exhausted" in {e.reason for e in result.events}


def test_register_denominators_present():
    adapter, runner = _runner("reference_stub")
    controllers = {"agent_1": _FixedController({"delta": 99}, "agent")}
    result = runner.run(scenario_id="default", run_seed=3, rounds=2,
                        controllers=controllers, personas={})
    from simcontract.evidence import build_register
    register = build_register(result.events, result.decisions,
                              result.rounds, result.invocations)
    assert register["denominators"]["rounds"] == 2
    assert register["denominators"]["decisions"] == 2
    assert sum(f["count"] for f in register["families"].values()) == len(result.events)
