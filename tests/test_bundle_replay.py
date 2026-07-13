"""Bundle writing, content hashing, and replay equivalence (RQ4, spec 8)."""
from __future__ import annotations

import json

from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import BundleView
from simcontract.engine import RandomValidController, SessionRunner, replay_bundle
from simcontract.evidence import write_bundle


def _run(seed: int, tmp_path, name: str):
    adapter = create_registry().create("reference_stub")
    schema, observation, catalog, _ = domain_assets("reference_stub")
    runner = SessionRunner(adapter, schema, observation, catalog)
    result = runner.run(scenario_id="default", run_seed=seed, rounds=4,
                        controllers={"agent_1": RandomValidController()}, personas={})
    return write_bundle(result, tmp_path / name)


def test_content_hash_identity_and_sensitivity(tmp_path):
    d1 = _run(7, tmp_path, "a")
    d2 = _run(7, tmp_path, "b")
    d3 = _run(8, tmp_path, "c")
    h = lambda d: json.loads((d / "manifest.json").read_text())["content_hash"]
    assert h(d1) == h(d2), "same seed must give identical content hash"
    assert h(d1) != h(d3), "different seed must change the content hash"


def test_replay_equivalence(tmp_path):
    d = _run(21, tmp_path, "r")
    bundle = BundleView.load(d)
    adapter = create_registry().create("reference_stub")
    schema, observation, catalog, _ = domain_assets("reference_stub")
    report = replay_bundle(bundle, adapter, schema, observation, catalog)
    assert report.equivalent, report.mismatches


def test_register_denominators(tmp_path):
    d = _run(3, tmp_path, "reg")
    register = json.loads((d / "register.json").read_text())
    assert register["denominators"]["rounds"] == 4
    assert register["denominators"]["decisions"] == 4
