"""SimContract contract layer: the comparability and reproducibility boundary.

This package imports nothing from the rest of SimContract (spec section 4).
"""
from .adapter import DefaultActionProvider, SimulationAdapter
from .actions import ActionSchema
from .domain_manifest import DomainManifest, UpstreamModelProvenance
from .core import (
    SOURCE_TAGS,
    Action,
    Outcome,
    Preview,
    RejectionInfo,
    ResolutionReport,
    RoleSpec,
    SourceTag,
    StepContext,
    canonical_json,
    digest,
)
from .evidence import (
    BundleView,
    DecisionRecord,
    FailureRecord,
    InvocationRecord,
    RoundRecord,
    RunManifest,
)
from .metrics import MetricCatalog
from .observation import ObservationPolicy
from .versioning import CONTRACT_VERSION

__all__ = [
    "Action", "ActionSchema", "BundleView", "CONTRACT_VERSION",
    "DecisionRecord", "DefaultActionProvider", "DomainManifest", "FailureRecord",
    "InvocationRecord", "MetricCatalog", "ObservationPolicy", "Outcome",
    "Preview", "RejectionInfo", "ResolutionReport", "RoleSpec", "RoundRecord",
    "RunManifest", "SOURCE_TAGS", "SimulationAdapter", "SourceTag",
    "StepContext", "UpstreamModelProvenance", "canonical_json", "digest",
]
