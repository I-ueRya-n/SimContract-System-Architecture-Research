"""Concrete controller conditions (spec 6.3, ADR 0003).

Each module implements one experimental condition behind the
``RoleController`` contract. Controllers propose or select actions; they
never mutate model state and never bypass the two validation tiers.
"""
from ._scoring import persona_score
from .bounded_llm import BoundedLlmController
from .free_llm import FreeLlmController
from .human import HumanController
from .human_script import ScriptedHumanController
from .random_valid import RandomValidController
from .rule import RuleController
from .top_score import TopScoreController

__all__ = [
    "BoundedLlmController", "FreeLlmController", "HumanController",
    "RandomValidController", "RuleController", "ScriptedHumanController",
    "TopScoreController", "persona_score",
]
