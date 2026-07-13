"""SimContract engine: model-agnostic orchestration. Imports contracts only."""
from .controllers import (
    BoundedLlmController,
    FreeLlmController,
    HumanController,
    RandomValidController,
    RuleController,
    TopScoreController,
    persona_score,
)
from .registry import AdapterRegistry, UnknownDomainError
from .replay import ReplayReport, replay_bundle
from .seeding import derive_seed, rng_for, seeded_softmax_pick
from .session import SessionResult, SessionRunner

__all__ = [
    "AdapterRegistry", "BoundedLlmController", "FreeLlmController",
    "HumanController", "RandomValidController", "RuleController",
    "ReplayReport", "SessionResult", "SessionRunner", "TopScoreController", "replay_bundle",
    "UnknownDomainError", "derive_seed", "persona_score", "rng_for",
    "seeded_softmax_pick",
]
