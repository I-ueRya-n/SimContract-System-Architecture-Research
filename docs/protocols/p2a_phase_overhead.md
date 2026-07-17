# Paper 2A — Phase-Level Overhead Decomposition

**Protocol version:** 1.0 (frozen 2026-07-17 after a feasibility probe that added T_candidate_generation and redesigned the instrumentation-tax measurement; see §4a)
**Experiment type:** Controlled instrumentation (paired against uninstrumented production runs; no staged feature disabling)
**Primary paper:** Paper 2A — Cross-Domain Contract Portability
**Implementation:** `experiments/overhead/phase_overhead.py`

## 1. Objective

RQ2A.5: what execution and evidence overhead does the architecture
introduce, and where does it come from? Success is **not** zero overhead —
it is transparent, bounded, reproducible overhead with phase attribution.

## 2. Method: instrumentation, not staged disabling

An earlier design (C0–C5, disabling mechanisms one at a time) was rejected:
it would require production toggles that do not exist and risks changing
execution semantics to manufacture comparison points. Instead, every phase
is measured by **wrapping the existing public objects** passed into
`SessionRunner` — the observation policy, each controller, the adapter, and
the evidence sink — in timing proxies that record `time.perf_counter()`
around each delegated call and then call straight through to the real
object. `content_hash_of` (a separately importable pure function called once
inside `BundleEvidenceWriter.finalise()`) is wrapped the same way at its
module binding, restored immediately after measurement. No proxy alters an
argument, a return value, or control flow — each is verified functionally
transparent (§4).

## 3. Phases measured

```text
T_candidate_generation   action_space() + preview() per candidate, via
                         engine.session.candidates_and_previews (module wrap) --
                         added after the feasibility probe (§4a): the initial
                         7-phase decomposition left 93% of wall-clock
                         unattributed, traced to this uninstrumented phase.
T_observation            ObservationPolicy.view() -- summed over all slots/rounds
T_controller             RoleController.act() -- summed over all slots/rounds
T_validation_syntactic   engine.session.validate_intake (module-level wrap)
T_validation_semantic    SimulationAdapter.validate_semantic()
T_resolution             SimulationAdapter.step() (branch computation + report)
T_evidence_collection    EvidenceSink.record_round/record_decision/record_event/record_invocation
T_hashing                content_hash_of() inside finalise()
T_evidence_persistence   finalise() minus T_hashing (file writes: rounds.json,
                         traces, register, metrics.csv, manifest, report.html)
T_branch_recording       residual = wall-clock run() time minus the sum of the
                         eight measured phases above (RoundRecord packaging,
                         seed/rng derivation, metric-catalog validation, and
                         proxy attribute-resolution instrumentation overhead;
                         reported as an explicit, labelled residual, never
                         hidden inside another phase -- see §4a on its size)
```

`T_replay_or_verification_support` is measured **separately**, after the
run, as `replay_run()` and `verify_bundle()` wall-clock time on the produced
bundle. It is reported alongside, not summed into `T_total`: replay/verify
is a distinct post-hoc workload on a persisted artifact, not a phase of
producing that artifact, and the plan itself cautions against comparing
unrelated workloads in one figure.

## 4. Feasibility probe (exploratory; not reported as confirmatory)

Before trusting any phase number, on 1 domain, 1 scenario, `rule`, 3 seeds:

1. **Semantic transparency:** an instrumented run and an uninstrumented
   `Application.run_session` call on the same (domain, scenario, seed,
   condition) must produce the **same content hash**. Any mismatch aborts.
2. **Reconciliation:** the sum of the measured phases plus the residual
   must equal the measured wall-clock `run()` time exactly (the residual is
   defined as the remainder, so this is true by construction; the probe
   instead checks the residual is a bounded, sane fraction of the total).
3. **Stability:** two repeated measurements of the same configuration must
   have phase totals within a documented tolerance of each other.
4. **No double-counting:** `T_evidence_persistence` is derived by
   subtraction specifically so hashing time can never be counted twice.

## 4a. Probe findings and two protocol revisions

**Finding 1 (incomplete decomposition, corrected).** The first probe pass
(7 phases, no `T_candidate_generation`) reconciled at only 7% of wall-clock
(93% residual) — a real gap, not a rounding error. Tracing it found
`candidates_and_previews()` (`action_space()` + one `preview()` call per
candidate, 8 candidates by default) running entirely outside any timed
phase. Added as `T_candidate_generation` (§3); the probe then reconciled at
39–43% residual, which was accepted (§4b).

**Finding 2 (noisy single-pair instrumentation tax, corrected by design,
not by discarding the result).** The probe additionally compares
instrumented vs. uninstrumented wall-clock as an "instrumentation tax." A
single paired comparison was **not stable** — repeated probe runs produced
tax estimates ranging from −28% to +2% of the uninstrumented time,
including negative values, on a workload of only ≈30 ms per 6-round run.
Root cause: at this scale, run-to-run system noise (OS scheduling,
allocator/GC variance, CPU frequency scaling) is comparable to or larger
than the quantity being measured; an early version additionally confounded
this with cold-start effects by always running the uninstrumented call
first (fixed by adding a discarded warm-up call before each timed call,
which changed the sign but not the instability). **Consequence for the
confirmatory design (§5a):** the instrumentation tax is not reported from a
single pair. It is reported as a paired median over a repeated subsample,
large enough that system noise averages out, and is explicitly bounded as
"not confidently distinguishable from a few percent either way at this
workload scale" if that is what the data show — this is a legitimate
finding about a lightweight architecture, not a measurement failure.

## 4b. Accepted probe result

Semantic transparency: pass (hash match, all runs). Stability: pass (phase
totals within 0.8–1.12x across repeats). Reconciliation: residual 57–61% of
wall-clock, accepted as `T_branch_recording` and reported as a named,
explicit bucket (§3) rather than pursued to near-zero — for this
architecture's very light per-round domain compute, fixed per-round
bookkeeping (seed derivation, dict/dataclass construction, metric-catalog
validation, and the timing proxies' own `__getattr__` dispatch) genuinely
dominates wall-clock at the 6-round, single-run scale tested. This is
reported as a characteristic of the implementation and the workload size,
not hidden or reduced by construction.

## 5. Confirmatory matrix

Reuses the canonical strong-matrix scope for direct comparability with
E2–E5: 2 domains x 2 scenarios x 3 deterministic conditions (`rule`,
`random_valid`, `top_score`) x 30 seeds x 6 rounds = 360 runs. LLM
conditions excluded (external endpoint latency is not architecture
overhead). Each run is measured once (instrumentation itself is
lightweight; repetition-based variance is covered by the 30-seed spread,
consistent with the probe's stability check rather than per-run repeats).

## 5a. Instrumentation-tax subsample

Per §4a Finding 2, a single instrumented-vs-uninstrumented comparison is
noise-dominated at this workload scale. One fixed configuration
(`energy_market_v1`, `baseline_v1`, `rule`, seed 1) is run 20 times
alternating instrumented/uninstrumented, each preceded by one discarded
warm-up call of the same kind, and the paired median difference is
reported as the instrumentation tax, with the full paired sample so the
spread is visible alongside the point estimate.

## 6. Reporting

Per phase, per domain: median, p95, maximum, mean share of total runtime
(%). Also: bundle size on disk (bytes), trace file bytes (`decisions.jsonl`
+ `fallback_events.jsonl` + `llm_invocations.jsonl`), and replay/verify
wall-clock time as a separate figure. No claim of universality beyond the
evaluated domains, scenarios, and machine.

## 7. Claim boundary

Supports: a transparent, phase-attributed account of where architectural
overhead is spent in this implementation, on this machine, for these
domains. Does not establish: absolute performance competitiveness against
other frameworks, scalability beyond the tested round/seed counts, or
overhead under a live LLM endpoint (network-dominated, out of scope).
