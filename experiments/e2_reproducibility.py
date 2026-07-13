"""E2: fixed-seed rerun identity + replay-from-bundle equivalence (RQ4).

Usage: PYTHONPATH=src python3 experiments/e2_reproducibility.py [alias]
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import BundleView
from simcontract.engine import RandomValidController, SessionRunner, replay_bundle
from simcontract.evidence import write_bundle


def run(alias: str = "energy_market_v1", seed: int = 73, rounds: int = 5) -> int:
    def one(name: str, tmp: Path) -> Path:
        adapter = create_registry().create(alias)
        schema, obs, catalog, _ = domain_assets(alias)
        controllers = {slot: RandomValidController()
                       for role in adapter.roles for slot in role.slots()}
        result = SessionRunner(adapter, schema, obs, catalog).run(
            scenario_id=adapter.manifest.scenario_ids[0], run_seed=seed,
            rounds=rounds, controllers=controllers, personas={})
        return write_bundle(result, tmp / name)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        h = lambda d: json.loads((d / "manifest.json").read_text())["content_hash"]
        a, b = one("a", tmp), one("b", tmp)
        identical = h(a) == h(b)
        print(f"[E2] {alias} rerun identity: {'PASS' if identical else 'FAIL'} ({h(a)[:12]})")

        bundle = BundleView.load(a)
        adapter = create_registry().create(alias)
        schema, obs, catalog, _ = domain_assets(alias)
        report = replay_bundle(bundle, adapter, schema, obs, catalog)
        print(f"[E2] {alias} replay equivalence: "
              f"{'PASS' if report.equivalent else 'FAIL'} "
              f"({report.equal_rounds}/{report.rounds_compared} rounds)")
        return 0 if identical and report.equivalent else 1


if __name__ == "__main__":
    sys.exit(run(*(sys.argv[1:2] or ["energy_market_v1"])))
