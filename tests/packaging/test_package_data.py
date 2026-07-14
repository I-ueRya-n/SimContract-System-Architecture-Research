"""Packaging guard (consolidated spec 5.4): every domain YAML that adapters
load at runtime MUST be covered by a package-data glob in pyproject.toml, or a
non-editable ``pip install .`` ships a wheel whose adapters crash at load.

This catches the common regression: a new domain adds a schema/scenario YAML
but nobody updates ``[tool.setuptools.package-data]``. It does not build a
wheel (too slow for the unit suite); ``scripts/verify_wheel.sh`` does that.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    tomllib = None

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "simcontract"


def _package_data_globs() -> list[str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if tomllib is not None:
        data = tomllib.loads(text)
        return list(data["tool"]["setuptools"]["package-data"]["simcontract"])
    # minimal fallback parser for the one array we need
    globs, capture = [], False
    for line in text.splitlines():
        if line.strip().startswith("simcontract = ["):
            capture = True
            continue
        if capture:
            if "]" in line:
                break
            item = line.strip().strip(",").strip().strip('"')
            if item:
                globs.append(item)
    return globs


def test_every_domain_yaml_is_shipped():
    globs = _package_data_globs()
    assert globs, "no package-data globs declared for simcontract"

    yamls = sorted(PKG.glob("domains/**/*.yaml"))
    assert yamls, "no domain YAML found — test wiring is wrong"

    uncovered = []
    for y in yamls:
        rel = y.relative_to(PKG).as_posix()
        if not any(fnmatch.fnmatch(rel, g) for g in globs):
            uncovered.append(rel)
    assert not uncovered, (
        "domain YAML not covered by package-data globs (would be missing from "
        f"a built wheel): {uncovered}; globs={globs}")
