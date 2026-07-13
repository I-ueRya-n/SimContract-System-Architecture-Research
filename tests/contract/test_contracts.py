"""Contract layer units: schema validation, catalog, observation."""
from __future__ import annotations

from simcontract.contracts import (
    Action,
    ActionSchema,
    MetricCatalog,
    ObservationPolicy,
)

SCHEMA = ActionSchema({
    "agent": {
        "delta": {"type": "int", "min": -5, "max": 5},
        "mode": {"type": "choice", "choices": ["a", "b"]},
        "flag": {"type": "bool"},
    }
})


def _act(**fields):
    return Action("agent", "agent_1", fields)


def test_valid_action_passes():
    assert SCHEMA.validate_syntactic(_act(delta=3, mode="a", flag=True)) is None


def test_missing_field():
    r = SCHEMA.validate_syntactic(_act(delta=3, mode="a"))
    assert r and r.code == "missing_field" and r.stage == "engine_syntactic"


def test_range_enum_type_and_extra():
    assert SCHEMA.validate_syntactic(_act(delta=9, mode="a", flag=True)).code == "range_error"
    assert SCHEMA.validate_syntactic(_act(delta=1, mode="z", flag=True)).code == "enum_error"
    assert SCHEMA.validate_syntactic(_act(delta=1.5, mode="a", flag=True)).code == "type_error"
    assert SCHEMA.validate_syntactic(
        _act(delta=1, mode="a", flag=True, extra=1)).code == "unknown_field"


def test_sample_candidates_always_valid():
    import random
    for cand in SCHEMA.sample_candidates("agent", "agent_1", random.Random(1), 25):
        assert SCHEMA.validate_syntactic(cand) is None


def test_metric_catalog():
    catalog = MetricCatalog([{"key": "x", "direction": "min"}])
    assert catalog.validate_metrics({"x": 1.0}) == []
    assert catalog.validate_metrics({"x": 1.0, "y": 2.0}) == ["y"]


def test_observation_policy_filters():
    policy = ObservationPolicy({"agent": ["a"], "admin": ["*"]})
    state = {"a": 1, "b": 2}
    assert policy.view(state, "agent") == {"a": 1}
    assert policy.view(state, "admin") == state
