"""Stub identity and manifest. NOT a research domain (spec 7.0)."""
from __future__ import annotations

from simcontract.contracts import CONTRACT_VERSION, RoleSpec
from simcontract.contracts.domain_manifest import DomainManifest

DOMAIN_ID = "reference_stub"
ADAPTER_VERSION = "0.2.0"
ROLES = [RoleSpec("agent", 1, stage=1)]

MANIFEST = DomainManifest(
    domain_id=DOMAIN_ID,
    domain_version=ADAPTER_VERSION,
    contract_version=CONTRACT_VERSION,
    origin="self_implemented",
    roles=tuple(ROLES),
    stage_order=(1,),
    action_schema_ids={"agent": "stub_delta_v1"},
    metric_catalog_id="stub_metrics_v1",
    observation_policy_id="stub_observation_v1",
    scenario_ids=("default",),
)
