"""Regression tests for Paper 2B-E6 external replication
(docs/protocols/p2b_e6_external_replication.md).

Locks the load-bearing external-replication properties that do not require a
long SUMO run: deterministic same-history reconstruction, the E4-consistent
CL/MT construction shape, the checker-independence of the manifest exporter,
and the frozen E5 checker's verdicts on the external SUMO manifests.
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

_E6 = (Path(__file__).resolve().parents[2]
       / "experiments" / "paper2b" / "e6_external_replication.py")
_spec = importlib.util.spec_from_file_location("e6_ext", _E6)
e6 = importlib.util.module_from_spec(_spec)
sys.modules["e6_ext"] = e6
_spec.loader.exec_module(e6)


def test_replay_reconstruction_is_deterministic():
    # two independent replays of the same history reach a byte-identical
    # observable pre-state (the CL shared-clone guarantee).
    _, s1 = e6.replay_branch("moderate", 1, 5, e6.DEFAULT_PHASE, e6.DEFAULT_PHASE, 5)
    _, s2 = e6.replay_branch("moderate", 1, 5, e6.DEFAULT_PHASE, e6.DEFAULT_PHASE, 5)
    assert s1 == s2


def test_intervention_changes_outcome_under_congestion():
    # a different signal programme at the decision changes cumulative waiting
    # (a real CL action channel).
    m_def, _ = e6.replay_branch("dense", 1, 7, e6.DEFAULT_PHASE, e6.DEFAULT_PHASE, 5)
    m_int, _ = e6.replay_branch("dense", 1, 7, e6.DEFAULT_PHASE, 2, 5)
    assert m_def[5] != m_int[5]


def test_manifest_exporter_does_not_import_checker():
    # portability / independence: the exporter must not consult the checker.
    src = inspect.getsource(e6.export_manifest)
    assert "e5.check" not in src and "check(" not in src


def test_frozen_checker_passes_intact_sumo_manifests():
    for dtype in e6.e5.ESTIMAND_TYPES:
        m, expected = e6.export_manifest("moderate", 1, 5, 5, dtype, "intact")
        assert expected == "PASS"
        assert e6.e5.check(m)["verdict"] == "PASS", dtype


def test_frozen_checker_flags_history_declared_local():
    # a historical (different-state) comparison mislabelled as cloned-local -> FAIL.
    m, expected = e6.export_manifest("moderate", 1, 5, 5, "matched_history_contrast",
                                     "history_declared_local")
    assert expected == "FAIL"
    r = e6.e5.check(m)
    assert r["verdict"] == "FAIL"
    assert r["supported_estimand"] == "matched_history_contrast"


def test_savestate_case_is_local_only_defect():
    # saveState non-clone: FAIL for local, PASS for MT/RS (they allow different states).
    m_cl, exp_cl = e6.export_manifest("moderate", 1, 5, 5, "cloned_local_h_step",
                                      "saveState_not_continuous")
    m_mt, exp_mt = e6.export_manifest("moderate", 1, 5, 5, "matched_history_contrast",
                                      "saveState_not_continuous")
    assert exp_cl == "FAIL" and e6.e5.check(m_cl)["verdict"] == "FAIL"
    assert exp_mt == "PASS" and e6.e5.check(m_mt)["verdict"] == "PASS"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
