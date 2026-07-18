"""SUMO Level-1 external architecture-transfer domain identity and manifest.

Protocol: docs/protocols/p2a_sumo_level1_transfer.md. This domain exists to
test whether an independently developed simulator (not designed for
SimContract) can be integrated through the frozen contracts without
modifying the common core -- not to model real traffic behaviour. See the
protocol for the disclosed checkpoint-fidelity limitation and the
authoritative-execution design this manifest supports.
"""
from __future__ import annotations

from simcontract.contracts import CONTRACT_VERSION, RoleSpec
from simcontract.contracts.domain_manifest import DomainManifest, UpstreamModelProvenance

DOMAIN_ID = "sumo_transfer_v1"
ADAPTER_VERSION = "0.1.0"
ROLES = [RoleSpec("traffic_authority", 1, stage=1)]

UPSTREAM = UpstreamModelProvenance(
    project_name="Eclipse SUMO",
    repository_url="https://github.com/eclipse-sumo/sumo",
    release="1.27.1",
    commit_hash=None,
    license_id="EPL-2.0",
    citation="Lopez, P.A. et al. (2018). Microscopic Traffic Simulation "
             "using SUMO. IEEE ITSC.",
    integration_mode="dependency_wrapper",
    source_modified=False,
)

MANIFEST = DomainManifest(
    domain_id=DOMAIN_ID,
    domain_version=ADAPTER_VERSION,
    contract_version=CONTRACT_VERSION,
    origin="third_party_open_source",
    roles=tuple(ROLES),
    stage_order=(1,),
    action_schema_ids={"traffic_authority": "sumo_phase_v1"},
    metric_catalog_id="sumo_metrics_v1",
    observation_policy_id="sumo_observation_v1",
    scenario_ids=("grid3x3_moderate_v1", "grid3x3_dense_v1"),
    upstream=UPSTREAM,
)
