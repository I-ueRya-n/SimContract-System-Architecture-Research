# Paper 2B feasibility probe: cloned-continuation methodology check

**Status: feasibility probe only. Not a Paper 2B experiment.**

Script: `experiments/paper2b/cloned_continuation_probe.py`. Run once,
`epidemic_policy_v1`, `second_wave_v1`, seed 1, `random_valid`, 6 rounds,
split at round 3.

## What this checks

The full Paper 2B design (continuing a cloned trajectory for H rounds after
a submitted decision, under a shared exogenous schedule and a shared
continuation policy) needs three things to hold. This probe checks each one
empirically, once, before any larger Paper 2B experiment is designed:

1. **Checkpoint clone identity.** A mid-run pre-decision state can be
   hashed, deep-copied twice, and both copies still hash-match the
   original.
2. **Cloned step() agrees with the adapter's own internal branch
   computation.** Clone A is advanced one round with the real submitted
   action; clone B with the domain's default action — both via the public
   `adapter.step()` call, independently. Clone A's result matches the
   original run's own `applied` branch exactly; clone B's result matches
   the original run's own `authoritative` branch exactly. This is the load
   -bearing check: A1 and A2 both depend on the adapter's *internal*
   authoritative/applied computation being trustworthy, and this confirms
   that *externally orchestrated* cloned continuation reproduces that same
   computation rather than approximating it.
3. **Shared exogenous schedule survives divergence.** After the round-3
   split, both clones continue for two more rounds (H=3 total) under a
   shared continuation policy (domain defaults) with independently
   recomputed exogenous draws at each round. Both branches draw identical
   exogenous vectors at rounds 4 and 5 despite their states having
   diverged since the split.

## Result

All 6 gates pass (`gates.json`). Notably, the round-3 metric divergence
computed here from two independently cloned `adapter.step()` calls
(`new_infections`: -880.77) is bit-identical to the value already recorded
in A2's manual spot check
(`paper2_evidence/p2_ablation_no_branch_separation/manual_spot_checks.md`,
Row 1) for the same (domain, scenario, seed, round) — an independent
cross-check between two differently-implemented pipelines, not a rerun of
the same code path.

`h3_trajectory.json` records the two continuation rounds' metric
divergence as raw numbers for reference. These are **not** a confirmatory
result — one seed, one scenario, one split point — and are not to be cited
as an effect size in any paper. They exist only to confirm the mechanism
produces sane, finite, non-degenerate output before a real H-step
experiment is designed.

## Claim boundary

Supports: cloned-checkpoint continuation is methodologically feasible and
agrees with the adapter's existing internal branch machinery, and the
shared-exogenous-schedule assumption a full H-step design would need holds
at H=3 for this domain. Does not establish: any effect size, any general
claim about continuation length, controller choice, or domain other than
the one tested. Does not activate `paper2b_gate_a` by itself — that gate
also requires `informative_a2_result` (already satisfied by the existing
A2 confirmatory result) and `defensible_general_estimand_question` (a
separate, not-yet-answered design question about what Paper 2B would
actually claim).
