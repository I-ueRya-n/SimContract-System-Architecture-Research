# Paper 2B-E6 — External Integrity Replication (SUMO) + E5 Layer-3

**Protocol version:** 1.0 (frozen 2026-07-18; feasibility spike §4 and pilot
findings §9 precede this freeze; the confirmatory matrix and the external
manifest oracle are frozen by this document.)
**Experiment type:** External replication of the CL-vs-MT distinction on an
independently developed simulator, plus the E5 checker's Layer-3
(external-manifest) evaluation.
**Primary paper:** Paper 2B. **Implementation:**
`experiments/paper2b/e6_external_replication.py`.
**Depends on:** E2/E4 (the estimand + decision machinery), E5 (the frozen
checker), and Paper 2A's SUMO Level-1 adapter (the external simulator
infrastructure; its 60-run architecture-transfer table is NOT reused as an
E6 result).

## 1. Research question

Does the CL--MT estimand distinction and the portable integrity checker
transfer to an independently developed, imperative traffic simulator
(Eclipse SUMO~\cite{lopez2018sumo}) under controlled demand and continuation
policies? Success is external transfer of the methodology, not a dramatic
failure: MT $\approx$ CL (external positive boundary), MT biased but ranking
stable (external approximation), or MT changes sign/ranking (external
divergent) are all legitimate outcomes.

## 2. Literature gate (two narrow passes; classic + recent)

Pass 1 (simulator/semantics, before the feasibility spike): Lopez et
al.~\cite{lopez2018sumo} (SUMO foundational), Krajzewicz et
al.~\cite{krajzewicz2012sumo} (development/demand semantics), Wegener et
al.~\cite{wegener2008traci} (TraCI runtime control). Pass 2
(traffic counterfactual/comparison, after the feasibility GO): Wei et
al.~\cite{wei2019tscsurvey} (signal-control comparison methodology), Chen et
al.~\cite{chen2020thousandlights} (large-scale signal-control comparison),
Li et al.~\cite{li2025cflight} (CFLight -- counterfactual, backtrack-and-try
traffic signal control, the closest on-theme neighbour). The gap: existing
traffic-counterfactual work does counterfactual \emph{learning}, not an
audit of whether the comparison preserves \emph{estimand identity}
(cloned-state vs matched-history).

## 3. CL/MT construction: deterministic replay-to-branch, not saveState

The Paper 2A SUMO probe showed `saveState`/`loadState` is repeatable but not
a complete continuous-state oracle. E6 therefore reconstructs pre-decision
states by \emph{deterministic replay from origin}: to reach the pre-decision
state at round $t$ under a given standing policy, start SUMO fresh (same
version, net, demand file, seed) and replay that policy for rounds
$1..t{-}1$. Mirroring 2B-E4:

```text
baseline B : default-history + default action, continue H
CL_i       : DEFAULT-history clone at t, apply candidate i, continue H
             (every candidate scored from the SAME reconstructed checkpoint)
MT_i       : candidate-i standing-policy history at t, apply candidate i,
             continue H (each candidate scored from its OWN evolved history)
```

CL's shared clone is verified by reconstructing it twice and requiring
byte-identical observable pre-states (the feasibility-spike guarantee).
Effects vs baseline: `d_cl_i = CL_i - B`, `d_mt_i = MT_i - B`;
`AE_i = |MT_i - CL_i|`.

## 4. Feasibility spike (executed before this freeze)

Five gates on the grid scenario at a congested decision point: (1) two
independent replays of the same history reach a byte-identical observable
pre-state; (2) two no-intervention continuations are bit-identical; (3)
repeating the reconstruction reproduces the result; (4) a different
intervention at $t$ changes the outcome (real CL action channel: default
258 vs EW-priority 164 vehicle-seconds); (5) a default history reaches a
different pre-state than a candidate history. All five pass -- GO for
replay-to-branch. Evidence:
`paper2_evidence/p2b_e6_external_replication/feasibility_spike/`.

## 5. Metric

Primary: **normalised cumulative waiting** (vehicle-seconds of delay,
summed from origin; halting = speed $<0.1$ m/s), IQR-normalised over the
baseline population per demand. Cumulative (not instantaneous) is required:
an instantaneous snapshot washes out the pre-decision history by the horizon
(same future demand $\to$ same vehicles present), giving $AE\approx0$
trivially; cumulative delay retains the history. Secondary traffic metrics
(queue length, throughput, travel time) are out of scope for v1.0.

## 6. Endpoints

Primary: `AE_i` normalised, and the external-boundary classification
(exact / approximation / divergent) at the preregistered tolerance
`TOL_REL = 0.10` (reused from E3). Secondary: sign disagreement between
`d_cl` and `d_mt`; tie-aware top-1 ranking disagreement over the four
candidate signal programmes per decision set (a set counts only when neither
the CL nor the MT top is value-tied, as in E4); `AE` by horizon;
state/history-distance flag.

## 7. E5 Layer-3 external-manifest evaluation (second deliverable)

A SUMO-specific `export_manifest` builds portable audit manifests (v1.0)
from SUMO execution identities. The exporter imports \emph{nothing} from the
checker, does not consult checker diagnostics, and does not reuse the E5
held-out mutation generator. The FROZEN E5 checker (code hash from E5) is
run ONCE on: intact manifests (all four estimand types, expected verdicts
per the claim-compatibility spec) and naturally-limited/negative cases with
a prospectively-defined oracle -- `saveState_not_continuous` (a
non-shared-clone pre-state: a defect for local claims, legitimate for
MT/RS), `schedule_partial` (covers $H{-}1$), `policy_unrecorded`,
`history_declared_local` (a historical comparison mislabelled cloned-local),
`metric_incomplete`. Reported: status accuracy, false-positive rate on
intact SUMO manifests, negative-case detection.

## 8. Confirmatory matrix

Grid scenario (controlled companion; a public/upstream SUMO scenario is the
next external-realism step, noted as future work) $\times$ 2 demand
configurations (moderate, dense) $\times$ 10 seeds $\times$ 2 decision rounds
$\times$ 4 candidate signal programmes $\times$ $H\in\{1,3,5\}$. The unit is
the decision set (demand, seed, round, horizon); candidates within a set are
correlated. No production `src/` change; the E2 machinery is mirrored, not
imported, and the frozen E5 checker is used unchanged.

## 9. Pilot findings (implementation/reporting only; design then frozen)

Pilot (1 demand, 3 seeds): all corrections were implementation- or
oracle-level, none changed the design. (i) The initial instantaneous
waiting-time metric washed out history ($AE\approx0$); switched to
cumulative waiting (§5). (ii) Ranking disagreement was tie-dominated;
added tie-aware counting (§6). (iii) The first CL construction cloned each
candidate's own history; realigned to E4's shared-clone construction (§3).
(iv) The Layer-3 oracle initially over-expected FAIL on
`saveState_not_continuous` for MT/RS -- but MT/RS legitimately allow
different pre-states, so the frozen checker's PASS is correct; the oracle
(ground truth) was corrected, the checker was not touched. After these
corrections the pilot shows an external-divergent boundary and a
Layer-3 status accuracy of 1.0 with 0\% false positives.

## 10. GO/STOP and claim boundary

GO held: replay-to-decision reconstruction is exact, demand/seed identity is
fixed, CL and MT are cleanly operationalised, continuation policy is shared,
metrics align, the manifest exporter is checker-independent, and the frozen
checker runs unchanged -- no Paper 2A frozen architecture was modified.
Supports: the CL--MT distinction and the portable checker transfer to an
external imperative traffic simulator, with a boundary classification and a
Layer-3 checker result. Does not establish: real-world traffic-policy
correctness (uncalibrated, model-relative), generality beyond the grid
scenario and the cumulative-waiting metric, or completeness of the checker
on manifests from sources other than this exporter.
