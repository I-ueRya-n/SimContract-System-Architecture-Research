# Reproduction

Independent reproduction of SimContract, its protocol, and the machine-readable
status of the reproductions collected to date. This directory is the
authoritative reproduction record; large raw returned bundles live in the
separate evidence release (Zenodo), not here.

## Contents

- `independent_reproduction_protocol.md` — the protocol an external reproducer
  follows (install → tests → benchmark → verify → replay), including the
  consent/pseudonym and data-handling policy.
- `reproduction_report_template.md` — the report template reproducers return.
- `status.yaml` — machine-readable status of every human reproduction and the
  automated cold-start check, plus the known issue and its remediation state.
- `public_summaries.md` — concise, redacted human-readable summaries.
- `DEFECT_v0.3.0_newline_serialization.md` — forensic note on the Windows
  byte-level serialization defect (`newline-byte-integrity`) found by an
  independent reproduction and fixed in v0.3.1.
- `public/` — redacted public evidence excerpts (e.g. the Windows terminal
  log with usernames and local paths removed).

## Current status (see `status.yaml` for the machine-readable form)

Release reproduced: **v0.3.0** (Zenodo DOI 10.5281/zenodo.21358450), benchmark
`energy_market_v1 / baseline_v1 / seed 73`, expected content hash `dd73a350…`.

| Check | Environment | Result |
|---|---|---|
| Human (Gin) | macOS, Py 3.12 | pass (60/60, hash match, files_ok, replay 5/5) |
| Human (Therese) | Linux/WSL2, Py 3.13 | pass (60/60, hash match, files_ok, replay 5/5) |
| Human (SL) | Windows/MinGW, Py 3.12 | semantic pass, byte-integrity fail (59/60; hash match + replay; files_ok false — `newline-byte-integrity`, fixed in v0.3.1) |
| Automated cold-start | isolated, Py 3.10 | pass, 3/3 (machine-actionability only) |

A v0.3.1 Windows remediation rerun against the final archive is pending.
