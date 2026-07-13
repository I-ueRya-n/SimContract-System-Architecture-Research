"""E1 core: dependency rules of spec section 4, enforced by AST import audit."""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "simcontract"

FORBIDDEN = {
    "contracts": ["simcontract.engine", "simcontract.evidence", "simcontract.analysis",
                  "simcontract.domains", "simcontract.composition", "simcontract.llm"],
    "engine": ["simcontract.domains", "simcontract.analysis", "simcontract.composition"],
    "evidence": ["simcontract.domains", "simcontract.analysis", "simcontract.engine",
                 "simcontract.composition"],
    "analysis": ["simcontract.domains", "simcontract.engine", "simcontract.evidence",
                 "simcontract.composition"],
    "domains": ["simcontract.engine", "simcontract.evidence", "simcontract.analysis",
                "simcontract.composition"],
}


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def test_dependency_rules():
    violations = []
    for package, forbidden in FORBIDDEN.items():
        for py in (SRC / package).rglob("*.py"):
            for imported in _imports_of(py):
                for bad in forbidden:
                    if imported == bad or imported.startswith(bad + "."):
                        violations.append(f"{py.relative_to(SRC)} imports {imported}")
    assert not violations, "dependency rule violations:\n" + "\n".join(violations)


def test_composition_is_only_domain_wirer():
    """Outside composition/cli/tests, nobody imports concrete domain packages."""
    offenders = []
    for py in SRC.rglob("*.py"):
        rel = py.relative_to(SRC).as_posix()
        if rel.startswith(("domains/", "composition", "cli")):
            continue
        for imported in _imports_of(py):
            if imported.startswith("simcontract.domains"):
                offenders.append(rel)
    assert not offenders, offenders
