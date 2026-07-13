"""Bundle loading and verification without execution (replay mode 3)."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from simcontract.contracts import BundleView

from .failure_register import build_register
from .hashing import content_hash_of, file_hash_of


def load_bundle(bundle_dir: str | Path) -> BundleView:
    return BundleView.load(bundle_dir)


def verify_bundle(bundle_dir: str | Path) -> dict:
    """Recompute file hashes and the canonical content hash; no execution."""
    d = Path(bundle_dir)
    view = BundleView.load(d)
    manifest = view.manifest

    file_results: dict[str, bool] = {}
    for name, recorded in (manifest.file_hashes or {}).items():
        path = d / name
        file_results[name] = path.exists() and file_hash_of(path) == recorded

    register = build_register(view.events, view.decisions,
                              view.rounds, view.invocations)
    payload = {
        "rounds": [asdict(r) for r in view.rounds],
        "decisions": [asdict(r) for r in view.decisions],
        "events": [asdict(r) for r in view.events],
        "invocations": [asdict(r) for r in view.invocations],
        "register": register,
    }
    recomputed = content_hash_of(asdict(manifest), payload)
    return {
        "bundle": str(d),
        "content_hash_recorded": manifest.content_hash,
        "content_hash_recomputed": recomputed,
        "content_hash_ok": recomputed == manifest.content_hash,
        "files_ok": all(file_results.values()) and bool(file_results),
        "files": file_results,
    }
