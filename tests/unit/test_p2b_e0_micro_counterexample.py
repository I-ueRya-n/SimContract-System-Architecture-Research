"""Regression tests for Paper 2B-E0 (docs/protocols/p2b_e0_micro_counterexample.md).

Locks the closed-form estimand values of the four canonical regimes and the
simulation-vs-closed-form identity. These are exact rational numbers, so the
assertions are tight (1e-9).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_E0_PATH = (Path(__file__).resolve().parents[2]
            / "experiments" / "paper2b" / "e0_micro_counterexample.py")
_spec = importlib.util.spec_from_file_location("e0_micro", _E0_PATH)
e0 = importlib.util.module_from_spec(_spec)
sys.modules["e0_micro"] = e0          # dataclass introspection needs this registered
_spec.loader.exec_module(e0)

TOL = 1e-9


def _est(rho, w_x, cand, H):
    sim = e0.simulate_estimands(rho, w_x, x0=1.0, cand=cand, H=H)
    cf = e0.closed_form(rho, w_x, cand, H)
    for k in ("SR", "CL", "MT", "AE"):
        assert abs(sim[k] - cf[k]) <= TOL, f"{k}: sim {sim[k]} != closed form {cf[k]}"
    return sim


def test_r1_equivalence_memoryless():
    sim = _est(0.0, 0.5, e0.CAND_AGGRESSIVE, 2)
    assert abs(sim["AE"]) <= TOL
    assert abs(sim["CL"] - sim["MT"]) <= TOL
    assert abs(sim["CL"] - 3.0) <= TOL


def test_r2_magnitude_error_same_sign():
    sim = _est(0.5, 0.5, e0.CAND_AGGRESSIVE, 2)
    assert abs(sim["CL"] - 2.25) <= TOL
    assert abs(sim["MT"] - 1.875) <= TOL
    assert sim["CL"] > 0 and sim["MT"] > 0          # same sign
    assert sim["MT"] < sim["CL"]                    # MT understates
    assert abs(sim["AE"] - 0.375) <= TOL


def test_r3_sign_reversal():
    sim = _est(0.9, 1.0, e0.CAND_AGGRESSIVE, 2)
    assert abs(sim["CL"] - 0.3) <= TOL
    assert abs(sim["MT"] - (-2.13)) <= TOL
    assert sim["CL"] > 0 and sim["MT"] < 0          # opposite signs
    assert abs(sim["AE"] - 2.43) <= TOL


def test_r4_ranking_reversal():
    a = _est(0.8, 0.5, e0.CAND_AGGRESSIVE, 2)
    e = _est(0.8, 0.5, e0.CAND_EFFICIENT, 2)
    # CL prefers aggressive; MT prefers efficient
    assert a["CL"] > e["CL"]
    assert e["MT"] > a["MT"]
    assert abs(a["CL"] - 1.8) <= TOL and abs(e["CL"] - 1.6) <= TOL
    assert abs(a["MT"] - 0.84) <= TOL and abs(e["MT"] - 1.28) <= TOL


def test_ae_closed_form_is_wx_rhoH_dload():
    # AE = w_x * rho^H * |l_i - l_d|, independent of benefit and of exogenous.
    for rho, w_x, H in [(0.3, 0.7, 1), (0.6, 1.2, 3), (0.95, 0.4, 5)]:
        sim = e0.simulate_estimands(rho, w_x, x0=1.0, cand=e0.CAND_AGGRESSIVE, H=H)
        expected = w_x * (rho ** H) * abs(e0.CAND_AGGRESSIVE.load - e0.DEFAULT.load)
        assert abs(sim["AE"] - expected) <= TOL


def test_sr_equals_cl_at_h1():
    # SR is the H=1 special case of CL by construction.
    for rho in (0.0, 0.5, 0.9):
        sim = e0.simulate_estimands(rho, 0.5, x0=1.0, cand=e0.CAND_AGGRESSIVE, H=1)
        assert abs(sim["SR"] - sim["CL"]) <= TOL


def test_exogenous_cancels_ae_invariant_to_shock():
    # Changing the shared exogenous schedule must not change any estimand
    # (they enter both branches identically and cancel). Patch _exog.
    original = e0._exog
    try:
        e0._exog = lambda H: [1.7, -2.3, 4.1, 0.6, -1.1, 3.3, -0.9][: 1 + H]
        shocked = e0.simulate_estimands(0.8, 0.5, x0=1.0, cand=e0.CAND_AGGRESSIVE, H=2)
        cf = e0.closed_form(0.8, 0.5, e0.CAND_AGGRESSIVE, 2)
        for k in ("SR", "CL", "MT", "AE"):
            assert abs(shocked[k] - cf[k]) <= TOL
    finally:
        e0._exog = original


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
