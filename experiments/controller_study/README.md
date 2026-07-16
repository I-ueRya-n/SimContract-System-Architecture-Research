# Controller study

Compares controller conditions under the same contract: `rule`,
`random_valid`, `top_score`, `human_script`, `reactive_npc` (pending),
`free_llm`, `bounded_llm`.

Planned structure:

- `paired_runs.py` — paired-seed repeated runs across domains and scenarios;
- `adversarial_cases.py` — malformed/hostile controller output;
- `ablations/` — candidate-set size, final re-validation removed, persona
  removed, preview metrics removed, fallback disabled;
- `rationale_annotation/` — blinded rationale-support assessment.

`reactive_npc` requires per-role `roles/<role>/npc.py` policies, which are
deliberately not yet created (ADR 0007).
