"""Trace files: JSONL streams, long-form metrics CSV, HTML summary."""
from __future__ import annotations

import csv
import html
import io
from dataclasses import asdict
from pathlib import Path

from simcontract.contracts import (
    DecisionRecord,
    FailureRecord,
    InvocationRecord,
    RoundRecord,
    RunManifest,
)

from .hashing import write_jsonl, write_text


def write_traces(d: Path, decisions: list[DecisionRecord],
                 events: list[FailureRecord],
                 invocations: list[InvocationRecord]) -> dict[str, str]:
    return {
        "decisions.jsonl": write_jsonl(d / "decisions.jsonl",
                                       [asdict(r) for r in decisions]),
        "fallback_events.jsonl": write_jsonl(d / "fallback_events.jsonl",
                                             [asdict(r) for r in events]),
        "llm_invocations.jsonl": write_jsonl(d / "llm_invocations.jsonl",
                                             [asdict(r) for r in invocations]),
    }


def write_metrics_csv(d: Path, rounds: list[RoundRecord]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["round", "branch", "metric", "value"])
    for r in rounds:
        for branch, metrics in sorted(r.branches.items()):
            for key, value in sorted(metrics.items()):
                writer.writerow([r.round_no, branch, key, value])
    return write_text(d / "metrics.csv", buf.getvalue())


def write_report_html(d: Path, manifest: RunManifest, rounds: list[RoundRecord],
                      register: dict) -> str:
    e = html.escape
    rows = "".join(
        f"<tr><td>{r.round_no}</td><td>{e(', '.join(f'{k}={v}' for k, v in sorted(r.system_metrics.items())))}</td></tr>"
        for r in rounds)
    families = "".join(
        f"<li>{e(fam)}: {info['count']} ({e(', '.join(f'{k}×{v}' for k, v in sorted(info['reasons'].items())))})</li>"
        for fam, info in sorted(register.get("families", {}).items())) or "<li>none</li>"
    denom = register.get("denominators", {})
    text = f"""<!doctype html><meta charset="utf-8"><title>{e(manifest.run_id)}</title>
<h1>SimContract evidence bundle</h1>
<p><b>run</b> {e(manifest.run_id)} · <b>domain</b> {e(manifest.domain_id)}
v{e(manifest.adapter_version)} · <b>scenario</b> {e(manifest.scenario_id)}
· <b>seed</b> {manifest.run_seed} · <b>rounds</b> {manifest.rounds}</p>
<p><b>content hash</b> <code>{e(str(manifest.content_hash))}</code></p>
<p><b>conditions</b> {e(str(manifest.conditions))}</p>
<h2>Failure register (denominators: {e(str(denom))})</h2><ul>{families}</ul>
<h2>Applied-branch metrics per round</h2>
<table border="1" cellpadding="4"><tr><th>round</th><th>metrics</th></tr>{rows}</table>
<p><i>{e(manifest.claim_boundary)}</i></p>
"""
    return write_text(d / "report.html", text)
