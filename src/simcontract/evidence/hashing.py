"""Canonical bundle identity (docs/evidence_schema.md, ADR 0004).

The content hash covers manifest + records under canonical serialisation
with volatile fields (``content_hash``, ``file_hashes``, ``created_at``)
nulled; per-file hashes are recorded separately.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from simcontract.contracts import canonical_json


def write_json(path: Path, obj: Any) -> str:
    """Write pretty JSON; return its SHA-256 file hash."""
    text = json.dumps(obj, indent=2, sort_keys=True, default=str)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> str:
    """Write one canonical JSON object per line; return the file hash."""
    text = "".join(canonical_json(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash_of(manifest_dict: dict, payload: dict) -> str:
    manifest_dict = dict(manifest_dict)
    manifest_dict["content_hash"] = None
    manifest_dict["file_hashes"] = {}
    manifest_dict["created_at"] = ""          # volatile; excluded from identity
    return hashlib.sha256(
        canonical_json({"manifest": manifest_dict, **payload}).encode("utf-8")
    ).hexdigest()


def file_hash_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
