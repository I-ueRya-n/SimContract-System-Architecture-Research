"""Stub transition: ``value' = clamp(value + delta + drift)`` (spec 7.0)."""
from __future__ import annotations

BOUND = 100


def transition(value: int, delta: int, drift: int) -> int:
    nxt = value + delta + drift
    return max(-BOUND, min(BOUND, nxt))
