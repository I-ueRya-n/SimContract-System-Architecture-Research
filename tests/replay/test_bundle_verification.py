"""Bundle verification (replay mode 3): hash checks without execution."""
from __future__ import annotations

from simcontract.composition import create_registry, domain_assets
from simcontract.controllers import RuleController
from simcontract.engine import SessionRunner
from simcontract.evidence import BundleEvidenceWriter, verify_bundle


def _bundle(tmp_path, name="v"):
    adapter = create_registry().create("reference_stub")
    schema, observation, catalog, _ = domain_assets("reference_stub")
    writer = BundleEvidenceWriter(tmp_path / name)
    runner = SessionRunner(adapter, schema, observation, catalog, sink=writer)
    runner.run(scenario_id="default", run_seed=17, rounds=3,
               controllers={"agent_1": RuleController(adapter.default_action_provider, None)},
               personas={})
    return writer.path


def test_verify_intact_bundle(tmp_path):
    d = _bundle(tmp_path)
    verdict = verify_bundle(d)
    assert verdict["content_hash_ok"], verdict
    assert verdict["files_ok"], verdict


def test_verify_detects_tampering(tmp_path):
    d = _bundle(tmp_path, "t")
    rounds = (d / "rounds.json").read_text()
    tampered = rounds.replace('"round_no": 1', '"round_no": 9', 1)
    assert tampered != rounds, "tamper target not found"
    (d / "rounds.json").write_text(tampered)
    verdict = verify_bundle(d)
    assert not (verdict["content_hash_ok"] and verdict["files_ok"]), verdict


def test_sink_records_expected_layout(tmp_path):
    d = _bundle(tmp_path, "layout")
    for name in ["manifest.json", "config.snapshot.json", "domain_manifest.json",
                 "rounds.json", "decisions.jsonl", "fallback_events.jsonl",
                 "llm_invocations.jsonl", "register.json", "metrics.csv",
                 "report.html"]:
        assert (d / name).exists(), f"missing {name}"
