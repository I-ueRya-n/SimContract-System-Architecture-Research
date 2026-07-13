"""E3: cross-domain contract portability — one experiment config, every domain.

Usage: PYTHONPATH=src python3 experiments/e3_contract_swap.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from simcontract.analysis import default_registry, write_report
from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import BundleView
from simcontract.controllers import RuleController
from simcontract.engine import SessionRunner
from simcontract.evidence import write_bundle

CONFIG = {"rounds": 4, "seed": 42}   # ONE config; the domain alias is the only change


def run() -> int:
    registry = create_registry()
    bundles = []
    with tempfile.TemporaryDirectory() as tmp:
        for alias in registry.aliases():
            adapter = registry.create(alias)
            schema, obs, catalog, _ = domain_assets(alias)
            controllers = {slot: RuleController(adapter.default_action_provider, None)
                           for role in adapter.roles for slot in role.slots()}
            result = SessionRunner(adapter, schema, obs, catalog).run(
                scenario_id=adapter.manifest.scenario_ids[0],
                run_seed=CONFIG["seed"], rounds=CONFIG["rounds"],
                controllers=controllers, personas={})
            out = write_bundle(result, Path(tmp) / alias)
            bundles.append(BundleView.load(out))
            print(f"[E3] {alias}: {CONFIG['rounds']} rounds OK, "
                  f"metrics={sorted(result.rounds[-1].system_metrics)[:3]}...")

        analyzer_reg = default_registry()
        results = [analyzer_reg.get(a).run(bundles) for a in analyzer_reg.ids()]
        report = write_report(results, "results/e3_analysis")
        print(f"[E3] same analyzers over all domains -> {report}")
    print("[E3] cross-domain contract portability: PASS "
          "(zero engine or analyzer changes across domains)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
