"""Machine-readable domain manifest (spec 5.7)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .core import RoleSpec


@dataclass(frozen=True)
class UpstreamModelProvenance:
    project_name: str
    repository_url: str
    release: str | None
    commit_hash: str | None
    license_id: str
    citation: str | None
    integration_mode: str          # dependency_wrapper | subprocess | fork
    source_modified: bool
    modification_summary: str | None = None


@dataclass(frozen=True)
class DomainManifest:
    domain_id: str
    domain_version: str
    contract_version: str
    origin: str                    # self_implemented | third_party_open_source
    roles: tuple[RoleSpec, ...]
    stage_order: tuple[int, ...]
    action_schema_ids: dict[str, str] = field(default_factory=dict)
    metric_catalog_id: str = ""
    observation_policy_id: str = ""
    scenario_ids: tuple[str, ...] = ()
    upstream: UpstreamModelProvenance | None = None

    def to_dict(self) -> dict:
        return asdict(self)
