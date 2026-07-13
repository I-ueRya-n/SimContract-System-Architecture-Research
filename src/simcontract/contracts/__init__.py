"""SimContract contract layer: the comparability and reproducibility boundary.

This package imports nothing from the rest of SimContract (spec section 4).
"""
from .adapter import DefaultActionProvider, SimulationAdapter
from .actions import ActionSchema
from .controllers import ControllerResult, RoleController
from .domain_manifest import DomainManifest, UpstreamModelProvenance
from .core import (
    SOURCE_TAGS,
    Action,
    ActionEnvelope,
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
    EvidenceSink,
    FailureRecord,
    InvocationRecord,
    NullEvidenceSink,
    RoundRecord,
    RunManifest,
)
from .metrics import MetricCatalog
from .observation import ObservationPolicy
from .plugins import AdapterFactory, DomainRegistry, PluginLoadError
from .versioning import CONTRACT_VERSION, EVIDENCE_SCHEMA_VERSION, is_compatible

__all__ = [
    "Action", "ActionEnvelope", "ActionSchema", "AdapterFactory", "BundleView",
    "CONTRACT_VERSION", "ControllerResult", "DecisionRecord",
    "DefaultActionProvider", "DomainManifest", "DomainRegistry",
    "EVIDENCE_SCHEMA_VERSION", "EvidenceSink", "FailureRecord",
    "InvocationRecord", "MetricCatalog", "NullEvidenceSink",
    "ObservationPolicy", "Outcome", "PluginLoadError", "Preview",
    "RejectionInfo", "ResolutionReport", "RoleController", "RoleSpec",
    "RoundRecord", "RunManifest", "SOURCE_TAGS", "SimulationAdapter",
    "SourceTag", "StepContext", "UpstreamModelProvenance", "canonical_json",
    "digest", "is_compatible",
]
