"""E7 --- governed AI participation vertical slice.

Two halves that together earn the "governed AI participation" claim:

  A. LIVE (needs a configured, reachable endpoint): a real bounded-LLM run in
     which the model selects an index from a validated shortlist for every
     role slot; each selection is re-validated, resolved by the adapter, and
     recorded with `bounded_llm` provenance + instrumentation. The live run is
     then replayed to show it stays deterministically reconstructable from its
     recorded decisions. Skipped cleanly when no endpoint is configured.

  B. DETERMINISTIC (always runs, no endpoint): mock language models exercise
     the containment guarantees regardless of any live model ---
       * bounded_llm + unparseable reply  -> deterministic softmax pick,
         a valid shortlist action, no invalid action ever emitted;
       * free_llm + malformed JSON        -> response_unparsable fallback,
         domain default completes the slot, run still completes.

Usage: PYTHONPATH=src python3 experiments/e7_governed_ai_slice.py
Outputs a committed summary at paper1_evidence/governed_ai_slice.json.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from simcontract.composition import (
    create_application,
    create_registry,
    domain_assets,
    load_dotenv,
)
from simcontract.contracts import ControllerResult
from simcontract.controllers import BoundedLlmController, FreeLlmController
from simcontract.engine import SessionRunner
from simcontract.llm import LlmClient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper1_evidence"
DOMAIN, SCENARIO = "energy_market_v1", "baseline_v1"


class _MockLlm:
    """Deterministic stand-in: always returns a fixed reply, never a network call."""

    def __init__(self, reply: str):
        self._reply = reply

    def complete(self, prompt, *, temperature, round_no, slot, prompt_version,
                 max_tokens=None):
        record = {"model_id": "mock", "prompt_version": prompt_version,
                  "prompt_digest": "mock", "temperature": temperature,
                  "input_tokens": None, "output_tokens": None, "latency_ms": 0,
                  "retry_index": 0, "response_digest": "mock", "status": "mock"}
        return self._reply, record


# ---- A. live governed participation -----------------------------------------
def live_slice() -> dict:
    load_dotenv()
    app = create_application()
    probe = LlmClient.from_env()
    if not probe.enabled:
        return {"ran": False, "reason": "no endpoint configured (SIMCONTRACT_LLM_*)"}

    run = app.run_session(
        domain=DOMAIN, scenario=SCENARIO, seed=73, rounds=3,
        conditions={"all": "bounded_llm"}, personas={"regulator_1": "decarb_first"},
        out_dir=OUT / "_live" / DOMAIN)
    result = run["result"]
    inv = result.invocations
    if not inv:
        return {"ran": True, "endpoint_reached": False,
                "note": "endpoint configured but produced no ok invocations"}

    lat = sorted(i.latency_ms for i in inv)
    sources: dict[str, int] = {}
    for r in result.rounds:
        for tag in r.resolution["sources"].values():
            sources[tag] = sources.get(tag, 0) + 1
    replay = app.replay_run(run["bundle"])
    return {
        "ran": True, "endpoint_reached": True,
        "model_id": inv[0].model_id,
        "invocations": len(inv),
        "all_ok": all(i.status == "ok" for i in inv),
        "latency_ms_median": lat[len(lat) // 2],
        "latency_ms_p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
        "latency_ms_max": lat[-1],
        "resolved_action_sources": sources,
        "fallbacks": len(result.events),
        "replay_rounds": replay.rounds_compared,
        "replay_equal": replay.equal_rounds,
        "replay_equivalent": replay.equivalent,
    }


# ---- B. deterministic containment -------------------------------------------
def _parts(alias):
    a = create_registry().create(alias)
    s, o, c, w = domain_assets(alias)
    return a, s, o, c, w


def containment() -> dict:
    rows = {}

    # bounded_llm with an unparseable reply -> deterministic valid softmax pick
    a, s, o, c, w = _parts(DOMAIN)
    ctrls = {}
    for role in a.roles:
        for slot in role.slots():
            ctrls[slot] = BoundedLlmController(_MockLlm("banana, no number here"),
                                               w(role.role, None), None)
    res = SessionRunner(a, s, o, c).run(scenario_id=SCENARIO, run_seed=1, rounds=2,
                                        controllers=ctrls, personas={})
    invalid = sum(len(r.resolution["rejected"]) for r in res.rounds)
    all_bounded = all(t == "bounded_llm" for r in res.rounds
                      for t in r.resolution["sources"].values())
    rows["bounded_unparseable"] = {
        "invalid_actions_emitted": invalid,          # must be 0
        "all_slots_bounded_llm": all_bounded,        # softmax fallback still a valid pick
        "run_completed": True,
    }

    # free_llm with malformed JSON -> response_unparsable -> domain completion
    a, s, o, c, w = _parts(DOMAIN)
    role0 = a.roles[0]
    slot0 = role0.slots()[0]
    ctrls = {slot0: FreeLlmController(_MockLlm("not json at all"),
                                      s.fields_for(role0.role), None, role0.role)}
    res = SessionRunner(a, s, o, c).run(scenario_id=SCENARIO, run_seed=1, rounds=1,
                                        controllers=ctrls, personas={})
    r0 = res.rounds[0]
    rows["free_malformed"] = {
        "fallback_reason": next((e.reason for e in res.events), None),
        "completed_by_default": r0.resolution["sources"][slot0] == "domain_default",
        "run_completed": True,
    }
    return rows


def main() -> int:
    OUT.mkdir(exist_ok=True)
    summary = {"live_governed_participation": live_slice(),
               "deterministic_containment": containment()}
    (OUT / "governed_ai_slice.json").write_text(json.dumps(summary, indent=2))

    live = summary["live_governed_participation"]
    cont = summary["deterministic_containment"]
    if live.get("endpoint_reached"):
        print(f"[E7-live] {live['model_id']}: {live['invocations']} selections, "
              f"all_ok={live['all_ok']}, sources={live['resolved_action_sources']}, "
              f"fallbacks={live['fallbacks']}, latency md/p95/max="
              f"{live['latency_ms_median']}/{live['latency_ms_p95']}/{live['latency_ms_max']}ms, "
              f"replay {live['replay_equal']}/{live['replay_rounds']} "
              f"{'EQUIVALENT' if live['replay_equivalent'] else 'MISMATCH'}")
    else:
        print(f"[E7-live] skipped: {live.get('reason') or live.get('note')}")
    print(f"[E7-containment] bounded/unparseable -> invalid actions="
          f"{cont['bounded_unparseable']['invalid_actions_emitted']} "
          f"(all slots bounded_llm={cont['bounded_unparseable']['all_slots_bounded_llm']}); "
          f"free/malformed -> {cont['free_malformed']['fallback_reason']} -> "
          f"default completion={cont['free_malformed']['completed_by_default']}")
    print(f"[E7] summary -> {OUT/'governed_ai_slice.json'}")

    ok = (cont["bounded_unparseable"]["invalid_actions_emitted"] == 0
          and cont["free_malformed"]["completed_by_default"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
