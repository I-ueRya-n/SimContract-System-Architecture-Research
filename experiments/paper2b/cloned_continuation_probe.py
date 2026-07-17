"""Paper 2B feasibility probe: cloned-continuation methodology check.

This is NOT a Paper 2B experiment. It is a small, bounded probe, run once on
one domain, answering three narrow questions before any Paper 2B experiment
design is committed to (activation gate `paper2b_gate_a`,
`cloned_h_step_feasible`):

  1. Can a mid-run pre-decision state be captured, hashed, and deep-copied
     into two identical clones?
  2. If each clone is advanced one round independently through the public
     `adapter.step()` call -- clone A with the real submitted action, clone
     B with the domain's default action -- does the result agree exactly
     with the SAME adapter's own internal authoritative/applied branch
     computation from the original run? (A1/A2's results already depend on
     that internal branch machinery; this checks that externally
     orchestrated cloned continuation is methodologically equivalent to it,
     which the full Paper 2B design requires.)
  3. If both clones then continue for two more rounds under a shared
     continuation policy (domain defaults) and a shared per-round exogenous
     draw, does the exogenous schedule stay identical across the two
     branches despite their states having diverged since the split (H=3
     total)?

Domain: epidemic_policy_v1 only -- the path-dependent domain already used
for A2's confirmatory result (energy_market_v1 has no mechanistically
carried state, so a cloned-continuation check there would be uninformative
by the same structural finding already reported for A2).

No production code is modified. `adapter.step()`, `adapter.sample_exogenous`,
and `adapter.default_action_provider` are all called through their existing
public interfaces, exactly as `engine.session.SessionRunner.run` calls them.

Usage: python experiments/paper2b/cloned_continuation_probe.py
"""
from __future__ import annotations

import copy
import json
import subprocess
import tempfile
from pathlib import Path

from simcontract.composition import create_application
from simcontract.contracts import Action, BundleView, StepContext, digest
from simcontract.contracts.seeding import derive_seed, rng_for

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper2_evidence" / "p2b_feasibility_cloned_continuation"

DOMAIN = "epidemic_policy_v1"
SCENARIO = "second_wave_v1"
SEED = 1
CONDITION = "random_valid"
ROUNDS = 6
CHECKPOINT_ROUND = 3          # mid-run; same round A2's manual spot check uses
CONTINUATION_ROUNDS = [4, 5]  # H=3 total: split round 3 + two continuation rounds


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


def _actions_from_resolved(resolved: dict) -> dict[str, Action]:
    return {slot: Action(role=d["role"], slot=slot, fields=d["fields"])
            for slot, d in resolved.items()}


def _default_actions(adapter, state, ctx) -> dict[str, Action]:
    out = {}
    for role in adapter.roles:
        for slot in role.slots():
            out[slot] = adapter.default_action_provider.action_for(state, slot, None, ctx)
    return out


def main() -> int:
    app = create_application()
    adapter = app._registry.create(DOMAIN)
    commit = _git_commit()
    gates: list[dict] = []

    # ---- capture a real submitted-condition run; pre-decision state per
    # round via the existing on_round hook (same technique as A2's run_one)
    states_entering: dict[int, dict] = {1: adapter.initial_state(SCENARIO, SEED)}

    def on_round(round_no, outcome):
        states_entering[round_no + 1] = outcome.state_next

    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td) / "run"
        app.run_session(domain=DOMAIN, scenario=SCENARIO, seed=SEED, rounds=ROUNDS,
                        conditions={"all": CONDITION}, personas={}, out_dir=out_dir,
                        on_round=on_round)
        bundle = BundleView.load(out_dir)

    rounds_by_no = {r.round_no: r for r in bundle.rounds}
    checkpoint_state = states_entering[CHECKPOINT_ROUND]
    original = rounds_by_no[CHECKPOINT_ROUND]

    # ---- checkpoint capture + hash; clone into two branches ----
    ck_digest = digest(checkpoint_state)
    state_a = copy.deepcopy(checkpoint_state)
    state_b = copy.deepcopy(checkpoint_state)
    gates.append({"gate": "checkpoint_clone_identity",
                 "pass": digest(state_a) == ck_digest and digest(state_b) == ck_digest,
                 "detail": f"checkpoint digest {ck_digest[:12]}..."})

    # ---- shared future exogenous schedule at the split round ----
    round_seed = derive_seed(SEED, CHECKPOINT_ROUND)
    exo_a = adapter.sample_exogenous(state_a, rng_for(round_seed, "exogenous"))
    exo_b = adapter.sample_exogenous(state_b, rng_for(round_seed, "exogenous"))
    gates.append({"gate": "split_round_exogenous_shared",
                 "pass": digest(exo_a) == digest(exo_b) == original.exogenous_digest,
                 "detail": "clone A, clone B, and the original run all draw the "
                           "identical exogenous vector at the split round"})

    # ---- H=1: submitted action in branch A, default action in branch B ----
    ctx_a = StepContext(round_no=CHECKPOINT_ROUND, round_seed=round_seed,
                        exogenous=exo_a, scenario_id=SCENARIO)
    ctx_b = StepContext(round_no=CHECKPOINT_ROUND, round_seed=round_seed,
                        exogenous=exo_b, scenario_id=SCENARIO)
    actions_submitted = _actions_from_resolved(original.resolved_actions)
    actions_default = _default_actions(adapter, state_b, ctx_b)

    outcome_a = adapter.step(state_a, actions_submitted, ctx_a)
    outcome_b = adapter.step(state_b, actions_default, ctx_b)

    gates.append({"gate": "clone_a_reproduces_applied",
                 "pass": outcome_a.system_metrics == original.branches["applied"],
                 "detail": "clone A (submitted action) vs. original run's applied branch"})
    gates.append({"gate": "clone_b_reproduces_authoritative",
                 "pass": outcome_b.system_metrics == original.branches["authoritative"],
                 "detail": "clone B (default action) vs. original run's authoritative branch"})

    d_local_original = {m: original.branches["applied"][m] - original.branches["authoritative"][m]
                        for m in original.system_metrics}
    d_local_cloned = {m: outcome_a.system_metrics[m] - outcome_b.system_metrics[m]
                      for m in original.system_metrics}
    gates.append({"gate": "cloned_divergence_matches_a2_d_local",
                 "pass": d_local_cloned == d_local_original,
                 "detail": f"round {CHECKPOINT_ROUND}: {d_local_cloned}"})

    h1_pass = all(g["pass"] for g in gates)

    # ---- H=3: continue both clones for two more rounds under a shared
    # continuation policy (domain defaults) and a shared per-round
    # exogenous draw; verify the exogenous schedule stays identical despite
    # the branches' states having diverged since the split. This is new
    # information beyond A2 (which never continues a trajectory past one
    # round of divergence) -- exploratory only, not a confirmatory claim.
    trajectory = []
    state_a, state_b = outcome_a.state_next, outcome_b.state_next
    h3_exo_shared = True
    for round_no in CONTINUATION_ROUNDS:
        r_seed = derive_seed(SEED, round_no)
        exo_a = adapter.sample_exogenous(state_a, rng_for(r_seed, "exogenous"))
        exo_b = adapter.sample_exogenous(state_b, rng_for(r_seed, "exogenous"))
        match = digest(exo_a) == digest(exo_b)
        h3_exo_shared = h3_exo_shared and match

        ctx_a = StepContext(round_no=round_no, round_seed=r_seed, exogenous=exo_a,
                            scenario_id=SCENARIO)
        ctx_b = StepContext(round_no=round_no, round_seed=r_seed, exogenous=exo_b,
                            scenario_id=SCENARIO)
        actions_a = _default_actions(adapter, state_a, ctx_a)
        actions_b = _default_actions(adapter, state_b, ctx_b)
        outcome_a = adapter.step(state_a, actions_a, ctx_a)
        outcome_b = adapter.step(state_b, actions_b, ctx_b)

        diffs = {m: outcome_a.system_metrics[m] - outcome_b.system_metrics[m]
                for m in outcome_a.system_metrics}
        trajectory.append({"round": round_no, "exogenous_match": match,
                           "metric_diff": diffs})
        state_a, state_b = outcome_a.state_next, outcome_b.state_next

    gates.append({"gate": "h3_exogenous_shared_despite_divergence",
                 "pass": h3_exo_shared,
                 "detail": "rounds " + ",".join(str(r) for r in CONTINUATION_ROUNDS)})

    all_pass = all(g["pass"] for g in gates)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gates.json").write_text(json.dumps({
        "domain": DOMAIN, "scenario": SCENARIO, "seed": SEED, "condition": CONDITION,
        "checkpoint_round": CHECKPOINT_ROUND, "continuation_rounds": CONTINUATION_ROUNDS,
        "gates": gates, "h1_pass": h1_pass, "all_gates_pass": all_pass,
    }, indent=2, default=str))
    (OUT / "h3_trajectory.json").write_text(json.dumps({
        "split_round": CHECKPOINT_ROUND,
        "split_metric_diff": d_local_cloned,
        "continuation": trajectory,
    }, indent=2, default=str))
    (OUT / "environment.json").write_text(json.dumps({
        "software_commit": commit,
        "config": {"domain": DOMAIN, "scenario": SCENARIO, "seed": SEED,
                   "condition": CONDITION, "rounds": ROUNDS,
                   "checkpoint_round": CHECKPOINT_ROUND,
                   "continuation_rounds": CONTINUATION_ROUNDS},
    }, indent=2))

    print(f"[paper2b feasibility probe] {'ALL GATES PASS' if all_pass else 'GATE FAILURE'}")
    for g in gates:
        print(f"  {g['gate']}: {'PASS' if g['pass'] else 'FAIL'} -- {g['detail']}")
    print(f"H=3 continuation trajectory (exploratory): {trajectory}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
