"""Role controllers: the experiment conditions (spec 6.3).

A controller returns ``(action | None, meta)``. Returning ``None`` signals the
engine to leave the slot unfilled (the adapter completes it, SC-I2) after the
engine records the fallback event (SC-I3).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from simcontract.contracts import Action, Preview, StepContext, digest

from .seeding import rng_for, seeded_softmax_pick

ScoreFn = Callable[[Preview], float]


def persona_score(preview: Preview, weights: dict[str, float]) -> float:
    return sum(w * float(preview.projected_metrics.get(k, 0.0)) for k, w in weights.items())


@dataclass
class ControllerResult:
    action: Action | None
    rationale: str | None = None
    scores: list[float] = field(default_factory=list)
    fallback_reason: str | None = None
    llm_record: dict[str, Any] | None = None


class RuleController:
    condition = "rule"

    def __init__(self, provider, persona: str | None):
        self._provider = provider
        self._persona = persona

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        action = self._provider.action_for(view, slot, self._persona, ctx)
        return ControllerResult(action=action)


class RandomValidController:
    condition = "random_valid"

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        if not candidates:
            return ControllerResult(action=None, fallback_reason="no_candidates")
        rng = rng_for(ctx.round_seed, slot, "random_valid")
        return ControllerResult(action=rng.choice(candidates))


class TopScoreController:
    condition = "top_score"

    def __init__(self, weights: dict[str, float]):
        self._weights = weights

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        if not candidates:
            return ControllerResult(action=None, fallback_reason="no_candidates")
        scores = [persona_score(p, self._weights) for p in previews]
        best = max(range(len(candidates)), key=lambda i: scores[i])
        return ControllerResult(action=candidates[best], scores=scores)


class BoundedLlmController:
    """LLM chooses an index from the ranked shortlist; never emits raw payloads."""

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

    def _build_prompt(self, slot: str, shortlist: list[Action], previews: list[Preview]) -> str:
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


class FreeLlmController:
    """Experiment-only condition: the LLM emits an action payload directly.

    Deliberately violates the bounded pattern so its failure modes can be
    measured. Post-hoc two-tier validation still applies downstream.
    """

    condition = "free_llm"
    PROMPT_VERSION = "free-v1"

    def __init__(self, llm, schema_fields: dict[str, dict[str, Any]],
                 persona: str | None, role: str, temperature: float = 0.2):
        self._llm = llm
        self._fields = schema_fields
        self._persona = persona
        self._role = role
        self._temperature = temperature

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        prompt = (
            f"You are playing role slot {slot} (role {self._role}) with persona "
            f"{self._persona!r}. Reply ONLY with a JSON object for your action fields. "
            f"Field definitions: {json.dumps(self._fields, sort_keys=True, default=str)}"
        )
        try:
            text, record = self._llm.complete(prompt, temperature=self._temperature,
                                              round_no=ctx.round_no, slot=slot,
                                              prompt_version=self.PROMPT_VERSION)
        except Exception as exc:  # noqa: BLE001
            return ControllerResult(action=None,
                                    fallback_reason=getattr(exc, "reason", "llm_unreachable"))
        try:
            start, end = text.index("{"), text.rindex("}") + 1
            fields = json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return ControllerResult(action=None, fallback_reason="response_unparsable",
                                    llm_record=record)
        return ControllerResult(action=Action(role=self._role, slot=slot, fields=fields),
                                rationale=text.strip()[:400], llm_record=record)


class HumanController:
    """Interactive play (CLI). ``input_fn`` supplies field values."""

    condition = "human"

    def __init__(self, input_fn, schema_fields: dict[str, dict[str, Any]], role: str):
        self._input = input_fn
        self._fields = schema_fields
        self._role = role

    def act(self, view, slot, candidates, previews, ctx: StepContext) -> ControllerResult:
        fields = self._input(slot, self._fields, view, candidates)
        if fields is None:
            return ControllerResult(action=None, fallback_reason="human_absent")
        return ControllerResult(action=Action(role=self._role, slot=slot, fields=fields))


def state_digest_of(view: Any) -> str:
    return digest(view)
