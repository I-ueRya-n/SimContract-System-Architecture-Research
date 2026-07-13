"""Seeding discipline (spec 6.2): the engine derives run → round → slot seeds.

The derivation utilities themselves are contract-level (shared with
controllers); this module is the engine's stable import site for them.
"""
from simcontract.contracts.seeding import derive_seed, rng_for, seeded_softmax_pick

__all__ = ["derive_seed", "rng_for", "seeded_softmax_pick"]
