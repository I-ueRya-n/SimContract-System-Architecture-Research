"""Analyzer protocol and registry (spec 9). Analyzers consume BundleViews only."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from simcontract.contracts import BundleView, digest


@dataclass(frozen=True)
class AnalyzerSpec:
    analysis_id: str
    version: str
    supported_domains: str | tuple[str, ...] = "*"   # "*" = domain-neutral
    requires_records: tuple[str, ...] = ()


@dataclass
class AnalysisResult:
    spec: AnalyzerSpec
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)


def supports(spec: AnalyzerSpec, domain_id: str) -> bool:
    return spec.supported_domains == "*" or domain_id in spec.supported_domains


def make_lineage(spec: AnalyzerSpec, bundles: list[BundleView],
                 parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "analysis_id": spec.analysis_id,
        "analysis_version": spec.version,
        "input_bundle_hashes": [b.manifest.content_hash for b in bundles],
        "parameter_digest": digest(parameters or {}),
    }
