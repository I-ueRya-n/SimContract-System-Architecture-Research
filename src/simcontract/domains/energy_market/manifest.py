"""Domain identity and machine-readable manifest (consolidated spec 9.2)."""
from __future__ import annotations

from simcontract.contracts import CONTRACT_VERSION, RoleSpec
from simcontract.contracts.domain_manifest import DomainManifest

DOMAIN_ID = "energy_market_v1"
ADAPTER_VERSION = "0.2.0"

ROLES = [
    RoleSpec("regulator", 1, stage=1),
    RoleSpec("generator", 3, stage=2),
    RoleSpec("retailer", 2, stage=3),
]

MANIFEST = DomainManifest(
    domain_id=DOMAIN_ID,
    domain_version=ADAPTER_VERSION,
    contract_version=CONTRACT_VERSION,
    origin="self_implemented",
    roles=tuple(ROLES),
    stage_order=(1, 2, 3),
    action_schema_ids={"regulator": "regulator_policy_v1",
                       "generator": "generator_bid_v1",
                       "retailer": "retailer_demand_v1"},
    metric_catalog_id="energy_metrics_v1",
    observation_policy_id="energy_observation_v1",
    scenario_ids=("baseline_v1", "tight_supply_v1"),
)
