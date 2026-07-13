"""Contract and evidence-schema versioning (docs/versioning-and-compatibility.md)."""
from __future__ import annotations

CONTRACT_VERSION = "1.0.0"
EVIDENCE_SCHEMA_VERSION = "1.0.0"


def major(version: str) -> int:
    return int(version.split(".", 1)[0])


def is_compatible(declared: str, current: str = CONTRACT_VERSION) -> bool:
    """A domain is compatible when it declares the same contract major version."""
    try:
        return major(declared) == major(current)
    except (ValueError, AttributeError):
        return False
