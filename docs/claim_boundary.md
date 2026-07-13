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
