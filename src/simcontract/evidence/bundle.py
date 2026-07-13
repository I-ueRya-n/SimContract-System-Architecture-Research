"""Evidence bundle writer (spec 8): canonical content hash + file hashes."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from typing import Any

from simcontract.contracts import canonical_json


def _write_json(path: Path, obj) -> str:
    text = json.dumps(obj, indent=2, sort_keys=True, default=str)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_register(result: Any) -> dict:
    families: dict[str, dict] = {}
    for ev in result.events:
        fam = families.setdefault(ev.family, {"count": 0, "reasons": {}})
        fam["count"] += 1
        fam["reasons"][ev.reason] = fam["reasons"].get(ev.reason, 0) + 1
    return {
        "families": families,
        "denominators": {
            "decisions": len(result.decisions),
            "rounds": len(result.rounds),
            "llm_invocations": len(result.invocations),
        },
    }


def write_bundle(result: Any, out_dir: str | Path) -> Path:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)

    payload = {
        "rounds": [asdict(r) for r in result.rounds],
        "decisions": [asdict(r) for r in result.decisions],
        "events": [asdict(r) for r in result.events],
        "invocations": [asdict(r) for r in result.invocations],
        "register": build_register(result),
    }

    # canonical content hash: manifest (sans hash fields) + payload
    manifest_dict = asdict(result.manifest)
    manifest_dict["content_hash"] = None
    manifest_dict["file_hashes"] = {}
    manifest_dict["created_at"] = ""          # volatile; excluded from identity
    content_hash = hashlib.sha256(
        canonical_json({"manifest": manifest_dict, **payload}).encode("utf-8")
    ).hexdigest()

    file_hashes = {
        "rounds.json": _write_json(d / "rounds.json", payload["rounds"]),
        "decisions.json": _write_json(d / "decisions.json", payload["decisions"]),
        "events.json": _write_json(d / "events.json", payload["events"]),
        "invocations.json": _write_json(d / "invocations.json", payload["invocations"]),
        "register.json": _write_json(d / "register.json", payload["register"]),
    }
    manifest_dict = asdict(result.manifest)
    manifest_dict["content_hash"] = content_hash
    manifest_dict["file_hashes"] = file_hashes
    _write_json(d / "manifest.json", manifest_dict)
    return d
