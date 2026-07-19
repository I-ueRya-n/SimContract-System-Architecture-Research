"""Cross-platform reproduction smoke check.

Regenerates the frozen deterministic benchmark and asserts three things:
the canonical content hash matches the archived expectation, byte-level
per-file verification passes (``files_ok``), and decision replay is
equivalent. Exits non-zero on any mismatch, so the CI matrix (including a
native Windows runner) catches serialization regressions such as the v0.3.0
newline defect fixed in v0.3.1.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED = "dd73a35091a5fb609cea12fb8b84fa4858d7cbf87d0c4469765d672a3b0be7bc"


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "simcontract.cli", *args],
        capture_output=True, text=True,
    )


def main() -> int:
    out = Path(tempfile.mkdtemp()) / "bench"
    run = _cli("run", "--domain", "energy_market_v1", "--scenario",
               "baseline_v1", "--seed", "73", "--rounds", "5",
               "--controllers", "all=rule", "--out", str(out))
    if run.returncode != 0:
        print("run failed:\n", run.stderr)
        return 1
    if EXPECTED not in run.stdout:
        print("expected content hash not printed by run:\n", run.stdout)
        return 1

    verify = _cli("verify", "--bundle", str(out))
    verdict = json.loads(verify.stdout)
    if not verdict.get("content_hash_ok"):
        print("content_hash_ok is false:", verdict)
        return 1
    if not verdict.get("files_ok"):
        print("files_ok is false (byte-level per-file verification failed):",
              verdict)
        return 1
    if verdict.get("content_hash_recomputed") != EXPECTED:
        print("content hash mismatch:", verdict)
        return 1

    replay = _cli("replay", "--bundle", str(out))
    if "REPLAY EQUIVALENT" not in replay.stdout:
        print("replay not equivalent:\n", replay.stdout)
        return 1

    print("reproduction smoke OK:",
          "content_hash_ok, files_ok, replay equivalent; hash",
          EXPECTED[:12] + "...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
