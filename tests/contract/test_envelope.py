"""ActionEnvelope construction and engine-tier envelope validation."""
from __future__ import annotations

from simcontract.composition import create_registry
from simcontract.contracts import Action, ActionEnvelope
from simcontract.engine import build_envelope, validate_envelope


def _adapter():
    return create_registry().create("reference_stub")


def test_envelope_round_trip_and_digest_stability():
    adapter = _adapter()
    action = Action(role="agent", slot="agent_1", fields={"delta": 2})
    env = build_envelope(adapter.manifest, adapter.adapter_version, "1", action)
    assert env.domain_id == adapter.domain_id
    assert env.schema_id == adapter.manifest.action_schema_ids["agent"]
    assert env.to_action("agent_1") == action
    assert env.digest() == build_envelope(adapter.manifest,
                                          adapter.adapter_version, "1",
                                          action).digest()


def test_envelope_validation_accepts_engine_built():
    adapter = _adapter()
    action = Action(role="agent", slot="agent_1", fields={"delta": 2})
    env = build_envelope(adapter.manifest, adapter.adapter_version, "1", action)
    assert validate_envelope(env, adapter.manifest) is None


def test_envelope_validation_rejects_foreign_context():
    adapter = _adapter()
    manifest = adapter.manifest
    good = build_envelope(manifest, adapter.adapter_version, "1",
                          Action(role="agent", slot="agent_1", fields={"delta": 1}))

    wrong_domain = ActionEnvelope("other_domain", good.domain_version,
                                  good.schema_id, good.role_id, good.stage_id,
                                  good.action_type, good.payload)
    rej = validate_envelope(wrong_domain, manifest)
    assert rej is not None and rej.code == "domain_mismatch"
    assert rej.stage == "engine_syntactic"

    wrong_role = ActionEnvelope(good.domain_id, good.domain_version,
                                good.schema_id, "nonexistent_role", good.stage_id,
                                good.action_type, good.payload)
    assert validate_envelope(wrong_role, manifest).code == "role_unknown"

    wrong_schema = ActionEnvelope(good.domain_id, good.domain_version,
                                  "stale_schema_v0", good.role_id, good.stage_id,
                                  good.action_type, good.payload)
    assert validate_envelope(wrong_schema, manifest).code == "schema_mismatch"

    wrong_stage = ActionEnvelope(good.domain_id, good.domain_version,
                                 good.schema_id, good.role_id, "99",
                                 good.action_type, good.payload)
    assert validate_envelope(wrong_stage, manifest).code == "stage_unknown"
