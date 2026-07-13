"""SimContract engine: domain-neutral orchestration. Imports contracts only.

Concrete controllers live in ``simcontract.controllers``; the registry lives
in ``simcontract.plugins`` (ADR 0003). The engine sees protocols only.
"""
from .preview import candidates_and_previews
from .replay_executor import ReplayReport, replay_bundle
from .seeding import derive_seed, rng_for, seeded_softmax_pick
from .session import SessionResult, SessionRunner
from .validation import build_envelope, validate_envelope, validate_intake

__all__ = [
    "ReplayReport", "SessionResult", "SessionRunner", "build_envelope",
    "candidates_and_previews", "derive_seed", "replay_bundle", "rng_for",
    "seeded_softmax_pick", "validate_envelope", "validate_intake",
]
