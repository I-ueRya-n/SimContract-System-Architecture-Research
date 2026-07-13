"""``free_llm`` condition (experiment-only): the LLM authors the payload.

Deliberately violates the bounded pattern so its failure modes can be
measured; two-tier validation still applies downstream. Never available in
interactive play.
"""
from __future__ import annotations

import json
from typing import Any

from simcontract.contracts import Action, ControllerResult, StepContext


class FreeLlmController:
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
