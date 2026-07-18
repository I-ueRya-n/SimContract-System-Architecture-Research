"""Regression tests for Paper 2B-E4 conclusion-impact study
(docs/protocols/p2b_e4_conclusion_impact.md).

Locks the decision-ranking machinery: Kendall tau, deterministic candidate
generation, live history divergence, and the energy structural-stability
anchor.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_E4 = (Path(__file__).resolve().parents[2]
       / "experiments" / "paper2b" / "e4_conclusion_impact.py")
_spec = importlib.util.spec_from_file_location("e4_impact", _E4)
e4 = importlib.util.module_from_spec(_spec)
sys.modules["e4_impact"] = e4
_spec.loader.exec_module(e4)

from simcontract.composition import create_application
from simcontract.contracts import digest


def test_kendall_tau_bounds():
    assert e4.kendall_tau(["a", "b", "c"], ["a", "b", "c"]) == 1.0       # identical
    assert e4.kendall_tau(["a", "b", "c"], ["c", "b", "a"]) == -1.0      # reversed
    tau = e4.kendall_tau(["a", "b", "c", "d"], ["a", "c", "b", "d"])     # one swap
    assert -1.0 < tau < 1.0


def test_candidate_generation_deterministic():
    app = create_application()
    ad = app._registry.create("epidemic_policy_v1")
    s = e4._history_state(ad, "second_wave_v1", 1, 5,
                          lambda st, cx: e4._default_map(ad, st, cx))
    m1 = e4._candidate_maps(ad, s, 1, 5, "epidemic_policy_v1")
    m2 = e4._candidate_maps(ad, s, 1, 5, "epidemic_policy_v1")
    slot = e4.DECISION_SLOT["epidemic_policy_v1"]
    assert [c[1][slot].fields for c in m1] == [c[1][slot].fields for c in m2]
    assert len(m1) == e4.K_CANDIDATES


def test_history_states_diverge():
    # candidate standing-policy histories must produce distinct pre-decision states.
    app = create_application()
    ad = app._registry.create("epidemic_policy_v1")
    s = e4._history_state(ad, "second_wave_v1", 1, 5,
                          lambda st, cx: e4._default_map(ad, st, cx))
    cmaps = e4._candidate_maps(ad, s, 1, 5, "epidemic_policy_v1")
    hs = [e4._history_state(ad, "second_wave_v1", 1, 5, m) for _, m in cmaps]
    assert len({digest(x) for x in hs}) == len(hs)          # all distinct


def test_energy_rankings_are_structurally_stable():
    # energy's outcome is state-independent, so CL and MT rankings coincide
    # (Kendall tau == 1) for every objective -- the exact anchor.
    app = create_application()
    ad = app._registry.create("energy_market_v1")
    _, _, catalog, _ = app._assets_for("energy_market_v1")
    s = e4._history_state(ad, "baseline_v1", 1, 5,
                          lambda st, cx: e4._default_map(ad, st, cx))
    cmaps = e4._candidate_maps(ad, s, 1, 5, "energy_market_v1")
    hist = {cid: e4._history_state(ad, "baseline_v1", 1, 5, m) for cid, m in cmaps}
    U = e4.e2.build_schedule(ad, s, 1, 5, 5)
    for m in catalog.keys:
        cl = {cid: e4._oriented(e4.e2.roll_out(ad, s, amap, 1, 5, U)[m],
                                catalog.direction(m)) for cid, amap in cmaps}
        mt = {cid: e4._oriented(e4.e2.roll_out(ad, hist[cid], amap, 1, 5, U)[m],
                                catalog.direction(m)) for cid, amap in cmaps}
        order_cl = sorted(cl, key=lambda c: cl[c], reverse=True)
        order_mt = sorted(mt, key=lambda c: mt[c], reverse=True)
        assert e4.kendall_tau(order_cl, order_mt) == 1.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
