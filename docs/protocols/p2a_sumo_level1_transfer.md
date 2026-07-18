# Paper 2A — SUMO Level-1 External Architecture Transfer

**Protocol version:** 1.0-pre (feasibility-probe stage; not yet frozen for a
confirmatory run -- see the GO/STOP decision in Sec. 6 before that happens)
**Experiment type:** Conditional, non-blocking, single upgrade (Master Plan
`TOP-TIER UPGRADE`, not part of the Paper 2A required submission gate)
**Primary paper:** Paper 2A -- optional RQ2A.6, appears in the manuscript
only if this upgrade is executed and integrated
**Branch:** `experiment/p2a-sumo-level1` (isolated; Candidate A remains
submittable at tag `p2a-submission-candidate-pre-sumo-20260718` regardless
of this branch's outcome)

## 1. Objective

RQ2A.6 (conditional): can an independently developed simulator -- one not
designed for SimContract -- be integrated through the frozen SimContract
contracts and evidence interfaces, without modifying the common core?

This answers a specific reviewer risk that E1-E6/A1/A2/overhead cannot: both
existing domains (`energy_market_v1`, `epidemic_policy_v1`) were designed
*for* SimContract from the start, so their portability evidence may include
a co-design advantage. SUMO was not designed for this architecture.

## 2. What "common core unchanged" precisely means here

The plan's language ("zero common-core changes") needs one precision before
it can be evaluated honestly. `composition.py` is the project's own
documented composition root (ADR 0001/0005); its docstring states plainly
that new domains are wired in there, and every existing domain
(`energy_market_v1`, `epidemic_policy_v1`) already required exactly this:
one `try/except ImportError` registration block plus one `domain_assets()`
branch. That boilerplate is the sanctioned, pre-existing extension seam
(ADR 0005 explicitly reserves "external entry-point discovery" for a later
phase), not a common-core modification in the sense the claim cares about.

**The actual claim under test:** `contracts/`, `engine/`, `analysis/`
(generic analyzers), and the domain-agnostic parts of `application.py` and
the CLI require zero changes. `composition.py`'s per-domain registration
lines are treated the same as they were for the two existing domains: an
expected, bounded, per-domain addition, not a violation. If integrating SUMO
required touching anything outside that seam, the upgrade stops (Sec. 6).

## 3. Upstream simulator

- **Software:** Eclipse SUMO 1.27.1, installed from PyPI (`eclipse-sumo`,
  `traci`, `libsumo`, `sumolib`), Eclipse Public License v2.0.
- **Citation:** Lopez, P.A. et al. (2018). Microscopic Traffic Simulation
  using SUMO. IEEE ITSC.
- **Interface used:** `libsumo` (in-process bindings; API-compatible with
  `traci`, avoids a socket/subprocess round trip per call).
- SUMO is genuinely external: it has its own execution model (an imperative,
  stateful simulation stepped via repeated `simulationStep()` calls against
  a live process/library handle), fundamentally different from the
  pure `state -> Outcome` functions `energy_market_v1` and
  `epidemic_policy_v1` were written as. Bridging that gap is the real
  content of this transfer test, not a formality.

## 4. Feasibility probe (exploratory; findings below, not a confirmatory run)

Scope: one synthetic network (not a real city -- see Sec. 5), one demand
file, seed 1, `libsumo` in-process. Three pre-registered questions, asked
before any adapter code was written:

**Q1 -- does continuing live for N seconds equal
save-state-at-T + reload + continue for N seconds, on the same metric
(total vehicle waiting time)?**
Finding: **no, not beyond a short window.** The two trajectories matched
exactly for the first 5 seconds after the checkpoint, then diverged from
second 6 onward (26.0 vs 23.0 at the 30-second horizon). A follow-up check
showed the *set* of vehicles present is identical between the two branches
at every second of the horizon -- the divergence is not from missing or
extra vehicles. The most likely mechanism (not yet root-caused to source
level, unlike A2's structural findings) is that the traffic light's
internal phase-elapsed timer is not part of what `saveState`/`loadState`
preserves, so the reloaded run's light can switch phase at a slightly
different moment than the live run's, cascading into different individual
vehicle waiting times.

**Q2 -- does forcing a specific traffic-light phase at the checkpoint
change the outcome relative to leaving the default program running (a real
action-to-effect channel)?**
Finding: **yes, strongly.** Default program: 26.0. Forced phase 0: 110.0.
Forced phase 2: 48.0. This is exactly the kind of large, controllable
effect a `step()` implementation needs to expose as a genuine action
surface.

**Q3 -- is checkpoint+reload itself deterministic across repeated,
identical trials?**
Finding: **yes, exactly.** Three repeats of reload-then-continue with no
forced action: `[26.0, 26.0, 26.0]`. Three repeats with a forced phase:
`[127.0, 127.0, 127.0]`. Bit-identical every time.

## 4a. What this means for feasibility -- and a correction

An earlier version of this section overstated Q3's finding as "`step()` is
deterministic given a state," stated without qualification. That is too
strong. What Q3 actually established is narrower:

```text
checkpoint reload repeatability
    != complete checkpoint fidelity
    != uninterrupted-run equivalence
```

Repeated reloads of the *same* saved-state artifact reproduce identical
results (Q3, holds). But because reload diverges from uninterrupted
execution after ~5 seconds (Q1), the saved checkpoint may not contain the
complete internal state needed to represent SUMO's continuous trajectory
exactly. Q3's repeatability is a fact about the checkpoint file, not proof
that the checkpoint is a complete state oracle.

This does not stop SUMO Level 1: the plan permits replay limitations to be
disclosed, and Level 1 is testing external architecture transfer, not
perfect checkpoint restoration.

**Consequence for the adapter design (Sec. 5, revised):** `saveState`/
`loadState` was repeatable across identical reloads but did not remain
equivalent to an uninterrupted execution after approximately five
simulated seconds. The checkpoint is therefore **not treated as a complete
scientific-state oracle**. The Level-1 adapter uses **uninterrupted
execution as the authoritative run semantics** for the trajectory that
actually continues (the "applied" path); verification reruns from the
initial configuration using the recorded action schedule (exactly what
`engine/replay_executor.py`'s existing `replay_bundle()` already does for
every domain -- a fresh `SessionRunner.run()` from round 1, not a mid-run
reload), rather than treating `saveState` as an exact replay oracle.
`saveState`/`loadState` is retained only as a bounded, local device for
computing the single-round authoritative (default-action) counterfactual
alongside the continuing applied trajectory -- never as the mechanism that
carries the real run forward, and never as a multi-round continuation
oracle. The most-likely mechanism for Q1's divergence (the traffic light's
phase-elapsed timer not surviving `saveState`) is stated as a **plausible
cause, not a source-verified one** -- unlike A1/A2's structural findings,
this has not been traced into SUMO's own source.

Superseded text, kept for the record rather than silently deleted: ~~`state`
is defined *as* the saved-checkpoint file (path + content hash), never as
"whatever a continuous run would have produced." `initial_state()` takes
its checkpoint immediately after network load, before any stepping -- so
there is no "continuous ground truth" for later states to be compared
against, and Q1's divergence mechanism never enters any claim this adapter
makes.~~ This treated the checkpoint as load-bearing for the adapter's core
state representation across the whole run, which is exactly the framing
the correction above replaces: the checkpoint is a local, bounded device,
not the state.

## 5. Minimal scenario (not a city digital twin)

- Network: synthetic 3x3 grid, generated by `netgenerate --grid
  --grid.number=3 --grid.length=100 --default.lanenumber=1 --tls.set=B1`
  -- fully reproducible from a documented command, no external dataset, no
  licensing question. One interior 4-way signalised junction (`B1`, 4
  phases).
- Demand: `randomTrips.py -n net_tls.xml -r routes.rou.xml -e 60 --seed 1
  --period 3` -- likewise fully reproducible from a documented command.
- Action surface: force a specific phase at junction `B1` for the round's
  duration (`traci.trafficlight.setPhase` + `setPhaseDuration`), vs. the
  domain default of leaving the loaded program running untouched.
- This is deliberately not: a real city network, calibrated demand, traffic
  data, or multiple intersections. Scaling up is out of scope for Level 1.

## 6. GO decision (from the probe above)

**GO, qualified.** All three feasibility questions were answerable and the
action channel is real and strong (Q2). Q3 shows checkpoint reload is
*repeatable*, not that it is a complete state oracle -- see the correction
in Sec. 4a. The adapter design responds to this directly: uninterrupted
execution is the authoritative run semantics for the trajectory that
actually continues; `saveState`/`loadState` is demoted to a bounded, local
device for the single-round authoritative-branch counterfactual, never the
carrier of the real run. Proceeding to a minimal adapter implementation
(`domains/sumo_transfer_v1/`) under the stop rules in Sec. 7.

## 7. Stop rules (unchanged from the plan; restated here as the frozen list)

Stop and return to Candidate A unchanged if any of the following becomes
true while implementing or running the adapter:

- stable contracts (`contracts/`) must be redesigned;
- SUMO-specific conditional logic must enter the generic engine
  (`engine/`) or generic analyzers (`analysis/`);
- a generic analyzer must be rewritten to understand SUMO's output;
- meaningful control requires modifying SUMO's own source rather than
  driving it through its public `libsumo`/`traci` API;
- reproducible input identity (seed + network + demand + action) cannot be
  established;
- the integration expands toward traffic-model calibration or validation
  (out of scope for an architecture-transfer result);
- the work threatens the Paper 2A submission timeline.

A stopped probe is a valid, reportable result, not a failed programme.

## 8. Success criteria for the minimal adapter (next step, not yet done)

```text
SumoTransferAdapter implements SimulationAdapter (contracts/adapter.py)
    with zero changes to contracts/, engine/, analysis/
one deterministic scenario runs through SessionRunner unmodified
a BundleView-readable evidence bundle is produced
BundleView.load, verify_bundle, replay_run consume it with zero changes
integration-effort measured: adapter-specific files/LOC vs. common-core diff
replay_run (full fresh rerun from round 1 using the recorded action
    schedule, per engine/replay_executor.py -- never a mid-run
    saveState/loadState) reproduces the original applied metrics/branches
```

**Result (smoke stage, `bdb5750`): all 6 gates pass** -- see
`paper2_evidence/p2a_sumo_level1_smoke/README.md`. Not yet sufficient on
its own for a Candidate B integration claim; see Sec. 10-14 for the
confirmatory study this result is upgraded to before that decision.

## 9. Claim boundary and precise footprint wording

**Do not write** "zero common-core files changed" -- the actual result is:

```text
contracts/  changed   0
engine/     changed   0
analysis/   changed   0
evidence/   changed   0
composition root changed   1 file / 12 lines
```

The correct, more credible sentence: *"No frozen contract, engine,
evidence, replay, or generic-analysis implementation was modified.
Integration required one 12-line composition-root registration change
using the same existing seam as the built-in domains."* `composition.py`
is the project's own pre-existing, sanctioned per-domain registration seam
(ADR 0001/0005) -- `energy_market_v1` and `epidemic_policy_v1` each
required the identically-shaped addition when they were added.

Would support: the sentence above, for one minimal controllable scenario,
on this machine. Would not establish: realistic traffic behaviour,
calibration validity, scaling to a real network, or checkpoint-continuation
fidelity beyond what Sec. 4a already discloses.

## 10. Confirmatory matrix design

Not a large traffic experiment. One synthetic network (Sec. 5) x two
demand configurations (`grid3x3_moderate_v1`, 20 vehicles/60s;
`grid3x3_dense_v1`, 60 vehicles/60s -- same `netgenerate` network, two
`randomTrips.py --period` settings, both fully reproducible commands in
`scenarios/grid3x3_v1/GENERATION.md`) x three deterministic conditions x
10 paired seeds = **60 canonical runs**, 10 rounds x 5 simulated seconds
each (inside the probe's verified exact-match window).

**Conditions: `rule`, `fixed_valid_intervention_A` (force phase 2 every
round), `fixed_valid_intervention_B` (force phase 1 every round) -- not
`top_score`.** `preview()` is a disclosed approximation (Sec. 8, returns
the constant last-observed metric regardless of candidate); `top_score`
ranks candidates by their preview, which would be degenerate here and
would manufacture a fair-execution claim `preview()` cannot support. Two
fixed, legal, deterministic interventions give clearly distinguishable,
trustworthy conditions without depending on preview at all.

Seeds vary SUMO's own `--seed` (car-following/insertion-jitter model);
the demand file itself is fixed per `scenario_id`, not regenerated per
seed -- matching how `energy_market_v1`/`epidemic_policy_v1` hold scenario
definitions fixed and vary only the run seed.

**Correction after a first confirmatory pass (phases 1/3, not itself
reported as final).** The first choice of fixed interventions was phase 1
vs. phase 3. Both produced bit-identical `waiting_time` across every one
of the 10 paired seeds, in both demand configurations -- not a bug.
`net.xml`'s `tlLogic` (source-inspected, not assumed) defines four phases:
`0` NS-green (42s), `1` NS-yellow (3s), `2` EW-green (42s), `3` EW-yellow
(3s). Phases 1 and 3 are both short, all-restrictive transition phases;
locking either one for a full round blocks the junction equivalently,
regardless of which approach's yellow it nominally is. This made phases 1
and 3 a degenerate pair for demonstrating "distinguishable legal
interventions" -- structurally analogous to A2's own STATE_FIELDS
correction (a field that looked plausible until source-inspection showed
it carried no distinguishing information). **Corrected** to phase 2
(EW-priority -- meaningfully asymmetric to `rule`'s NS-priority phase 0)
and phase 1 (all-stop transitional -- meaningfully distinct from both).
The confirmatory matrix in Sec. 10-14 uses the corrected pair; the
degenerate first pass is not reported as evidence.

## 11. Per-run verification checklist

Every one of the 60 runs must satisfy all of:

```text
fresh execution succeeds (no exception)
bundle verification passes (verify_bundle: content_hash_ok, files_ok)
full replay from round 1 succeeds (replay_bundle: .equivalent)
recorded actions reproduce evidence (0 mismatches)
generic analyzer succeeds (report generated)
no orphan SUMO process remains after this run's explicit cleanup
configuration/input hashes resolve (net.xml + routes file + seed + condition digest)
```

Aggregate report: run-level replay pass rate, evidence mismatch count,
process-cleanup failure count (checked externally via `pgrep -f sumo`
before/after the whole matrix, not just per-run), contract/compliance pass
rate, scenario/configuration identity, bundle size and wall-clock time per
run, adapter files/LOC, composition-root change size, and disclosed
exceptions.

## 12. Explicit cleanup discipline

`__del__` (Sec. 8's smoke stage) is a safety net, not the primary
mechanism -- CPython does not guarantee its timing across all execution
paths, and a confirmatory claim of zero leaked processes needs a
deterministic guarantee. `SumoTransferAdapter.close()` is an
adapter-owned, non-contract method (adding it does not modify
`SimulationAdapter`); the confirmatory runner constructs the adapter and
`SessionRunner` directly -- mirroring `Application.run_session()`'s own
construction path, the same technique `experiments/overhead/
phase_overhead.py`'s `_plain_equivalent_run()` already uses for a
different reason -- specifically so it can hold a reference to call
`adapter.close()` in a `finally` block around both the original run and
the replay rerun.

## 13. Confirmatory stop rule (in addition to Sec. 7)

Stop and do not create a Candidate B integration if any of:

- replay mismatch rate is greater than 0 on any of the 60 runs;
- any leaked SUMO process is detected after the full matrix completes;
- reliable cleanup requires anything beyond the adapter-owned `close()`
  method;
- a fair controller comparison would require relying on the disclosed
  `preview()` approximation (this is exactly why Sec. 10 uses fixed
  interventions instead of `top_score`).

## 14. Candidate B decision rule

Integrate a compact external-transfer subsection into Paper 2A
(RQ2A.6) if and only if: all 60 runs complete, replay/verification pass
rate is complete, the generic analyzer works unchanged, no frozen layer is
modified, the composition change remains the declared 12-line seam, zero
processes are leaked, and the result fits the page budget without cutting
A1/A2/overhead. Otherwise: keep the confirmatory result as a standalone
feasibility artifact and submit Candidate A unchanged.
