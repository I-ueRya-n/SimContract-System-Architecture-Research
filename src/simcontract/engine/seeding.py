"""Seeding discipline (spec 6.2): stable derivation, no ambient randomness."""
from __future__ import annotations

import hashlib
import random


def derive_seed(*parts: object) -> int:
    material = "\x1f".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def rng_for(*parts: object) -> random.Random:
    return random.Random(derive_seed(*parts))


def seeded_softmax_pick(scores: list[float], temperature: float, *seed_parts: object) -> int:
    """Deterministic softmax sampling over scores; index of the pick."""
    if not scores:
        raise ValueError("no scores to pick from")
    if temperature <= 1e-9 or len(scores) == 1:
        return max(range(len(scores)), key=lambda i: scores[i])
    m = max(scores)
    weights = [pow(2.718281828, (s - m) / temperature) for s in scores]
    total = sum(weights)
    r = rng_for(*seed_parts).random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if r <= acc:
            return i
    return len(scores) - 1
