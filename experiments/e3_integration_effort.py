"""E3 supplement: git-defensible integration-effort measurement per domain.

Reports only what the repository history can defend (protocol discipline: no
active-hours are inferred from commit timestamps, and no prospective diary
exists for the two controlled domains). Measures per-domain code inventory by
category, the shared-layer footprint of the commit that introduced the
research domains, and cross-references the refactoring-invariance result.

Usage: PYTHONPATH=src python3 experiments/e3_integration_effort.py
Output: paper2_evidence/integration_effort/
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper2_evidence" / "integration_effort"
DOMAIN_COMMIT = "d362723"          # feat: two controlled research domains ...

SHARED_PREFIXES = ("src/simcontract/contracts/", "src/simcontract/engine/",
                   "src/simcontract/evidence/", "src/simcontract/analysis/",
                   "src/simcontract/controllers/", "src/simcontract/plugins/",
                   "src/simcontract/application.py", "src/simcontract/composition.py",
                   "src/simcontract/cli.py")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          cwd=ROOT).stdout


def loc(path: Path) -> int:
    try:
        return len(path.read_text().splitlines())
    except Exception:
        return 0


def domain_inventory(domain: str) -> dict:
    base = ROOT / "src" / "simcontract" / "domains" / domain
    cats = {"core_python": [], "contract_yaml": [], "scenarios": [],
            "role_policies": [], "package_init": []}
    for p in sorted(base.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(base).as_posix()
        if rel.startswith("contract/"):
            cats["contract_yaml"].append(p)
        elif rel.startswith("scenarios/"):
            cats["scenarios"].append(p)
        elif rel.startswith("roles/"):
            cats["role_policies"].append(p)
        elif rel == "__init__.py":
            cats["package_init"].append(p)
        elif p.suffix == ".py":
            cats["core_python"].append(p)
        elif p.suffix == ".yaml":
            cats["contract_yaml"].append(p)
    inv = {k: {"files": len(v), "loc": sum(loc(p) for p in v)} for k, v in cats.items()}
    inv["total"] = {"files": sum(v["files"] for v in inv.values()),
                    "loc": sum(v["loc"] for v in inv.values())}
    return inv


def introducing_commit_footprint() -> dict:
    """Path-categorised diffstat of the commit that added both research domains."""
    numstat = _git("show", "--numstat", "--format=", DOMAIN_COMMIT)
    buckets = {"domain_specific": [0, 0, 0], "shared_layers": [0, 0, 0],
               "tests": [0, 0, 0], "experiments_docs_other": [0, 0, 0]}
    for line in numstat.strip().splitlines():
        try:
            add, rm, path = line.split("\t")
            add, rm = int(add), int(rm)
        except ValueError:
            continue
        if path.startswith("src/simcontract/domains/"):
            b = "domain_specific"
        elif path.startswith(SHARED_PREFIXES):
            b = "shared_layers"
        elif path.startswith("tests/"):
            b = "tests"
        else:
            b = "experiments_docs_other"
        buckets[b][0] += 1
        buckets[b][1] += add
        buckets[b][2] += rm
    shared_files = [l.split("\t")[2] for l in numstat.strip().splitlines()
                    if len(l.split("\t")) == 3 and l.split("\t")[2].startswith(SHARED_PREFIXES)]
    return {"commit": DOMAIN_COMMIT,
            "subject": _git("log", "-1", "--format=%s", DOMAIN_COMMIT).strip(),
            "buckets": {k: {"files": v[0], "loc_added": v[1], "loc_removed": v[2]}
                        for k, v in buckets.items()},
            "shared_files_touched": shared_files}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "method": ("git-derived only; both research domains were introduced in a "
                   "single commit, so per-domain shared-layer impact cannot be "
                   "separated retrospectively, and no prospective effort diary "
                   "exists, so no active-hours are reported"),
        "head_commit": _git("rev-parse", "HEAD").strip(),
        "per_domain_inventory": {d: domain_inventory(d)
                                 for d in ("energy_market", "epidemic_policy",
                                           "reference_stub")},
        "introducing_commit": introducing_commit_footprint(),
        "cross_reference": ("Refactoring-invariance study: restructuring both "
                            "domain interiors changed 0 files in engine/evidence/"
                            "analysis/contracts with both fixed-seed hashes "
                            "identical (see paper2_evidence and the manuscript)."),
    }
    (OUT / "integration_effort.json").write_text(json.dumps(result, indent=2))
    with open(OUT / "integration_effort.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["domain", "category", "files", "loc"])
        for d, inv in result["per_domain_inventory"].items():
            for cat, v in inv.items():
                w.writerow([d, cat, v["files"], v["loc"]])
    print(json.dumps(result["per_domain_inventory"], indent=1)[:400])
    print("shared files touched by domain commit:",
          result["introducing_commit"]["shared_files_touched"])
    print("buckets:", json.dumps(result["introducing_commit"]["buckets"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
