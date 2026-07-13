"""``BundleEvidenceWriter``: the concrete ``EvidenceSink`` (ADR 0004).

Collects records during a run and, at ``finalise``, computes the failure
register and canonical content hash, then writes the full bundle layout of
``docs/evidence_schema.md``. Injected by the composition root; the engine
never instantiates it.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from simcontract.contracts import (
    DecisionRecord,
    FailureRecord,
    InvocationRecord,
    RoundRecord,
    RunManifest,
)

from .failure_register import build_register
from .hashing import content_hash_of, write_json
from .manifest_writer import write_manifest, write_sidecars
from .trace_writer import write_metrics_csv, write_report_html, write_traces


class BundleEvidenceWriter:
    def __init__(self, out_dir: str | Path):
        self.path = Path(out_dir)
        self.rounds: list[RoundRecord] = []
        self.decisions: list[DecisionRecord] = []
        self.events: list[FailureRecord] = []
        self.invocations: list[InvocationRecord] = []
        self.content_hash: str | None = None

    # EvidenceSink protocol -------------------------------------------------
    def record_round(self, record: RoundRecord) -> None:
        self.rounds.append(record)

    def record_decision(self, record: DecisionRecord) -> None:
        self.decisions.append(record)

    def record_event(self, record: FailureRecord) -> None:
        self.events.append(record)

    def record_invocation(self, record: InvocationRecord) -> None:
        self.invocations.append(record)

    def finalise(self, manifest: RunManifest,
                 extra: dict[str, Any] | None = None) -> None:
        d = self.path
        d.mkdir(parents=True, exist_ok=True)

        register = build_register(self.events, self.decisions,
                                  self.rounds, self.invocations)
        payload = {
            "rounds": [asdict(r) for r in self.rounds],
            "decisions": [asdict(r) for r in self.decisions],
            "events": [asdict(r) for r in self.events],
            "invocations": [asdict(r) for r in self.invocations],
            "register": register,
        }
        self.content_hash = content_hash_of(asdict(manifest), payload)

        file_hashes: dict[str, str] = {}
        file_hashes["rounds.json"] = write_json(d / "rounds.json", payload["rounds"])
        file_hashes.update(write_traces(d, self.decisions, self.events,
                                        self.invocations))
        file_hashes["register.json"] = write_json(d / "register.json", register)
        file_hashes["metrics.csv"] = write_metrics_csv(d, self.rounds)
        file_hashes.update(write_sidecars(d, extra))

        write_manifest(d, manifest, self.content_hash, file_hashes)
        write_report_html(d, manifest, self.rounds, register)


def write_bundle(result: Any, out_dir: str | Path,
                 extra: dict[str, Any] | None = None) -> Path:
    """Convenience: persist an in-memory ``SessionResult``-shaped object."""
    writer = BundleEvidenceWriter(out_dir)
    for r in result.rounds:
        writer.record_round(r)
    for r in result.decisions:
        writer.record_decision(r)
    for r in result.events:
        writer.record_event(r)
    for r in result.invocations:
        writer.record_invocation(r)
    writer.finalise(result.manifest, extra)
    return writer.path
