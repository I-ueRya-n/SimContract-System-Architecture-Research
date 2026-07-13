"""Manifest, config snapshot, and domain-manifest files of a bundle."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from simcontract.contracts import RunManifest

from .hashing import write_json


def write_manifest(d: Path, manifest: RunManifest, content_hash: str,
                   file_hashes: dict[str, str]) -> None:
    manifest.content_hash = content_hash
    manifest.file_hashes = dict(file_hashes)
    manifest_dict = asdict(manifest)
    write_json(d / "manifest.json", manifest_dict)


def write_sidecars(d: Path, extra: dict[str, Any] | None) -> dict[str, str]:
    extra = extra or {}
    hashes: dict[str, str] = {}
    if "config_snapshot" in extra:
        hashes["config.snapshot.json"] = write_json(
            d / "config.snapshot.json", extra["config_snapshot"])
    if "domain_manifest" in extra:
        hashes["domain_manifest.json"] = write_json(
            d / "domain_manifest.json", extra["domain_manifest"])
    return hashes
