# Claim boundary

What the SimContract evidence programme does and does not support.

## Supported by the current programme

- cross-domain **contract portability** (adapter substitution under one
  protocol, compliance suite, integration-effort accounting);
- **simulator-authoritative** state transition (controllers never mutate);
- **controller comparability** (six conditions through one validation path);
- **two-tier validation** separation (engine syntactic / adapter semantic);
- **complete decision provenance** (adapter-returned resolution truth,
  candidate sets, scores, rationales, state digests);
- **reproducible bundles and replay** (canonical content hashes, LLM-off
  rerun identity, decision replay, bundle verification);
- **bounded-AI structural validity and failure containment** (selection from
  validated candidates; observable degradation with denominators);
- **analysis-interface extensibility** (analyzer registration without core
  changes).

## Not claimed without further evidence

- universal model agnosticism (claims are cross-domain over the implemented
  domains, plus a future external adapter);
- externally validated domain predictions — both research domains are
  controlled, literature-informed testbeds, not calibrated forecasters;
- human-equivalent agents, better real-world decisions, realistic
  stakeholder behaviour;
- serious-game usability or learning effectiveness (no human sessions;
  the system is *human-ready* via the controller contract, ADR 0006);
- real-time digital-twin status;
- scientific correctness of any wrapped external model (upstream vs adapter
  contributions are separated in provenance records).

Papers describe the system as a **simulation-based decision experiment
architecture**. Analyzer claims are about interface extensibility and
consistency, not the scientific validity of a particular method.

## Claim-boundary matrix

| Claim | Status | Evidence | Boundary |
|---|---|---|---|
| Cross-domain contract portability | supported | E3: one protocol on 3 domains, zero engine/analyzer diff; compliance suite | portability over the implemented domains + a future external adapter — not universal model agnosticism |
| Simulator-authoritative transitions | supported | controllers never mutate; only `adapter.step()` resolves; dependency audit | architectural guarantee, not a claim about decision quality |
| Two-tier validation separation | supported | rejection tests tag `engine_syntactic` / `adapter_semantic` | — |
| Complete decision provenance | supported | adapter-returned `ResolutionReport`; decision records with state digests | returned truth; provenance ≠ correctness |
| Reproducible bundles + replay | supported | E2: rerun identity hashes, replay 5/5, verification tamper-detect | LLM-off runs; live-LLM runs measure stability, not identity |
| Bounded-AI structural validity + containment | supported (containment) | E4 LLM-off: degrades on every slot, all runs complete, denominators | outage containment executed; live-LLM behavioural quality = Paper 3, TBD |
| Analysis-interface extensibility | supported | E6: 4th analyzer registered at runtime, zero core diff, lineage | interface extensibility, not method validity |
| Model-defined decision quality | scoped, mostly TBD | best-of-candidate regret vs `top_score` (design) | model-relative, candidate-set-relative — never global optimum |
| Behavioural plausibility of NPC/AI | NOT claimed | — | requires behavioural data / calibration (out of scope) |
| External / real-world validity | NOT claimed | — | domains are controlled testbeds; requires calibration + real data |

Required wording for Papers 2–3: *SimContract makes validation evidence
explicit and reproducible; it does not by itself establish the external
validity of the underlying models or the real-world rationality of the
controllers.*
