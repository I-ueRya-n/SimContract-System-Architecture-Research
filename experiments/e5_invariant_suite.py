"""E5: SC-I1..I7 checked over every evidence bundle under a directory.

Usage: PYTHONPATH=src python3 experiments/e5_invariant_suite.py [bundle_root]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from simcontract.contracts import SOURCE_TAGS, BundleView

ROOT = Path(__file__).resolve().parents[1]


def check_bundle(d: Path) -> dict[str, bool]:
    view = BundleView.load(d)
    rounds, decisions, events = view.rounds, view.decisions, view.events
    register = view.register

    checks: dict[str, bool] = {}
    # SC-I1: both branches present in every round, exogenous digest recorded
    checks["SC-I1"] = all(set(r.branches) == {"authoritative", "applied"}
                          and r.exogenous_digest for r in rounds)
    # SC-I2: every unaccepted slot completed by the domain with a reason
    checks["SC-I2"] = all(
        slot in r.resolution["completion_reasons"]
        for r in rounds
        for slot, tag in r.resolution["sources"].items() if tag == "domain_default")
    # SC-I3: every rejection has a structured event with a reason
    event_keys = {(e.round_no, e.slot) for e in events}
    checks["SC-I3"] = all(
        (r.round_no, slot) in event_keys
        for r in rounds for slot in r.resolution["rejected"])
    # SC-I4: rounds strictly ordered
    checks["SC-I4"] = [r.round_no for r in rounds] == sorted(
        {r.round_no for r in rounds})
    # SC-I5: every source tag from the controlled vocabulary
    checks["SC-I5"] = all(tag in SOURCE_TAGS
                          for r in rounds for tag in r.resolution["sources"].values())
    # SC-I6: every decision carries state digest + candidate set
    checks["SC-I6"] = all(d_.state_digest and d_.candidate_digests is not None
                          for d_ in decisions)
    # SC-I7: register denominators match the records
    denom = register.get("denominators", {})
    checks["SC-I7"] = (denom.get("rounds") == len(rounds)
                       and denom.get("decisions") == len(decisions)
                       and sum(f["count"] for f in register.get("families", {}).values())
                       == len(events))
    return checks


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results"
    bundles = sorted(p.parent for p in root.rglob("manifest.json"))
    if not bundles:
        print(f"[E5] no bundles under {root}")
        return 1

    rows, all_ok = [], True
    for d in bundles:
        checks = check_bundle(d)
        ok = all(checks.values())
        all_ok &= ok
        rows.append({"bundle": str(d.relative_to(ROOT) if d.is_relative_to(ROOT) else d),
                     "checks": checks, "pass": ok})
        failed = [k for k, v in checks.items() if not v]
        print(f"[E5] {'PASS' if ok else 'FAIL ' + str(failed):24s} {d.name}")

    out = ROOT / "results" / "e5_invariant_report.json"
    out.write_text(json.dumps({"bundles": len(rows), "all_pass": all_ok,
                               "rows": rows}, indent=2))
    print(f"[E5] {len(rows)} bundles, all invariants "
          f"{'PASS' if all_ok else 'FAIL'} -> {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
