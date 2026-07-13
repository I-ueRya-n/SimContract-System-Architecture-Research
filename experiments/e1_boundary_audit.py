"""E1: machine-checked boundary audit (docs/experiment_protocol.md).

Reports every cross-layer import edge, the composition-root exception, and
the domain-token scan over core layers. Exit 0 only if all rules hold.

Usage: PYTHONPATH=src python3 experiments/e1_boundary_audit.py
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "simcontract"
sys.path.insert(0, str(ROOT / "tests" / "dependency"))

from test_dependency_rules import FORBIDDEN, _imports_of  # noqa: E402
from test_token_leakage import CORE_LAYERS, _PATTERN  # noqa: E402


def main() -> int:
    edges: dict[str, sorted] = {}
    violations: list[str] = []
    for py in SRC.rglob("*.py"):
        rel = py.relative_to(SRC).as_posix()
        internal = sorted(i for i in _imports_of(py) if i.startswith("simcontract"))
        if internal:
            edges[rel] = internal
        layer = rel.split("/", 1)[0].removesuffix(".py")
        for bad in FORBIDDEN.get(layer, []):
            for imported in internal:
                if imported == bad or imported.startswith(bad + "."):
                    violations.append(f"{rel} imports {imported}")

    token_hits: list[str] = []
    for layer in CORE_LAYERS:
        for py in (SRC / layer).rglob("*.py"):
            for i, line in enumerate(py.read_text().splitlines(), 1):
                m = _PATTERN.search(line)
                if m:
                    token_hits.append(f"{py.relative_to(SRC)}:{i}:{m.group(0)}")

    composition_imports = sorted(
        i for i in _imports_of(SRC / "composition.py")
        if i.startswith("simcontract.domains"))

    report = {
        "modules_audited": len(list(SRC.rglob("*.py"))),
        "import_edges": edges,
        "forbidden_violations": violations,
        "token_leaks_in_core": token_hits,
        "composition_root_domain_imports": composition_imports,
    }
    out = ROOT / "results" / "e1_boundary_audit.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    ok = not violations and not token_hits
    print(f"[E1] modules audited: {report['modules_audited']}")
    print(f"[E1] forbidden import edges: {len(violations)}")
    print(f"[E1] domain-token leaks in core layers: {len(token_hits)}")
    print(f"[E1] composition-root exception (only domain-import site): "
          f"{composition_imports}")
    print(f"[E1] report: {out}")
    print(f"[E1] boundary audit: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
