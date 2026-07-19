# Who should use SimContract

SimContract is a decision-governance and evidence layer for reproducible
simulation experiments. It is a good fit for some workflows and a poor fit for
others; this page states both plainly.

## A good fit if you need

- **Multi-role controller comparison** — compare human, rule-based, ranked, or
  LLM-assisted controllers for one or more stakeholder roles under identical,
  seeded conditions.
- **Governed LLM-in-the-loop simulation** — let an LLM stand in for a
  participant while every action passes the same validation as any other
  controller and every invocation is recorded with denominators.
- **Reproducible, auditable experiments** — you want each run to be a
  content-hashed, replayable, verifiable research object by construction, not
  assembled afterwards.
- **Evidence-/replay-heavy workflows** — provenance, decision replay, bundle
  verification, and lineage-tracked offline analysis matter to your study or to
  your reviewers.

## Not the right tool if you need

- **Spatial/GIS model primitives** or a modelling DSL — use an ABM framework
  such as Mesa or GAMA (see `docs/positioning.md`); a model built there can
  later be wrapped behind the adapter contract.
- **A real-time or streaming digital twin** — SimContract is headless, seeded,
  and batch by design; that is what makes bit-identical rerun and replay
  possible.
- **Large-scale distributed simulation** — there is no cluster/worker runtime.
- **Interactive ABM visualization** — there is no built-in visual front end;
  analysis is offline over evidence bundles.

## In one line

Choose SimContract when the research question is *"which governed decision
policy, and can I prove the run"* — not when the task is *"build and visualize
a spatial agent model."*
