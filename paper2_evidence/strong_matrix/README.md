# E2-E5 strong matrix — result package

360 canonical runs (2 domains x 2 scenarios x {rule, random_valid, top_score}
x 30 seeds x 6 rounds), each re-executed once (rerun identity) and replayed
once from its bundle. Negative controls per (domain, scenario, condition):
a one-field config change must change the content hash and a tampered bundle
must fail verification. Invariants SC-I1..I7 audited on every bundle.

Regenerate: `PYTHONPATH=src python3 experiments/strong_matrix.py`
Verify:     `PYTHONPATH=src python3 experiments/strong_matrix.py --verify`

Headline: 360/360 rerun hash matches, 360/360 replay-equivalent runs
(2,160/2,160 rounds), 12/12 config-change detections, 12/12 tamper
detections, 0 fallback events, all source tags match the assigned condition,
SC-I1..I7 pass on 360/360 bundles.
