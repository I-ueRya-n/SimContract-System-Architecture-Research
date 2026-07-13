"""E1 core: dependency rules of docs/dependency-rules.md, enforced by AST audit."""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "simcontract"

_ALL = ["simcontract.contracts", "simcontract.engine", "simcontract.controllers",
        "simcontract.plugins", "simcontract.domains", "simcontract.evidence",
        "simcontract.analysis", "simcontract.llm", "simcontract.application",
        "simcontract.composition", "simcontract.cli"]


def _others(*allowed: str) -> list[str]:
    keep = set(allowed)
    return [layer for layer in _ALL if layer not in keep]


FORBIDDEN = {
    "contracts": _others("simcontract.contracts"),
    "engine": _others("simcontract.contracts", "simcontract.engine"),
    "controllers": _others("simcontract.contracts", "simcontract.controllers",
                           "simcontract.llm"),
    "plugins": _others("simcontract.contracts", "simcontract.plugins"),
    "domains": _others("simcontract.contracts", "simcontract.domains"),
    "evidence": _others("simcontract.contracts", "simcontract.evidence"),
    "analysis": _others("simcontract.contracts", "simcontract.analysis"),
    "llm": _others("simcontract.contracts", "simcontract.llm"),
}

# application: platform layers yes, domains/composition no
APPLICATION_FORBIDDEN = ["simcontract.domains", "simcontract.composition"]


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


def test_domains_do_not_import_each_other():
    domain_dirs = [d.name for d in (SRC / "domains").iterdir() if d.is_dir()
                   and not d.name.startswith("__")]
    violations = []
    for name in domain_dirs:
        for py in (SRC / "domains" / name).rglob("*.py"):
            for imported in _imports_of(py):
                for other in domain_dirs:
                    if other != name and imported.startswith(f"simcontract.domains.{other}"):
                        violations.append(f"{py.relative_to(SRC)} imports {imported}")
    assert not violations, violations


def test_application_facade_rules():
    for imported in _imports_of(SRC / "application.py"):
        for bad in APPLICATION_FORBIDDEN:
            assert not (imported == bad or imported.startswith(bad + ".")), (
                f"application.py imports {imported}")


def test_composition_is_only_domain_wirer():
    """Outside composition and domains themselves, nobody imports concrete domains."""
    offenders = []
    for py in SRC.rglob("*.py"):
        rel = py.relative_to(SRC).as_posix()
        if rel.startswith("domains/") or rel == "composition.py":
            continue
        for imported in _imports_of(py):
            if imported.startswith("simcontract.domains"):
                offenders.append(rel)
    assert not offenders, offenders


def test_nothing_imports_composition():
    """Only entry points (cli) may import the composition root."""
    offenders = []
    for py in SRC.rglob("*.py"):
        rel = py.relative_to(SRC).as_posix()
        if rel == "cli.py" or rel == "composition.py":
            continue
        for imported in _imports_of(py):
            if imported.startswith("simcontract.composition"):
                offenders.append(rel)
    assert not offenders, offenders
