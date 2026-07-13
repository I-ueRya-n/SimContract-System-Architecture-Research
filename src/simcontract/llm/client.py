"""Minimal OpenAI-compatible chat client with full instrumentation (spec 6.3).

Disabled by default; every call returns an invocation record suitable for
``InvocationRecord``. No API keys are ever persisted.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request


class LlmUnavailable(RuntimeError):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LlmClient:
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 api_key: str | None = None, timeout_s: float = 30.0,
                 max_retries: int = 1):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.model = model
        self._api_key = api_key
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)

    def complete(self, prompt: str, *, temperature: float, round_no: int,
                 slot: str, prompt_version: str, max_tokens: int = 200):
        if not self.enabled:
            raise LlmUnavailable("llm_disabled", "no base_url/model configured")
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_exc: Exception | None = None
        for retry in range(self.max_retries + 1):
            started = time.monotonic()
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions", data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                record = {
                    "model_id": self.model,
                    "prompt_version": prompt_version,
                    "prompt_digest": _digest(prompt),
                    "temperature": temperature,
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "retry_index": retry,
                    "response_digest": _digest(text),
                    "status": "ok",
                }
                return text, record
            except (urllib.error.URLError, TimeoutError, OSError, KeyError,
                    json.JSONDecodeError) as exc:
                last_exc = exc
        raise LlmUnavailable("endpoint_unreachable", str(last_exc))
