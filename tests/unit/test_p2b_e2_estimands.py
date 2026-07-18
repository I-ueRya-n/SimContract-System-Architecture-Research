"""Regression tests for Paper 2B-E2 estimand machinery
(docs/protocols/p2b_e2_cloned_continuation.md).

Locks the load-bearing correctness properties of the confirmatory harness:
roll_out purity, schedule-injection determinism, and the H=1 identity
between the cloned CL estimand and the adapter's own internal
applied-minus-authoritative branch (the generalisation of the feasibility
probe's -880.77 cross-check).
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_E2_PATH = (Path(__file__).resolve().parents[2]
            / "experiments" / "paper2b" / "e2_cloned_continuation.py")
_spec = importlib.util.spec_from_file_location("e2_cloned", _E2_PATH)
e2 = importlib.util.module_from_spec(_spec)
sys.modules["e2_cloned"] = e2
_spec.loader.exec_module(e2)

from simcontract.composition import create_application
from simcontract.contracts import Action, StepContext, digest
from simcontract.contracts.seeding import derive_seed


def _setup(domain="epidemic_policy_v1", scenario="second_wave_v1", seed=1, t=3):
    app = create_application()
    adapter = app._registry.create(domain)
    fac_bundle, fac_states = e2._run_capture(app, domain, scenario, "random_valid",
                                             seed, e2.SESSION_ROUNDS)
    _, def_states = e2._run_capture(app, domain, scenario, "rule", seed, e2.SESSION_ROUNDS)
    rounds_by_no = {r.round_no: r for r in fac_bundle.rounds}
    return adapter, fac_states[t], def_states[t], rounds_by_no[t]


def test_roll_out_does_not_mutate_inputs():
    adapter, s_fac, _s_def, _orig = _setup()
    before = digest(s_fac)
    submitted = e2._actions_from_resolved(_orig.resolved_actions)
    U = e2.build_schedule(adapter, s_fac, 1, 3, 3)
    U_before = [digest(u) for u in U]
    e2.roll_out(adapter, s_fac, submitted, 1, 3, U)
    assert digest(s_fac) == before            # start state untouched
    assert [digest(u) for u in U] == U_before  # schedule untouched


def test_schedule_injection_is_deterministic():
    adapter, s_fac, _s_def, _orig = _setup()
    U1 = e2.build_schedule(adapter, s_fac, 1, 3, 5)
    U2 = e2.build_schedule(adapter, s_fac, 1, 3, 5)
    assert [digest(u) for u in U1] == [digest(u) for u in U2]


def test_h1_cl_equals_internal_branch():
    # The generalised probe cross-check: at H=1, the cloned CL estimand must
    # equal the adapter's own applied-minus-authoritative branch at round t.
    adapter, s_fac, _s_def, orig = _setup()
    submitted = e2._actions_from_resolved(orig.resolved_actions)
    ctx0 = StepContext(round_no=3, round_seed=derive_seed(1, 3), exogenous={},
                       scenario_id="second_wave_v1")
    default_t = e2._default_actions(adapter, s_fac, ctx0)
    U = e2.build_schedule(adapter, s_fac, 1, 3, 1)
    cl_a = e2.roll_out(adapter, s_fac, submitted, 1, 3, U)
    cl_b = e2.roll_out(adapter, s_fac, default_t, 1, 3, U)
    d_cl = {m: cl_a[m] - cl_b[m] for m in cl_a}
    internal = {m: orig.branches["applied"][m] - orig.branches["authoritative"][m]
                for m in orig.system_metrics}
    assert d_cl == internal


def test_energy_cl_equals_mt_structural_zero():
    # energy_market's outcome is state-independent: the matched-schedule
    # default branch must coincide with the cloned default branch, so AE=0.
    adapter, s_fac, s_def, orig = _setup(domain="energy_market_v1",
                                         scenario="baseline_v1", t=3)
    submitted = e2._actions_from_resolved(orig.resolved_actions)
    ctx0 = StepContext(round_no=3, round_seed=derive_seed(1, 3), exogenous={},
                       scenario_id="baseline_v1")
    default_t = e2._default_actions(adapter, s_fac, ctx0)
    U = e2.build_schedule(adapter, s_fac, 1, 3, 5)
    cl_b = e2.roll_out(adapter, s_fac, default_t, 1, 3, U)
    mt_d = e2.roll_out(adapter, s_def, default_t, 1, 3, U)
    assert cl_b == mt_d          # structural coincidence -> AE == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
