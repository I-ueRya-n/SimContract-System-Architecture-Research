"""Stable evidence schema (spec 5.6).

Both the evidence writer and every analyzer depend on this module and on
nothing else of each other. Storage format changes must keep these views
constructible.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class DecisionRecord:
    round_no: int
    role: str
    slot: str
    condition: str
    persona: str | None
    candidate_digests: list[str]
    scores: list[float]
    selected_digest: str | None
    source_tag: str
    rationale: str | None
    state_digest: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureRecord:
    round_no: int
    slot: str | None
    stage: str          # suggest | select | validate | resolve
    family: str         # controller | llm | adapter
    reason: str
    detail: str = ""


@dataclass
class InvocationRecord:
    round_no: int
    slot: str
    model_id: str
    prompt_version: str
    prompt_digest: str
    temperature: float
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    retry_index: int
    response_digest: str | None
    status: str


@dataclass
class RoundRecord:
    round_no: int
    round_seed: int
    exogenous_digest: str
    system_metrics: dict[str, float]
    branches: dict[str, dict[str, float]]
    resolution: dict[str, Any]
    # Full resolved action set (accepted + domain-completed), required so that
    # replay can re-execute the engine path (digests are not invertible).
    resolved_actions: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class RunManifest:
    run_id: str
    domain_id: str
    scenario_id: str
    contract_version: str
    adapter_version: str
    run_seed: int
    rounds: int
    conditions: dict[str, str]           # slot -> condition
    personas: dict[str, str | None]
    config_digest: str
    evidence_schema_version: str = "1.0.0"
    content_hash: str | None = None      # canonical hash, computed pre-embed
    file_hashes: dict[str, str] = field(default_factory=dict)
    claim_boundary: str = (
        "Architecture, traceability, and reproducibility evidence only; no claim of "
        "external behavioural validity for either domain model."
    )
    created_at: str = ""


class EvidenceSink(Protocol):
    """The engine's only view of evidence persistence (ADR 0004).

    Composition injects a concrete writer; the engine never instantiates one.
    """

    def record_round(self, record: RoundRecord) -> None: ...

    def record_decision(self, record: DecisionRecord) -> None: ...

    def record_event(self, record: FailureRecord) -> None: ...

    def record_invocation(self, record: InvocationRecord) -> None: ...

    def finalise(self, manifest: RunManifest,
                 extra: dict[str, Any] | None = None) -> None: ...


class NullEvidenceSink:
    """No-op sink for in-memory runs (tests, previews)."""

    def record_round(self, record: RoundRecord) -> None: ...

    def record_decision(self, record: DecisionRecord) -> None: ...

    def record_event(self, record: FailureRecord) -> None: ...

    def record_invocation(self, record: InvocationRecord) -> None: ...

    def finalise(self, manifest: RunManifest,
                 extra: dict[str, Any] | None = None) -> None: ...


@dataclass
class BundleView:
    """Read-only view over one evidence bundle directory."""

    manifest: RunManifest
    rounds: list[RoundRecord]
    decisions: list[DecisionRecord]
    events: list[FailureRecord]
    invocations: list[InvocationRecord]
    register: dict[str, Any]

    @classmethod
    def load(cls, bundle_dir: str | Path) -> "BundleView":
        d = Path(bundle_dir)

        def _read(name: str) -> Any:
            with open(d / name, "r", encoding="utf-8") as fh:
                return json.load(fh)

        def _read_jsonl(name: str) -> list[dict]:
            path = d / name
            if not path.exists():
                return []
            with open(path, "r", encoding="utf-8") as fh:
                return [json.loads(line) for line in fh if line.strip()]

        manifest = RunManifest(**_read("manifest.json"))
        rounds = [RoundRecord(**r) for r in _read("rounds.json")]
        decisions = [DecisionRecord(**r) for r in _read_jsonl("decisions.jsonl")]
        events = [FailureRecord(**r) for r in _read_jsonl("fallback_events.jsonl")]
        invocations = [InvocationRecord(**r) for r in _read_jsonl("llm_invocations.jsonl")]
        register = _read("register.json")
        return cls(manifest, rounds, decisions, events, invocations, register)

    def to_dicts(self) -> dict[str, Any]:
        return {
            "manifest": asdict(self.manifest),
            "rounds": [asdict(r) for r in self.rounds],
            "decisions": [asdict(r) for r in self.decisions],
            "events": [asdict(r) for r in self.events],
            "invocations": [asdict(r) for r in self.invocations],
            "register": self.register,
        }
