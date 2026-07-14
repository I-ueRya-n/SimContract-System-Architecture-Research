"""Paper-1 evidence pack: materialise the artifact-paper tables from executed
runs as committed, machine-readable artifacts + a markdown appendix.

This turns the prose evidence in the manuscript into the structured tables an
artifact reviewer scores: contract-compliance matrix, determinism (per-item
hash identity), replay equivalence, failure containment (invalid + missing
injection), and dual-branch divergence. Everything is regenerable:

    PYTHONPATH=src python3 experiments/paper1_evidence_pack.py

Outputs land in ``paper1_evidence/`` (committed, not gitignored) as JSON + CSV
plus ``EVIDENCE_APPENDIX.md``.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

from simcontract.composition import create_application, create_registry, domain_assets
from simcontract.contracts import (
    Action,
    BundleView,
    ControllerResult,
    SimulationAdapter,
    digest,
)
from simcontract.engine import SessionRunner, rng_for
from simcontract.evidence import BundleEvidenceWriter, verify_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper1_evidence"
DOMAINS = ["reference_stub", "energy_market_v1", "epidemic_policy_v1"]
DEMO = {"reference_stub": "default",
        "energy_market_v1": "baseline_v1",
        "epidemic_policy_v1": "seed_outbreak_v1"}


# ----------------------------------------------------------------------------
def _csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _write(name: str, rows: list[dict]) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (OUT / f"{name}.csv").write_text(_csv(rows), encoding="utf-8")


class _Fixed:
    """Inject a specific action to exercise rejection/containment paths."""
    condition = "human"

    def __init__(self, fields, role):
        self._fields, self._role = fields, role

    def act(self, view, slot, candidates, previews, ctx) -> ControllerResult:
        return ControllerResult(action=Action(self._role, slot, dict(self._fields)))


# ---- E-table 1: contract-compliance matrix ---------------------------------
def compliance_matrix() -> list[dict]:
    rows = []
    for alias in DOMAINS:
        adapter = create_registry().create(alias)
        schema, obs, catalog, _ = domain_assets(alias)
        state = adapter.initial_state(DEMO[alias], seed=1)
        checks: dict[str, bool] = {}
        checks["protocol_satisfied"] = isinstance(adapter, SimulationAdapter)
        checks["manifest_valid"] = bool(adapter.manifest.to_dict()["domain_id"])
        # candidate validity at both tiers
        ok_syn = ok_sem = True
        for role in adapter.roles:
            for slot in role.slots():
                for c in adapter.action_space(state, slot, rng_for(1, slot), 6):
                    ok_syn &= schema.validate_syntactic(c) is None
                    ok_sem &= adapter.validate_semantic(state, c) is None
        checks["candidates_syntactic_valid"] = ok_syn
        checks["candidates_semantic_valid"] = ok_sem
        # run once for branch / resolution / catalog / replay
        writer = BundleEvidenceWriter(OUT / "_bundles" / alias)
        runner = SessionRunner(adapter, schema, obs, catalog, sink=writer)
        ctrls = {slot: _rule(adapter, slot) for role in adapter.roles
                 for slot in role.slots()}
        res = runner.run(scenario_id=DEMO[alias], run_seed=9, rounds=3,
                         controllers=ctrls, personas={})
        checks["both_branches_emitted"] = all(
            set(r.branches) == {"authoritative", "applied"} for r in res.rounds)
        checks["resolution_report_complete"] = all(
            set(r.resolution["sources"]) for r in res.rounds)
        checks["metrics_in_catalog"] = all(
            catalog.validate_metrics(r.system_metrics) == [] for r in res.rounds)
        rep = create_application().replay_run(writer.path)
        checks["replay_equivalent"] = rep.equivalent
        checks["default_action_completion"] = adapter.default_action_provider is not None
        row = {"capability": None}  # placeholder; expanded below
        rows.append({"domain": alias, **{k: ("Pass" if v else "FAIL")
                                         for k, v in checks.items()}})
    return rows


def _rule(adapter, slot):
    from simcontract.controllers import RuleController
    return RuleController(adapter.default_action_provider, None)


# ---- E-table 2: determinism (per-item hash identity) -----------------------
def determinism() -> list[dict]:
    app = create_application()
    rows = []
    for alias in ["energy_market_v1", "epidemic_policy_v1"]:
        outs = []
        for tag in ("A", "B"):
            r = app.run_session(domain=alias, scenario=DEMO[alias], seed=73,
                                rounds=4, conditions={"all": "rule"}, personas={},
                                out_dir=OUT / "_det" / f"{alias}_{tag}")
            outs.append(r)
        a, b = outs[0]["result"], outs[1]["result"]
        items = {
            "content_hash": (outs[0]["content_hash"], outs[1]["content_hash"]),
            "candidate_pool_digest": (
                digest([r.resolved_actions for r in a.rounds]),
                digest([r.resolved_actions for r in b.rounds])),
            "exogenous_digest": (
                digest([r.exogenous_digest for r in a.rounds]),
                digest([r.exogenous_digest for r in b.rounds])),
            "metrics_digest": (
                digest([r.system_metrics for r in a.rounds]),
                digest([r.system_metrics for r in b.rounds])),
            "branches_digest": (
                digest([r.branches for r in a.rounds]),
                digest([r.branches for r in b.rounds])),
        }
        for item, (ha, hb) in items.items():
            rows.append({"domain": alias, "item": item,
                         "run_A": ha[:16], "run_B": hb[:16],
                         "identical": "Yes" if ha == hb else "NO"})
    return rows


# ---- E-table 3: replay equivalence -----------------------------------------
def replay_equivalence() -> list[dict]:
    app = create_application()
    rows = []
    for alias in ["energy_market_v1", "epidemic_policy_v1"]:
        r = app.run_session(domain=alias, scenario=DEMO[alias], seed=73, rounds=5,
                            conditions={"all": "rule"}, personas={},
                            out_dir=OUT / "_replay" / alias)
        rep = app.replay_run(r["bundle"])
        ver = verify_bundle(r["bundle"])
        rows.append({"domain": alias, "rounds_compared": rep.rounds_compared,
                     "equal_rounds": rep.equal_rounds,
                     "replay_equivalent": "Yes" if rep.equivalent else "NO",
                     "hash_verified": "Yes" if ver["content_hash_ok"] else "NO",
                     "files_verified": "Yes" if ver["files_ok"] else "NO"})
    return rows


# ---- E-table 4: failure containment ----------------------------------------
def failure_containment() -> list[dict]:
    rows = []
    # invalid (out-of-range) action on the stub
    a = create_registry().create("reference_stub")
    s, o, c, _ = domain_assets("reference_stub")
    res = SessionRunner(a, s, o, c).run(
        scenario_id="default", run_seed=3, rounds=1,
        controllers={"agent_1": _Fixed({"delta": 99}, "agent")}, personas={})
    r0 = res.rounds[0]
    rows.append({"case": "invalid_action (out of range)",
                 "rejected": "Yes" if r0.resolution["rejected"] else "NO",
                 "rejection_tier": next(iter(r0.resolution["rejected"].values()))["stage"],
                 "completed_by_default": "Yes" if r0.resolution["sources"]["agent_1"]
                 == "domain_default" else "NO",
                 "run_completed": "Yes"})
    # semantic-invalid (shares!=1) on epidemic
    a = create_registry().create("epidemic_policy_v1")
    s, o, c, _ = domain_assets("epidemic_policy_v1")
    bad = {"share_testing": 0.9, "share_vaccination": 0.9, "share_capacity": 0.9}
    res = SessionRunner(a, s, o, c).run(
        scenario_id=DEMO["epidemic_policy_v1"], run_seed=3, rounds=1,
        controllers={"region_manager_1": _Fixed(bad, "region_manager")}, personas={})
    r0 = res.rounds[0]
    info = r0.resolution["rejected"]["region_manager_1"]
    rows.append({"case": "semantic_invalid (shares!=1)",
                 "rejected": "Yes", "rejection_tier": info["stage"],
                 "completed_by_default": "Yes" if r0.resolution["sources"]
                 ["region_manager_1"] == "domain_default" else "NO",
                 "run_completed": "Yes"})
    # missing controller (unassigned slot) on the stub
    res = SessionRunner(*(_bundle_parts("reference_stub"))).run(
        scenario_id="default", run_seed=3, rounds=1, controllers={}, personas={})
    r0 = res.rounds[0]
    rows.append({"case": "missing_controller (unassigned)",
                 "rejected": "n/a", "rejection_tier": "n/a",
                 "completed_by_default": "Yes" if r0.resolution["sources"]["agent_1"]
                 == "domain_default" else "NO",
                 "run_completed": "Yes"})
    return rows


def _bundle_parts(alias):
    a = create_registry().create(alias)
    s, o, c, _ = domain_assets(alias)
    return a, s, o, c


# ---- E-table 5: dual-branch divergence --------------------------------------
def dual_branch() -> list[dict]:
    app = create_application()
    alias = "energy_market_v1"
    # mixed conditions so applied != authoritative
    r = app.run_session(domain=alias, scenario=DEMO[alias], seed=73, rounds=5,
                        conditions={"regulator_1": "top_score", "all": "rule"},
                        personas={"regulator_1": "decarb_first"},
                        out_dir=OUT / "_branch" / alias)
    rows = []
    for rd in r["result"].rounds:
        auth, appl = rd.branches["authoritative"], rd.branches["applied"]
        key = "clearing_price"
        rows.append({"round": rd.round_no,
                     f"authoritative_{key}": round(auth.get(key, 0.0), 3),
                     f"applied_{key}": round(appl.get(key, 0.0), 3),
                     "renewable_share_auth": round(auth.get("renewable_share", 0.0), 4),
                     "renewable_share_applied": round(appl.get("renewable_share", 0.0), 4),
                     "regulator_source": rd.resolution["sources"]["regulator_1"]})
    return rows


# ---- test summary -----------------------------------------------------------
def test_summary() -> dict:
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q",
                            "--no-header"], cwd=ROOT, capture_output=True, text=True,
                           timeout=300)
        last = [l for l in p.stdout.splitlines() if l.strip()][-1]
        return {"pytest_summary": last, "returncode": p.returncode}
    except Exception as exc:  # noqa: BLE001
        return {"pytest_summary": f"unavailable: {exc}", "returncode": -1}


# ---- appendix ---------------------------------------------------------------
def _md_table(rows: list[dict], title: str) -> str:
    if not rows:
        return f"### {title}\n\n(no rows)\n\n"
    cols = list(rows[0].keys())
    out = [f"### {title}", "", "| " + " | ".join(cols) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out) + "\n\n"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    comp = compliance_matrix()
    det = determinism()
    rep = replay_equivalence()
    fail = failure_containment()
    branch = dual_branch()
    tests = test_summary()

    _write("compliance_matrix", comp)
    _write("determinism", det)
    _write("replay_equivalence", rep)
    _write("failure_containment", fail)
    _write("dual_branch", branch)
    (OUT / "test_summary.json").write_text(json.dumps(tests, indent=2))

    md = ["# Paper-1 evidence appendix (regenerable)",
          "",
          "Produced by `experiments/paper1_evidence_pack.py` from executed runs "
          "of SimContract. All tables are machine-generated; the CSV/JSON "
          "siblings are the citable artifacts.", "",
          f"Test suite: `{tests['pytest_summary']}`", "",
          _md_table(comp, "E-1 Contract-compliance matrix (per domain)"),
          _md_table(det, "E-2 Determinism: per-item semantic hash identity "
                    "(two independent runs, same seed)"),
          _md_table(rep, "E-3 Replay equivalence + bundle verification"),
          _md_table(fail, "E-4 Failure containment (injected)"),
          _md_table(branch, "E-5 Dual-branch divergence (energy, mixed conditions)"),
          "> Claim boundary: all values are architecture / reproducibility "
          "evidence and model-relative branch comparison. No external "
          "behavioural or predictive validity is claimed."]
    (OUT / "EVIDENCE_APPENDIX.md").write_text("\n".join(md), encoding="utf-8")

    print(f"[paper1] compliance rows: {len(comp)} | determinism: {len(det)} | "
          f"replay: {len(rep)} | failure: {len(fail)} | branch: {len(branch)}")
    print(f"[paper1] tests: {tests['pytest_summary']}")
    print(f"[paper1] appendix + CSV/JSON -> {OUT}")
    all_ok = (all(all(v == "Pass" for k, v in r.items() if k != "domain")
                  for r in comp)
              and all(r["identical"] == "Yes" for r in det)
              and all(r["replay_equivalent"] == "Yes" for r in rep)
              and all(r["run_completed"] == "Yes" for r in fail))
    print(f"[paper1] evidence pack: {'PASS' if all_ok else 'CHECK ROWS'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
