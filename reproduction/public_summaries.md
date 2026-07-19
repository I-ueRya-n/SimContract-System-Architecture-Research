# Independent reproduction summaries (public, redacted)

Concise, honest summaries of the independent reproductions of SimContract
v0.3.0 and the automated cold-start machine-actionability check. Reproducers
consented to publication and are identified by their chosen handles. Full
returned bundles (terminal logs, complete `benchmark-reproduction/`
directories) are archived in the separate evidence release; this repository
keeps summaries, the machine-readable `status.yaml`, the protocol, and the
defect note. See `DEFECT_v0.3.0_newline_serialization.md` for the Windows
finding and `status.yaml` for the machine-readable record.

Common target: `energy_market_v1 / baseline_v1 / seed 73 / 5 rounds /
all=rule`, expected canonical content hash `dd73a350…`.

## Human reproductions

### Gin — macOS 26.5.1 (Apple M2), Python 3.12.7 (2026-07-17)
Clean install, `60/60` tests, content hash `dd73a350…` match, `verify`
`content_hash_ok` + `files_ok` true, replay `5/5` equivalent. No assistance,
no deviations. **Status: pass.**

### Therese — Linux Ubuntu 22.04 (WSL2), Python 3.13.5 (2026-07-19)
Built from the authentic Zenodo archive, `60/60` tests, content hash
`dd73a350…` match, `content_hash_ok` + `files_ok` true, replay `5/5`
equivalent; a second run re-emitted the same hash. All canonical evidence
files byte-identical to Gin's, manifests differing only in a timestamp.
**Status: pass.**

### SL — Windows 11 25H2 (MinGW/MSYS2 Python), Python 3.12.9 (2026-07-19)
Authentic source archive (`20174f58…`). Canonical content hash `dd73a350…`
**match** and replay `5/5` **equivalent** — the primary determinism guarantees
held on Windows. However `59/60` tests (one failure:
`test_verify_intact_bundle`) and `files_ok: false`, both from platform newline
translation: text files were written `CRLF` (the CSV `CRCRLF`), so raw byte
hashes differed from the recorded hashes while every file was content-identical
after normalization. Minor environment deviation: the MinGW Python created a
Unix-style `.venv/bin` layout, requiring an activation-path adjustment.
**Status: semantic pass, byte-level integrity fail** — the defect
(`newline-byte-integrity`) is fixed in v0.3.1; a v0.3.1 Windows remediation
rerun is pending. Redacted terminal log: `public/windows-sl-terminal.redacted.md`.

## Automated documentation execution (machine-actionability)

### Cold-start agent check — 3 trials (Linux WSL2, Python 3.10.12)
A context-isolated, cold-start tool-using agent (Claude Opus 4.8 under the
Claude Code agent harness) was given only the frozen archive, its shipped
documentation, and a high-level objective — no commands, no expected hash, no
success path. Across **3/3** clean-start trials it independently discovered and
executed install → tests → benchmark → verify → replay, reproducing
`dd73a350…` with `files_ok` true and `60/60` tests, without modifying source or
documentation. All three surfaced the same self-recovered documentation gap
(README runs `pytest` before installing the `[dev]` extra that provides it).
**Boundary:** this is not a human reproducer and not evidence of human
usability, general agent compatibility, or community adoption — only
documentation machine-actionability under one model-and-harness configuration.
