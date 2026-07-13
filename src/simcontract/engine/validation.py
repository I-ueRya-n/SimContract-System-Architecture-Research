"""Engine-tier platform validation (spec 12.1).

The engine validates the platform context (envelope) and the declared
syntax (schema shape, types, ranges, enums). State-dependent legality is the
adapter's tier (spec 12.2); the two tiers never duplicate each other.
"""
from __future__ import annotations

from simcontract.contracts import (
    Action,
    ActionEnvelope,
    ActionSchema,
    DomainManifest,
    RejectionInfo,
)


def build_envelope(manifest: DomainManifest, adapter_version: str, stage_id: str,
                   action: Action) -> ActionEnvelope:
    return ActionEnvelope(
        domain_id=manifest.domain_id,
        domain_version=adapter_version,
        schema_id=manifest.action_schema_ids.get(action.role, ""),
        role_id=action.role,
        stage_id=stage_id,
        action_type=action.role,
        payload=dict(action.fields),
    )


def validate_envelope(envelope: ActionEnvelope,
                      manifest: DomainManifest) -> RejectionInfo | None:
    """Platform-context checks; the future API submits envelopes through here."""
    if envelope.domain_id != manifest.domain_id:
        return RejectionInfo("engine_syntactic", "domain_mismatch",
                             f"envelope addresses {envelope.domain_id!r}, "
                             f"active domain is {manifest.domain_id!r}")
    if envelope.role_id not in manifest.action_schema_ids:
        return RejectionInfo("engine_syntactic", "role_unknown",
                             f"role {envelope.role_id!r} not declared by the manifest")
    declared_schema = manifest.action_schema_ids[envelope.role_id]
    if envelope.schema_id != declared_schema:
        return RejectionInfo("engine_syntactic", "schema_mismatch",
                             f"envelope schema {envelope.schema_id!r}, "
                             f"manifest declares {declared_schema!r}")
    declared_stages = {str(s) for s in manifest.stage_order}
    if envelope.stage_id not in declared_stages:
        return RejectionInfo("engine_syntactic", "stage_unknown",
                             f"stage {envelope.stage_id!r} not in manifest order")
    return None


def validate_intake(envelope: ActionEnvelope, action: Action,
                    manifest: DomainManifest,
                    schema: ActionSchema) -> RejectionInfo | None:
    """Full engine tier: envelope context, then declared payload syntax."""
    rejection = validate_envelope(envelope, manifest)
    if rejection is not None:
        return rejection
    return schema.validate_syntactic(action)
