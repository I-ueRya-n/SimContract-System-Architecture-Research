"""Cross-platform byte-level bundle serialization (v0.3.1 newline fix).

The v0.3.0 writers used ``Path.write_text``, which on Windows translated
``\\n`` to ``\\r\\n`` (and the CSV's ``\\r\\n`` to ``\\r\\r\\n``) while the
recorded per-file hash was taken from the in-memory LF string. The recorded
hash then disagreed with the on-disk bytes and per-file verification
(``files_ok``) failed on Windows even though canonical content identity and
replay were unaffected.

These tests lock the invariant that the recorded per-file hash equals the
SHA-256 of the exact on-disk bytes, and that canonical evidence files are
written without platform newline translation. On POSIX they hold for the old
and new implementations alike (POSIX never translates); on Windows they fail
for the old implementation and pass for the fixed one, so they are the
regression guard exercised by the Windows CI job.
"""
from __future__ import annotations

from simcontract.evidence.hashing import (
    file_hash_of,
    write_json,
    write_jsonl,
    write_text,
)


def test_write_json_recorded_hash_equals_on_disk_bytes(tmp_path):
    p = tmp_path / "a.json"
    recorded = write_json(p, {"b": 1, "a": [1, 2, 3], "n": "x\ny"})
    assert recorded == file_hash_of(p)          # recorded == on-disk bytes
    assert b"\r" not in p.read_bytes()          # LF-only, no CR translation


def test_write_jsonl_recorded_hash_equals_on_disk_bytes(tmp_path):
    p = tmp_path / "a.jsonl"
    recorded = write_jsonl(p, [{"x": 1}, {"y": 2}])
    assert recorded == file_hash_of(p)
    assert b"\r" not in p.read_bytes()


def test_write_text_writes_exact_bytes(tmp_path):
    p = tmp_path / "a.txt"
    text = "line1\nline2\n"
    recorded = write_text(p, text)
    assert recorded == file_hash_of(p)
    assert p.read_bytes() == text.encode("utf-8")   # no translation at all


def test_csv_style_payload_has_no_doubled_carriage_return(tmp_path):
    # metrics.csv is produced by csv.writer (CRLF terminators) then written
    # verbatim; it must never gain a doubled CR (the Windows text-mode defect).
    p = tmp_path / "metrics.csv"
    csv_text = "round,branch,metric,value\r\n0,applied,x,1\r\n"
    recorded = write_text(p, csv_text)
    assert recorded == file_hash_of(p)
    assert b"\r\r\n" not in p.read_bytes()
    assert p.read_bytes() == csv_text.encode("utf-8")
