"""E4: controller-condition comparison across domains with paired seeds.

Per condition x domain: invalid-action rate by tier, fallback rate by reason,
decision-source mix, and mean applied-vs-authoritative branch divergence over
shared metrics. Paired seeds give identical exogenous streams per condition.
Without a configured LLM endpoint the LLM conditions run and degrade
observably (failure containment evidence); their decision behaviour is
measured only when an endpoint is configured.

Usage: PYTHONPATH=src python3 experiments/e4_controller_comparison.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from simcontract.composition import create_application

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments" / "configs" / "e4_controller_comparison.yaml"


def divergence(rounds) -> float:
    total, count = 0.0, 0
    for r in rounds:
        auth, appl = r.branches["authoritative"], r.branches["applied"]
        for key in set(auth) & set(appl):
            scale = max(abs(auth[key]), abs(appl[key]), 1e-9)
            total += abs(auth[key] - appl[key]) / scale
            count += 1
    return total / max(count, 1)


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text())
    app = create_application()
    out_root = ROOT / "results" / "e4"
    summary: list[dict] = []

    for domain in config["domains"]:
        for condition in config["conditions"]:
            cells = []
            for seed in config["seeds"]:
                run = app.run_session(
                    domain=domain,
                    scenario=_first_scenario(app, domain),
                    seed=seed, rounds=config["rounds"],
                    conditions={"all": condition}, personas={},
                    out_dir=out_root / domain / condition / f"seed_{seed}",
                    llm_base_url=config.get("llm_base_url"),
                    llm_model=config.get("llm_model"),
                )
                result = run["result"]
                decisions = len(result.decisions) or 1
                rejected = sum(1 for r in result.rounds
                               for _ in r.resolution["rejected"])
                syntactic = sum(1 for r in result.rounds
                                for info in r.resolution["rejected"].values()
                                if info["stage"] == "engine_syntactic")
                fallbacks = len(result.events)
                sources: dict[str, int] = {}
                for r in result.rounds:
                    for tag in r.resolution["sources"].values():
                        sources[tag] = sources.get(tag, 0) + 1
                cells.append({
                    "seed": seed,
                    "content_hash": run["content_hash"],
                    "decision_slots": decisions,
                    "rejected": rejected,
                    "rejected_syntactic": syntactic,
                    "rejected_semantic": rejected - syntactic,
                    "fallback_events": fallbacks,
                    "source_mix": sources,
                    "branch_divergence": round(divergence(result.rounds), 6),
                })
            n = len(cells)
            summary.append({
                "domain": domain, "condition": condition, "runs": n,
                "invalid_rate": round(sum(c["rejected"] / c["decision_slots"]
                                          for c in cells) / n, 4),
                "fallback_per_run": round(sum(c["fallback_events"] for c in cells) / n, 2),
                "mean_divergence": round(sum(c["branch_divergence"] for c in cells) / n, 6),
                "cells": cells,
            })
            row = summary[-1]
            print(f"[E4] {domain:20s} {condition:14s} invalid={row['invalid_rate']:.3f} "
                  f"fallback/run={row['fallback_per_run']:5.1f} "
                  f"divergence={row['mean_divergence']:.4f}")

    out = ROOT / "results" / "e4_summary.json"
    out.write_text(json.dumps({
        "config": config,
        "llm_configured": bool(config.get("llm_base_url")),
        "rows": summary,
    }, indent=2))
    print(f"[E4] summary: {out}")
    if not config.get("llm_base_url"):
        print("[E4] NOTE: no LLM endpoint configured — llm conditions measured "
              "degradation containment only")
    return 0


def _first_scenario(app, domain: str) -> str:
    for d in app.list_domains():
        if d["domain_id"] == domain:
            return d["scenarios"][0]
    raise KeyError(domain)


if __name__ == "__main__":
    sys.exit(main())
