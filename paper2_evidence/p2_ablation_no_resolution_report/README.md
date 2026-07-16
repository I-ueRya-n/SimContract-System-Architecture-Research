# Paper 2 Ablation A1 — result package

Confirmatory matrix: 2 domains x 2 scenarios x 30 seeds x 6 rounds (120 runs,
3,600 resolved role-decision slots). Protocol v1.0.1 (hash in protocol.sha256);
frozen configuration in experiment_config.yaml (hash alongside). LLM disabled.

Regenerate: `PYTHONPATH=src python3 experiments/ablations/no_resolution_report.py`
Verify:     `PYTHONPATH=src python3 experiments/ablations/no_resolution_report.py --verify`

Headline: withholding the adapter-returned ResolutionReport leaves source tag,
completion status, completion reason, and rejection stage fully reconstructable
from engine-visible records (3600/3600), but the identity of the final applied
action is unrecoverable for every domain-completed slot (2974/3600 slots under
the injected failure mix), because the applied action is produced by the
adapter's default policy evaluated against current state inside step().
