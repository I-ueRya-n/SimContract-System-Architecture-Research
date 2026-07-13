"""Static report generation: CSV + markdown out of AnalysisResults."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .base import AnalysisResult


def write_report(results: list[AnalysisResult], out_dir: str | Path) -> Path:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# SimContract analysis report", ""]
    for res in results:
        lines.append(f"## {res.spec.analysis_id} v{res.spec.version}")
        lines.append("")
        lines.append(f"lineage: `{json.dumps(res.lineage, sort_keys=True)}`")
        lines.append("")
        for name, rows in res.tables.items():
            csv_path = d / f"{res.spec.analysis_id}_{name}.csv"
            if rows:
                with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
            lines.append(f"- `{name}`: {len(rows)} rows -> `{csv_path.name}`")
        lines.append("")
    (d / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return d / "report.md"
