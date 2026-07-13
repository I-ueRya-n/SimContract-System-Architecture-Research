"""Token-leakage gate (consolidated spec 8.4): core layers carry no domain
vocabulary. A new domain must never require touching core code."""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "simcontract"

CORE_LAYERS = ["contracts", "engine", "controllers", "plugins", "evidence",
               "analysis", "llm"]
CORE_MODULES = ["application.py"]

DOMAIN_TOKENS = [
    "energy", "generator", "carbon", "renewable", "retailer", "clearing",
    "merit_order", "wind", "epidemic", "seir", "infection", "vaccin",
    "restriction", "mask_level", "hospital", "region_manager",
    "health_authority", "regulator",
]

_PATTERN = re.compile("|".join(DOMAIN_TOKENS), re.IGNORECASE)


def _leaks_in(path: Path) -> list[str]:
    hits = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = _PATTERN.search(line)
        if m:
            hits.append(f"{path.relative_to(SRC)}:{i}: {m.group(0)}")
    return hits


def test_core_layers_have_no_domain_tokens():
    leaks: list[str] = []
    for layer in CORE_LAYERS:
        for py in (SRC / layer).rglob("*.py"):
            leaks.extend(_leaks_in(py))
    for module in CORE_MODULES:
        leaks.extend(_leaks_in(SRC / module))
    assert not leaks, "domain vocabulary leaked into core layers:\n" + "\n".join(leaks)
