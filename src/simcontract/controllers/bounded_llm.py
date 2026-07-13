"""``bounded_llm`` condition: the LLM chooses an index from the ranked,
validated shortlist; it never authors payloads. Unavailable or unparsable
replies degrade to a deterministic seeded-softmax pick within the shortlist.
"""
from __future__ import annotations

import json

from simcontract.contracts import Action, ControllerResult, Preview, StepContext
from simcontract.contracts.seeding import seeded_softmax_pick

from ._scoring import persona_score


class BoundedLlmController:
    condition = "bounded_llm"
    PROMPT_VERSION = "bounded-v1"

    def __init__(self, llm, weights: dict[str, float], persona: str | None,
                 shortlist_size: int = 5, temperature: float = 0.2):
        self._llm = llm
        self._weights = weights
        self._persona = persona
        self._k = shortlist_size
        self._temperature = temperature

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        if not candidates:
            return ControllerResult(action=None, fallback_reason="no_candidates")
        scores = [persona_score(p, self._weights) for p in previews]
        order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)[: self._k]
        shortlist = [candidates[i] for i in order]
        prompt = self._build_prompt(slot, shortlist, [previews[i] for i in order])
        try:
            text, record = self._llm.complete(prompt, temperature=self._temperature,
                                              round_no=ctx.round_no, slot=slot,
                                              prompt_version=self.PROMPT_VERSION)
        except Exception as exc:  # noqa: BLE001 - degradation is data (SC-I3)
            return ControllerResult(action=None,
                                    fallback_reason=getattr(exc, "reason", "llm_unreachable"))
        index = self._parse_index(text, len(shortlist))
        if index is None:
            # deterministic tie-safe fallback within the shortlist
            index = seeded_softmax_pick([scores[i] for i in order], self._temperature,
                                        ctx.round_seed, slot, "bounded_llm")
            rationale = "unparsable LLM reply; deterministic softmax over shortlist"
        else:
            rationale = text.strip()[:400]
        return ControllerResult(action=shortlist[index], rationale=rationale,
                                scores=[scores[i] for i in order], llm_record=record)

    def _build_prompt(self, slot: str, shortlist: list[Action],
                      previews: list[Preview]) -> str:
        lines = [
            f"You are playing role slot {slot} with persona {self._persona!r} in a "
            "round-based simulation. Choose exactly one candidate action by replying "
            "with its number only.",
        ]
        for i, (a, p) in enumerate(zip(shortlist, previews), start=1):
            lines.append(f"{i}. fields={json.dumps(a.fields, sort_keys=True)} "
                         f"projected={json.dumps(p.projected_metrics, sort_keys=True)}")
        lines.append("Answer with a single integer between 1 and "
                     f"{len(shortlist)}.")
        return "\n".join(lines)

    @staticmethod
    def _parse_index(text: str, n: int) -> int | None:
        for token in text.replace(".", " ").split():
            if token.isdigit():
                value = int(token)
                if 1 <= value <= n:
                    return value - 1
        return None
