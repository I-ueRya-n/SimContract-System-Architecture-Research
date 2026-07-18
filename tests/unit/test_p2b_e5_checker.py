"""Regression tests for the Paper 2B-E5 integrity checker
(docs/protocols/p2b_e5_integrity_checker.md).

Locks the frozen checker's verdict logic on canonical cases: intact -> PASS,
missing-recommended -> WARN, identity violations -> FAIL with the correct
supported estimand, and unknown inputs -> UNSUPPORTED.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_E5 = (Path(__file__).resolve().parents[2]
       / "experiments" / "paper2b" / "e5_integrity_checker.py")
_spec = importlib.util.spec_from_file_location("e5_checker", _E5)
e5 = importlib.util.module_from_spec(_spec)
sys.modules["e5_checker"] = e5
_spec.loader.exec_module(e5)

_IDS = {
    "domain": "epidemic_policy_v1", "decision_point": 3, "horizon": 5,
    "shared_checkpoint": "aa", "factual_state": "bb", "default_state": "cc",
    "schedule_hash": "sched", "model_hash": "model", "metric_hash": "metric",
    "policy_hash": "policy", "branch_a": "A", "branch_b": "B",
    "hist_branch_f": "Fh", "hist_branch_d": "Dh", "ancestry_f": "ancF",
    "ancestry_d": "ancD", "proposed": "prop", "applied": "appl",
}


def _cl():
    return e5._intact_manifest("cloned_local_h_step", _IDS)


def test_intact_passes():
    for et in e5.ESTIMAND_TYPES:
        r = e5.check(e5._intact_manifest(et, _IDS))
        assert r["verdict"] == "PASS", (et, r["reason"])


def test_unknown_schema_and_type_unsupported():
    m = _cl(); m["manifest_schema_version"] = "x/9.9"
    assert e5.check(m)["verdict"] == "UNSUPPORTED"
    m = _cl(); m["declared_estimand"]["type"] = "mystery"
    assert e5.check(m)["verdict"] == "UNSUPPORTED"


def test_missing_recommended_provenance_warns():
    m = _cl(); m["provenance"]["source_tag"] = None
    r = e5.check(m)
    assert r["verdict"] == "WARN"


def test_local_without_shared_clone_fails_and_reports_matched():
    # a cloned-local claim whose branches are not a shared clone actually
    # supports a matched-history contrast.
    m = _cl(); m["state_identity"]["alternative_predecision_state_hash"] = "different"
    r = e5.check(m)
    assert r["verdict"] == "FAIL"
    assert r["supported_estimand"] == "matched_history_contrast"
    assert "matched-schedule historical contrast" in r["safe_wording"]


def test_continuation_policy_mismatch_fails():
    m = _cl(); m["branch_identity"]["alternative_continuation_policy_hash"] = "other"
    assert e5.check(m)["verdict"] == "FAIL"


def test_matched_declared_but_resampled_fails():
    m = e5._intact_manifest("matched_history_contrast", _IDS)
    m["exogenous_identity"]["resampled"] = True
    r = e5.check(m)
    assert r["verdict"] == "FAIL"
    assert r["supported_estimand"] == "resampled_contrast"


def test_checker_is_portable_no_simcontract_import():
    # the check() function must not require SimContract -- portability.
    import inspect
    src = inspect.getsource(e5.check)
    assert "simcontract" not in src.lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
