# v0.3.0 defect: cross-platform newline serialization in per-file hashing

**ID:** `newline-byte-integrity` · **Affects:** v0.3.0 · **Fixed in:** v0.3.1 ·
**Discovered by:** an independent third-party Windows reproduction (reproducer
SL, 2026-07-19).

## Summary

On v0.3.0, regenerating the frozen benchmark on Windows reproduced the
**canonical content hash exactly** (`dd73a350…`) and replayed `5/5` rounds
equivalent, but `verify` reported **`files_ok: false`** and one unit test
(`test_verify_intact_bundle`) failed. Canonical content identity and decision
replay were unaffected; only byte-level per-file verification failed.

## Root cause

The evidence writers wrote files with `Path.write_text(..., encoding="utf-8")`
and recorded each file's hash as the SHA-256 of the **in-memory** string:

```python
path.write_text(text, encoding="utf-8")           # text mode
return hashlib.sha256(text.encode("utf-8")).hexdigest()   # in-memory (LF)
```

`write_text` uses text mode, which on newline-rewriting platforms translates
`\n` to `\r\n` on the way to disk (and turns the CSV's `\r\n` into `\r\r\n`).
`verify` recomputes each hash from the on-disk **bytes**
(`hashlib.sha256(path.read_bytes())`), so the on-disk (CRLF) hash disagreed
with the recorded (LF) hash. On POSIX, text mode does not translate, so the
two agreed and `files_ok` was true.

## Evidence (from SL's returned bundle, verified independently)

- Source archive SHA-256 matched the published value (`20174f58…`) — authentic
  release, not an operator error.
- `verify` on Windows: `content_hash_ok: true`, `files_ok: false`; the six
  non-empty text files reported `false`, the two empty `.jsonl` files `true`.
- Every failing file was **content-identical to the reference after newline
  normalization**; each normalized hash matched the manifest exactly.
- `metrics.csv` began `round,branch,metric,value\r\r\n` (bytes `0d 0d 0a`), the
  csv-writer `\r\n` plus a text-mode `\r` — a doubled carriage return.

## Fix (v0.3.1)

Writers now emit canonical UTF-8 bytes and hash exactly the bytes written:

```python
data = text.encode("utf-8")
path.write_bytes(data)                 # no newline translation, any platform
return hashlib.sha256(data).hexdigest()
```

The recorded hash therefore equals the on-disk bytes on every platform. On
POSIX the produced bytes are byte-identical to v0.3.0, so the frozen
`energy_baseline_v1_seed73` benchmark still verifies and reproduces
`dd73a350…` unchanged. Regression tests
(`tests/replay/test_newline_serialization.py`) and a native-Windows CI job
guard the invariant.

The verifier was **not** changed to normalize newlines before hashing: that
would weaken the exact byte-level integrity guarantee and hide real
serialization defects such as the `\r\r\n` CSV double-CR.

## Remediation status

`v0.3.1` Windows remediation rerun: **pending** (rerun the final v0.3.1 archive
on a Windows host and record a clean `files_ok: true` result).
