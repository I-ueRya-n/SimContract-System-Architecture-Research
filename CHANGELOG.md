# Changelog

All notable changes to SimContract are documented here. This project follows
semantic versioning; v0.3.x releases are backward-compatible bug-fix and
assurance releases.

## v0.3.1 (unreleased) — cross-platform serialization remediation

### Fixed
- **Cross-platform per-file bundle verification (newline serialization).**
  Evidence files were written with `Path.write_text`, whose text mode
  translates `\n` to `\r\n` on platforms that rewrite newlines (and turns the
  CSV's `\r\n` into `\r\r\n`), while the recorded per-file hash was taken from
  the in-memory LF string. The on-disk bytes then disagreed with the recorded
  hash, so `verify` reported `files_ok: false` and one unit test
  (`test_verify_intact_bundle`) failed on Windows. The canonical `content_hash`
  and decision `replay` were unaffected. Writers now emit canonical UTF-8 bytes
  and hash exactly the bytes written, so the recorded hash equals the on-disk
  bytes on every platform. On POSIX the produced bytes are identical to
  v0.3.0, so the frozen `energy_baseline_v1_seed73` benchmark still verifies
  and reproduces content hash `dd73a350…` unchanged.

  This defect was found by an independent third-party Windows reproduction of
  v0.3.0 (see `reproduction/`), which reproduced the canonical content hash and
  replay exactly while exposing the byte-level mismatch.

### Added
- Regression tests (`tests/replay/test_newline_serialization.py`) locking the
  invariant that the recorded per-file hash equals the SHA-256 of the exact
  on-disk bytes, that canonical evidence files carry no platform newline
  translation, and that `metrics.csv` never gains a doubled carriage return.
- Cross-platform CI (`.github/workflows/ci.yml`): unit tests and a
  reproduction smoke check (content hash + `files_ok` + replay) on
  Ubuntu, macOS, and **Windows**, plus a wheel-install smoke on Ubuntu and
  Windows.
- `scripts/reproduction_smoke.py`: regenerates the frozen benchmark and asserts
  content-hash match, `files_ok`, and replay equivalence; exits non-zero on any
  mismatch.

### Notes
- The verifier was **not** changed to normalize newlines before hashing: doing
  so would weaken the exact byte-level integrity guarantee and would hide real
  serialization defects (such as the `\r\r\n` CSV double-CR). The fix is at the
  writer, which now produces canonical bytes.

## v0.3.0

Frozen release archived at Zenodo (DOI 10.5281/zenodo.21358450), commit
`c3654d8`. Validation-aware, simulator-authoritative multi-stakeholder
simulation framework with a hashed, replayable evidence bundle; two research
domains (`energy_market_v1`, `epidemic_policy_v1`), a reference stub, a 60-test
suite, the E1–E7 evidence programme, and a deterministic benchmark.
