"""Domain identity and machine-readable manifest (consolidated spec 9.2)."""
from __future__ import annotations

from simcontract.contracts import CONTRACT_VERSION, RoleSpec
from simcontract.contracts.domain_manifest import DomainManifest

DOMAIN_ID = "epidemic_policy_v1"
ADAPTER_VERSION = "0.2.0"

ROLES = [
    RoleSpec("health_authority", 1, stage=1),
    RoleSpec("region_manager", 3, stage=2),
]

MANIFEST = DomainManifest(
    domain_id=DOMAIN_ID,
    domain_version=ADAPTER_VERSION,
    contract_version=CONTRACT_VERSION,
    origin="self_implemented",
    roles=tuple(ROLES),
    stage_order=(1, 2),
    action_schema_ids={"health_authority": "health_policy_v1",
                       "region_manager": "regional_allocation_v1"},
    metric_catalog_id="epidemic_metrics_v1",
    observation_policy_id="epidemic_observation_v1",
    scenario_ids=("seed_outbreak_v1", "second_wave_v1"),
)
