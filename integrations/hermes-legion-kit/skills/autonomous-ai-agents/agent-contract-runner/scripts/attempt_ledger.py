#!/usr/bin/env python3
"""Append immutable Aquila attempt telemetry rows to JSONL."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "objectiveId",
    "orderId",
    "attempt",
    "taskClass",
    "executor",
    "model",
    "reviewer",
    "risk",
    "status",
    "failureClass",
    "resultPath",
    "durationSeconds",
    "uncachedInput",
    "cachedInput",
    "output",
    "costUsd",
    "telemetryStatus",
)
USAGE_FIELDS = ("uncachedInput", "cachedInput", "output", "costUsd")


class LedgerError(ValueError):
    """Raised when a ledger row cannot be safely appended."""


def _nonempty_string(row: dict[str, Any], key: str) -> None:
    if not isinstance(row.get(key), str) or not row[key].strip():
        raise LedgerError(f"{key} must be a non-empty string")


def normalize_attempt_row(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a validated row, representing absent telemetry as unmeasured."""
    row = dict(candidate)
    for field in USAGE_FIELDS:
        if field not in row or row[field] is None:
            row[field] = "unmeasured"
    if "telemetryStatus" not in row or row["telemetryStatus"] is None:
        row["telemetryStatus"] = "unmeasured" if any(row[field] == "unmeasured" for field in USAGE_FIELDS) else "measured"
    missing = [field for field in REQUIRED_FIELDS if field not in row]
    if missing:
        raise LedgerError("attempt row missing fields: " + ", ".join(missing))
    for key in (
        "objectiveId",
        "orderId",
        "taskClass",
        "executor",
        "model",
        "reviewer",
        "risk",
        "status",
        "failureClass",
        "resultPath",
        "telemetryStatus",
    ):
        _nonempty_string(row, key)
    if isinstance(row["attempt"], bool) or not isinstance(row["attempt"], int) or row["attempt"] < 1:
        raise LedgerError("attempt must be a positive integer")
    duration = row["durationSeconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
        raise LedgerError("durationSeconds must be a non-negative number")
    for field in USAGE_FIELDS:
        value = row[field]
        if value == "unmeasured":
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise LedgerError(f"{field} must be a non-negative number or unmeasured")
    if any(row[field] == "unmeasured" for field in USAGE_FIELDS) and row["telemetryStatus"] != "unmeasured":
        raise LedgerError("telemetryStatus must be unmeasured when any usage field is absent")
    return row


def _read_existing_rows(fd: int, ledger_path: Path) -> list[dict[str, Any]]:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    content = b"".join(chunks)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"ledger line {line_number} is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LedgerError(f"ledger line {line_number} must be a JSON object")
        rows.append(parsed)
    return rows


def validate_attempt_lineage(existing: list[dict[str, Any]], row: dict[str, Any]) -> None:
    if any(item.get("orderId") == row["orderId"] for item in existing):
        raise LedgerError(f"orderId already exists in ledger: {row['orderId']}")
    if any(item.get("resultPath") == row["resultPath"] for item in existing):
        raise LedgerError(f"resultPath already exists in ledger: {row['resultPath']}")
    objective_rows = [item for item in existing if item.get("objectiveId") == row["objectiveId"]]
    if not objective_rows:
        if row["attempt"] != 1:
            raise LedgerError("a new objective must begin at attempt 1")
        return
    if any(item.get("taskClass") != row["taskClass"] for item in objective_rows):
        raise LedgerError("taskClass must remain stable within one objectiveId")
    attempts = [item.get("attempt") for item in objective_rows]
    if not all(isinstance(attempt, int) and not isinstance(attempt, bool) and attempt > 0 for attempt in attempts):
        raise LedgerError("existing ledger contains invalid attempt lineage")
    expected_attempt = max(attempts) + 1
    if row["attempt"] != expected_attempt:
        raise LedgerError(f"objective attempt must be {expected_attempt}")


def load_attempt_history(ledger_path: Path, *, missing_ok: bool = False) -> tuple[dict[str, Any], ...]:
    """Return one coherent read-only ledger snapshot under a shared lock."""
    try:
        fd = os.open(ledger_path, os.O_RDONLY)
    except FileNotFoundError:
        if missing_ok:
            return ()
        raise
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        parsed_rows = _read_existing_rows(fd, ledger_path)
        history: list[dict[str, Any]] = []
        for row_number, candidate in enumerate(parsed_rows, start=1):
            try:
                row = normalize_attempt_row(candidate)
                validate_attempt_lineage(history, row)
            except LedgerError as exc:
                raise LedgerError(f"ledger row {row_number} is invalid: {exc}") from exc
            history.append(row)
        return tuple(history)
    finally:
        os.close(fd)


def append_attempt(ledger_path: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    """Append one fsync'd JSONL row; never rewrite an existing ledger byte."""
    row = normalize_attempt_row(candidate)
    if not ledger_path.parent.is_dir():
        raise LedgerError(f"ledger parent does not exist: {ledger_path.parent}")
    encoded = (json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    fd = os.open(ledger_path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        validate_attempt_lineage(_read_existing_rows(fd, ledger_path), row)
        offset = 0
        while offset < len(encoded):
            written = os.write(fd, encoded[offset:])
            if written <= 0:
                raise LedgerError(f"could not append ledger row to {ledger_path}")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--row", required=True, type=Path, help="JSON object containing one attempt row")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        candidate = json.loads(args.row.read_text(encoding="utf-8"))
        if not isinstance(candidate, dict):
            raise LedgerError("row JSON must be an object")
        row = append_attempt(args.ledger, candidate)
    except (OSError, json.JSONDecodeError, LedgerError) as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1
    print(json.dumps({"status": "appended", "orderId": row["orderId"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
