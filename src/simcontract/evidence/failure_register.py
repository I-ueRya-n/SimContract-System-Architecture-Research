"""Run-level failure register with explicit denominators (SC-I7)."""
from __future__ import annotations

from simcontract.contracts import DecisionRecord, FailureRecord, InvocationRecord, RoundRecord


def build_register(events: list[FailureRecord], decisions: list[DecisionRecord],
                   rounds: list[RoundRecord],
                   invocations: list[InvocationRecord]) -> dict:
    families: dict[str, dict] = {}
    for ev in events:
        fam = families.setdefault(ev.family, {"count": 0, "reasons": {}})
        fam["count"] += 1
        fam["reasons"][ev.reason] = fam["reasons"].get(ev.reason, 0) + 1
    return {
        "families": families,
        "denominators": {
            "decisions": len(decisions),
            "rounds": len(rounds),
            "llm_invocations": len(invocations),
        },
    }
