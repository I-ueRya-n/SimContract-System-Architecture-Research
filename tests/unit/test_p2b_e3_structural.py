"""Regression tests for Paper 2B-E3 structural boundary study
(docs/protocols/p2b_e3_structural_boundary.md).

Locks the structural anchors the boundary map depends on: no-delayed-cost
and memoryless configs are exactly MT==CL; the fractional-factorial design
is the documented 2^(7-2) size; and the estimand machinery is deterministic.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_E3 = (Path(__file__).resolve().parents[2]
       / "experiments" / "paper2b" / "e3_structural_boundary.py")
_spec = importlib.util.spec_from_file_location("e3_struct", _E3)
e3 = importlib.util.module_from_spec(_spec)
sys.modules["e3_struct"] = e3
_spec.loader.exec_module(e3)


def _struct(**kw):
    base = dict(rho=0.6, phi=0.3, irrev="reversible", w_x=1.0, sigma=0.5,
                timing=3, magnitude="large")
    base.update(kw)
    return e3.Structure(**base)


def test_no_delayed_cost_is_exact():
    # w_x = 0: outcome ignores the state, so MT == CL exactly for any structure.
    for cand in e3.CANDIDATES:
        for H in e3.HORIZONS:
            e = e3.estimands(seed=1, s=_struct(w_x=0.0), cand_name=cand, H=H)
            assert e["ae"] <= e3.EPS_ABS
            assert e3.classify(e["cl"], e["mt"], e["ae"]) == "exact"


def test_early_intervention_no_history_divergence():
    # timing=1: no pre-decision rounds, so S_t^F == S_t^D and MT == CL.
    e = e3.estimands(seed=3, s=_struct(timing=1), cand_name="aggressive", H=3)
    assert e["state_distance"] <= e3.EPS_ABS
    assert e["ae"] <= e3.EPS_ABS


def test_persistence_plus_delay_can_diverge():
    # high persistence + delayed cost + late timing -> nonzero attribution error.
    e = e3.estimands(seed=1, s=_struct(rho=0.9, w_x=1.0, timing=5),
                     cand_name="aggressive", H=5)
    assert e["ae"] > e3.EPS_ABS


def test_estimands_are_deterministic():
    a = e3.estimands(seed=7, s=_struct(), cand_name="efficient", H=3)
    b = e3.estimands(seed=7, s=_struct(), cand_name="efficient", H=3)
    assert a == b


def test_fractional_factorial_is_2pow7minus2():
    cells = e3.fractional_factorial()
    assert len(cells) == 32                       # 2^(7-2) resolution IV
    # every factor is balanced (16 lo / 16 hi) -- a valid orthogonal fraction
    for f in e3.FACTORS:
        his = sum(1 for c in cells if c[f] == "hi")
        assert his == 16, f"{f} unbalanced: {his} hi"


def test_classifier_regimes():
    assert e3.classify(1.0, 1.0, 0.0) == "exact"
    assert e3.classify(1.0, -1.0, 2.0) == "divergent"      # sign flip
    assert e3.classify(1.0, 1.02, 0.02) == "approximate"   # within 10%
    assert e3.classify(1.0, 1.5, 0.5) == "divergent"       # 50% > 10% tol


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
