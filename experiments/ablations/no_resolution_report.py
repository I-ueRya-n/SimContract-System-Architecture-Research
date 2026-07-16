"""Paper 2 ablation A1: withhold the adapter-returned ResolutionReport.

Protocol: docs/protocols/p2_ablation_no_resolution_report.md. Paired
within-run design: every resolved role-decision slot yields the intact
report (oracle) and an ablated reconstruction computed from an
engine-visible view only. Explicit wrapper; production code is untouched.

Usage:
  python experiments/ablations/no_resolution_report.py --pilot   # 1 domain, 3 seeds
  python experiments/ablations/no_resolution_report.py           # confirmatory matrix
  python experiments/ablations/no_resolution_report.py --verify  # recompute aggregates
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from simcontract.contracts import Action, ControllerResult
from simcontract.engine.session import SessionRunner
from simcontract.composition import create_registry, domain_assets

RESULTS_DIR = Path(__file__).resolve().parents[2] / "paper2_evidence" / "p2_ablation_no_resolution_report"
UNRESOLVED = "__unresolved__"

# Injected cases per role capability (protocol section 4).
BASE_CASES = ["valid_action", "missing_submission", "controller_failure",
              "syntactic_rejection"]
SEMANTIC_ROLES = {"generator", "region_manager"}   # roles with a reachable adapter-tier rejection


def cases_for_role(role: str) -> list[str]:
    return BASE_CASES + (["semantic_rejection"] if role in SEMANTIC_ROLES else [])


class ScriptedCaseController:
    """Deterministic case-injecting controller (failure-as-data pattern)."""

    condition = "scripted_case"

    def __init__(self, slot_index: int):
        self._slot_index = slot_index

    def case_for(self, role: str, round_no: int) -> str:
        cases = cases_for_role(role)
        return cases[(self._slot_index + round_no - 1) % len(cases)]

    def act(self, view, slot, candidates, previews, ctx) -> ControllerResult:
        role = candidates[0].role
        case = self.case_for(role, ctx.round_no)
        base = candidates[0]
        if case == "valid_action":
            return ControllerResult(action=base)
        if case == "missing_submission":
            return ControllerResult(action=None, fallback_reason="controller_absent")
        if case == "controller_failure":
            return ControllerResult(action=None, fallback_reason="controller_exception")
        if case == "syntactic_rejection":
            fields = dict(base.fields)
            for key, value in fields.items():
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    fields[key] = 1e9          # beyond every schema max
                    break
            return ControllerResult(action=Action(role=role, slot=slot, fields=fields))
        if case == "semantic_rejection":
            if role == "generator":            # maintenance_conflict: schema-valid
                fields = dict(base.fields)
                fields.update({"capacity_offered": 10.0, "maintenance": True})
            elif role == "region_manager":     # shares_not_normalised: each share in [0,1]
                fields = {"share_testing": 0.5, "share_vaccination": 0.5,
                          "share_capacity": 0.3}
            else:  # pragma: no cover - schedule never assigns this case elsewhere
                return ControllerResult(action=base)
            return ControllerResult(action=Action(role=role, slot=slot, fields=fields))
        raise ValueError(f"unknown case {case!r}")  # pragma: no cover


class CaptureSink:
    """Collects everything; the ablated view is built from the engine-visible subset."""

    def __init__(self):
        self.rounds, self.decisions, self.events, self.invocations = [], [], [], []

    def record_round(self, record):      self.rounds.append(record)
    def record_decision(self, record):   self.decisions.append(record)
    def record_event(self, record):      self.events.append(record)
    def record_invocation(self, record): self.invocations.append(record)
    def finalise(self, manifest, extra=None): ...


def engine_visible_view(sink: CaptureSink, round_no: int, slot: str) -> dict:
    """Only what the engine observes at intake: decisions, validation failures,
    fallback events. Never the resolution report or resolved actions."""
    decision = next((d for d in sink.decisions
                     if d.round_no == round_no and d.slot == slot), None)
    validate_failure = next((e for e in sink.events
                             if e.round_no == round_no and e.slot == slot
                             and e.stage == "validate"), None)
    select_failure = next((e for e in sink.events
                           if e.round_no == round_no and e.slot == slot
                           and e.stage == "select"), None)
    view = {
        "condition": decision.condition if decision else None,
        "submitted_digest": decision.selected_digest if decision else None,
        "validate_failure": ({"reason": validate_failure.reason,
                              "family": validate_failure.family}
                             if validate_failure else None),
        "select_failure": ({"reason": select_failure.reason}
                           if select_failure else None),
    }
    assert "resolution" not in view and "resolved_actions" not in view  # negative access test
    return view


def reconstruct(view: dict) -> dict:
    """Ablated reconstruction from the engine-visible view alone."""
    if view["validate_failure"] is not None:
        stage = ("adapter_semantic" if view["validate_failure"]["family"] == "adapter"
                 else "engine_syntactic")
        return {"final_action": UNRESOLVED, "source_tag": "domain_default",
                "completed": True, "completion_reason": "rejected_upstream",
                "rejection_stage": stage}
    if view["select_failure"] is not None or view["submitted_digest"] is None:
        return {"final_action": UNRESOLVED, "source_tag": "domain_default",
                "completed": True, "completion_reason": "no_accepted_action",
                "rejection_stage": None}
    return {"final_action": view["submitted_digest"],
            "source_tag": view["condition"], "completed": False,
            "completion_reason": None, "rejection_stage": None}


def oracle_from_report(resolution: dict, slot: str) -> dict:
    completed = slot in resolution["completed"]
    if completed:
        final = resolution["completed"][slot]
    else:
        final = resolution["accepted"].get(slot, UNRESOLVED)
    rejected = resolution["rejected"].get(slot)
    return {"final_action": final,
            "source_tag": resolution["sources"].get(slot, UNRESOLVED),
            "completed": completed,
            "completion_reason": resolution["completion_reasons"].get(slot),
            "rejection_stage": rejected["stage"] if rejected else None}


def wilson_ci(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.959964, k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def run_matrix(domains: list[str], seeds: range, rounds: int) -> list[dict]:
    registry = create_registry()
    per_slot: list[dict] = []
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=Path(__file__).resolve().parents[2]
                            ).stdout.strip()
    for domain_id in domains:
        adapter = registry.create(domain_id)
        schema, observation, catalog, _ = domain_assets(domain_id)
        scenarios = list(adapter.manifest.scenario_ids)
        slots = [s for r in adapter.roles for s in r.slots()]
        slot_roles = {s: r.role for r in adapter.roles for s in r.slots()}
        for scenario_id in scenarios:
            for seed in seeds:
                unassigned = slots[seed % len(slots)]        # domain_completion case
                controllers = {s: ScriptedCaseController(i)
                               for i, s in enumerate(slots) if s != unassigned}
                sink = CaptureSink()
                runner = SessionRunner(registry.create(domain_id), schema,
                                       observation, catalog, sink=sink)
                result = runner.run(scenario_id=scenario_id, run_seed=seed,
                                    rounds=rounds, controllers=controllers,
                                    personas={})
                for record in sink.rounds:
                    for slot in slots:
                        role = slot_roles[slot]
                        if slot == unassigned:
                            case = "domain_completion"
                        else:
                            case = controllers[slot].case_for(role, record.round_no)
                        oracle = oracle_from_report(record.resolution, slot)
                        inferred = reconstruct(
                            engine_visible_view(sink, record.round_no, slot))
                        flags = {f: oracle[f] == inferred[f] for f in
                                 ("final_action", "source_tag", "completed",
                                  "completion_reason", "rejection_stage")}
                        per_slot.append({
                            "software_commit": commit, "domain_id": domain_id,
                            "scenario_id": scenario_id, "seed": seed,
                            "round_no": record.round_no, "slot": slot,
                            "role": role, "case_id": case,
                            "oracle": oracle, "inferred": inferred,
                            "field_match": flags,
                            "complete_exact_match": all(flags.values()),
                            "unresolved_fields": [k for k, v in inferred.items()
                                                  if v == UNRESOLVED],
                        })
    return per_slot


def aggregate(per_slot: list[dict]) -> dict:
    n = len(per_slot)
    exact = sum(r["complete_exact_match"] for r in per_slot)
    fields = ("final_action", "source_tag", "completed",
              "completion_reason", "rejection_stage")
    agg = {"total_slots": n,
           "complete_exact_match": {"count": exact, "rate": exact / n,
                                    "wilson95": wilson_ci(exact, n)},
           "field_accuracy": {}, "by_case": {}, "by_domain": {},
           "unresolved_final_action_rate":
               sum("final_action" in r["unresolved_fields"] for r in per_slot) / n}
    for f in fields:
        k = sum(r["field_match"][f] for r in per_slot)
        agg["field_accuracy"][f] = {"count": k, "rate": k / n,
                                    "wilson95": wilson_ci(k, n)}
    for key, sel in (("by_case", "case_id"), ("by_domain", "domain_id")):
        groups = defaultdict(list)
        for r in per_slot:
            groups[r[sel]].append(r)
        for g, rows in sorted(groups.items()):
            k = sum(r["complete_exact_match"] for r in rows)
            fa = sum(r["field_match"]["final_action"] for r in rows)
            agg[key][g] = {"slots": len(rows), "exact_match": k,
                           "exact_rate": k / len(rows),
                           "final_action_match": fa,
                           "final_action_rate": fa / len(rows)}
    return agg


def write_outputs(per_slot: list[dict], agg: dict, args_desc: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "per_slot_results.jsonl", "w") as f:
        for row in per_slot:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with open(RESULTS_DIR / "aggregate_results.json", "w") as f:
        json.dump(agg, f, indent=2, sort_keys=True)
    confusion = Counter((r["oracle"]["source_tag"], r["inferred"]["source_tag"])
                        for r in per_slot)
    with open(RESULTS_DIR / "source_tag_confusion.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["oracle_source", "inferred_source", "count"])
        for (o, i), c in sorted(confusion.items()):
            w.writerow([o, i, c])
    for name, key in (("case_breakdown.csv", "by_case"),
                      ("domain_breakdown.csv", "by_domain")):
        with open(RESULTS_DIR / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["group", "slots", "exact_match", "exact_rate",
                        "final_action_match", "final_action_rate"])
            for g, v in agg[key].items():
                w.writerow([g, v["slots"], v["exact_match"],
                            f"{v['exact_rate']:.4f}", v["final_action_match"],
                            f"{v['final_action_rate']:.4f}"])
    env = {"python": sys.version.split()[0], "platform": platform.platform(),
           "matrix": args_desc,
           "software_commit": per_slot[0]["software_commit"] if per_slot else None}
    with open(RESULTS_DIR / "environment.json", "w") as f:
        json.dump(env, f, indent=2)
    with open(RESULTS_DIR / "run_manifest.json", "w") as f:
        json.dump({"records": len(per_slot),
                   "per_slot_sha256": hashlib.sha256(
                       (RESULTS_DIR / "per_slot_results.jsonl").read_bytes()
                   ).hexdigest()}, f, indent=2)


def verify() -> int:
    per_slot = [json.loads(line) for line in
                open(RESULTS_DIR / "per_slot_results.jsonl")]
    stored = json.load(open(RESULTS_DIR / "aggregate_results.json"))
    recomputed = aggregate(per_slot)
    stored_j = json.dumps(stored, sort_keys=True)
    recomputed_j = json.dumps(json.loads(json.dumps(recomputed)), sort_keys=True)
    ok = stored_j == recomputed_j
    print(f"[A1 verify] aggregates match per-slot records: {ok}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true",
                    help="energy domain only, seeds 1-3 (excluded from confirmatory)")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        return verify()
    if args.pilot:
        domains, seeds, desc = ["energy_market_v1"], range(1, 4), "pilot: energy x 2 scen x 3 seeds x 6 rounds"
    else:
        domains, seeds, desc = (["energy_market_v1", "epidemic_policy_v1"],
                                range(1, 31),
                                "confirmatory: 2 domains x 2 scenarios x 30 seeds x 6 rounds")
    per_slot = run_matrix(domains, seeds, rounds=6)
    agg = aggregate(per_slot)
    write_outputs(per_slot, agg, desc)
    print(f"[A1] slots={agg['total_slots']} "
          f"exact={agg['complete_exact_match']['count']} "
          f"({agg['complete_exact_match']['rate']:.3f}) "
          f"final_action={agg['field_accuracy']['final_action']['rate']:.3f} "
          f"source_tag={agg['field_accuracy']['source_tag']['rate']:.3f}")
    for case, v in agg["by_case"].items():
        print(f"  case {case:22s} slots={v['slots']:5d} exact_rate={v['exact_rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
