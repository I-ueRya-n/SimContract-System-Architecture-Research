# E3 integration effort — git-defensible measures

Regenerate: `PYTHONPATH=src python3 experiments/e3_integration_effort.py`

Honest limitations recorded in integration_effort.json: both research domains
were introduced in one commit, so per-domain shared-layer impact cannot be
separated retrospectively; no prospective effort diary exists, so no
active-hours are reported (never inferred from commit timestamps).

Headline: the commit introducing both research domains touched 16
domain-specific files (759 LOC) plus one compliance-test file (99 LOC) and
zero shared-layer files (engine, contracts, evidence, analysis, controllers,
plugins, application, composition, cli).
