#!/usr/bin/env python3
"""Create and verify controller receipts for the runner's direct dispatch path."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_artifact_namespace import ArtifactNamespaceError, require_control_path
from strict_json import StrictJSONError, strict_json_load_bytes


START_VERSION = "AQUILA_DIRECT_START_V1"
CLOSURE_VERSION = "AQUILA_DIRECT_CLOSURE_V1"
TERMINAL_VERSION = "AQUILA_DIRECT_ACCEPTANCE_V1"


class CustodyError(ValueError):
    """A direct attempt has unsafe paths or broken receipt bindings."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _create_only(path: Path, content: bytes) -> None:
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise CustodyError(f"receipt parent must be an existing directory: {path.parent}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise CustodyError(f"receipt path already exists: {path}") from exc
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        temporary_path.unlink(missing_ok=True)


def _encode(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = strict_json_load_bytes(path.read_bytes(), str(path))
    except (OSError, StrictJSONError) as exc:
        raise CustodyError(f"cannot read receipt {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CustodyError(f"receipt must be an object: {path}")
    return value


def start_direct_attempt(
    *, namespace: Path, order_path: Path, order: dict[str, Any], result_path: Path, argv: list[str]
) -> dict[str, Any]:
    """Write the start receipt before the external process can run."""
    try:
        run_id = secrets.token_hex(32)
        start_path = require_control_path(namespace / f"direct-start-{run_id}.json", namespace, "direct start receipt")
        closure_path = require_control_path(namespace / f"direct-closure-{run_id}.json", namespace, "direct closure receipt")
        terminal_path = require_control_path(namespace / f"direct-acceptance-{run_id}.json", namespace, "direct terminal receipt")
        require_control_path(result_path, namespace, "direct result")
    except ArtifactNamespaceError as exc:
        raise CustodyError(str(exc)) from exc
    for label, path in (("start", start_path), ("closure", closure_path), ("terminal", terminal_path), ("result", result_path)):
        if path.exists() or path.is_symlink():
            raise CustodyError(f"{label} path already exists before direct launch: {path}")
    try:
        order_bytes = order_path.read_bytes()
        observed_order = strict_json_load_bytes(order_bytes, str(order_path))
    except (OSError, StrictJSONError) as exc:
        raise CustodyError(f"cannot read order before direct launch: {exc}") from exc
    if observed_order != order:
        raise CustodyError("order bytes changed after validation and before direct launch")
    payload = {
        "version": START_VERSION,
        "orderId": order["orderId"],
        "executor": order["executor"],
        "orderPath": str(order_path.resolve(strict=False)),
        "orderSha256": _sha256(order_bytes),
        "resultPath": str(result_path),
        "commandSha256": _sha256(_encode({"argv": argv})),
        "runId": run_id,
        "startReceiptPath": str(start_path),
        "closurePath": str(closure_path),
        "terminalPath": str(terminal_path),
        "startedAt": _utc_now(),
    }
    encoded = _encode(payload)
    _create_only(start_path, encoded)
    return {"start": start_path, "closure": closure_path, "terminal": terminal_path, "startPayload": payload, "startSha256": _sha256(encoded)}


def close_direct_attempt(
    custody: dict[str, Any], *, result_path: Path, outcome: str, result_status: str | None,
    reason: str | None, checks: dict[str, Any], expected_result_sha256: str | None = None,
) -> dict[str, Any]:
    if outcome not in {"passed", "rejected"}:
        raise CustodyError("direct outcome must be passed or rejected")
    start = custody["startPayload"]
    start_path = custody["start"]
    if _sha256(start_path.read_bytes()) != custody["startSha256"]:
        raise CustodyError("direct start receipt changed after launch")
    result_sha256 = _sha256(result_path.read_bytes()) if result_path.is_file() and not result_path.is_symlink() else None
    if expected_result_sha256 is not None and result_sha256 != expected_result_sha256:
        outcome = "rejected"
        reason = "result bytes changed during controller verification"
    if outcome == "passed" and (result_sha256 is None or result_status != "done"):
        raise CustodyError("passed direct attempt requires an unchanged done result")
    closure = {
        "version": CLOSURE_VERSION,
        "scope": "post_execution_proof",
        "orderId": start["orderId"],
        "executor": start["executor"],
        "runId": start["runId"],
        "orderSha256": start["orderSha256"],
        "startReceiptSha256": custody["startSha256"],
        "startReceiptPath": str(start_path),
        "closurePath": str(custody["closure"]),
        "resultSha256": result_sha256,
        "resultPath": str(result_path),
        "resultStatus": result_status,
        "controllerVerification": outcome,
        "reason": reason,
        "observedChecks": checks,
        "closedAt": _utc_now(),
    }
    _create_only(custody["closure"], _encode(closure))
    verify_direct_attempt(custody["start"], custody["closure"], Path(start["orderPath"]), result_path)
    return closure


def finalize_direct_attempt(
    custody: dict[str, Any], *, order_path: Path, result_path: Path, status: str, reason: str | None
) -> dict[str, Any]:
    """Record the final controller outcome after any loop-state transition."""
    if status not in {"passed", "rejected"}:
        raise CustodyError("direct terminal status must be passed or rejected")
    closure = verify_direct_attempt(custody["start"], custody["closure"], order_path, result_path)
    if status == "passed" and closure["controllerVerification"] != "passed":
        raise CustodyError("cannot accept a direct attempt with rejected proof")
    terminal = {
        "version": TERMINAL_VERSION,
        "orderId": closure["orderId"],
        "executor": closure["executor"],
        "runId": closure["runId"],
        "orderSha256": closure["orderSha256"],
        "startReceiptSha256": custody["startSha256"],
        "closureSha256": _sha256(custody["closure"].read_bytes()),
        "resultSha256": closure["resultSha256"],
        "status": status,
        "reason": reason,
        "completedAt": _utc_now(),
    }
    _create_only(custody["terminal"], _encode(terminal))
    verify_direct_terminal(custody["start"], custody["closure"], custody["terminal"], order_path, result_path)
    return terminal


def verify_direct_terminal(
    start_path: Path, closure_path: Path, terminal_path: Path, order_path: Path, result_path: Path
) -> dict[str, Any]:
    closure = verify_direct_attempt(start_path, closure_path, order_path, result_path)
    start = _load(start_path)
    terminal = _load(terminal_path)
    if terminal.get("version") != TERMINAL_VERSION or start.get("terminalPath") != str(terminal_path):
        raise CustodyError("direct terminal version or path mismatch")
    if any(terminal.get(key) != closure.get(key) for key in ("orderId", "executor", "runId", "orderSha256", "resultSha256")):
        raise CustodyError("direct terminal identity mismatch")
    if terminal.get("startReceiptSha256") != _sha256(start_path.read_bytes()) or terminal.get("closureSha256") != _sha256(closure_path.read_bytes()):
        raise CustodyError("direct terminal receipt digest mismatch")
    if terminal.get("status") not in {"passed", "rejected"}:
        raise CustodyError("direct terminal status is invalid")
    if terminal["status"] == "passed" and closure["controllerVerification"] != "passed":
        raise CustodyError("direct terminal cannot pass rejected proof")
    return terminal


def verify_direct_attempt(start_path: Path, closure_path: Path, order_path: Path, result_path: Path) -> dict[str, Any]:
    """Recompute live order, result, and receipt digests for one direct attempt."""
    start = _load(start_path)
    closure = _load(closure_path)
    if start.get("version") != START_VERSION or closure.get("version") != CLOSURE_VERSION:
        raise CustodyError("direct receipt version mismatch")
    if any(start.get(key) != closure.get(key) for key in ("orderId", "executor", "runId", "orderSha256")):
        raise CustodyError("direct receipt identity mismatch")
    if closure.get("startReceiptSha256") != _sha256(start_path.read_bytes()):
        raise CustodyError("direct start receipt digest mismatch")
    if start.get("startReceiptPath") != str(start_path) or closure.get("startReceiptPath") != str(start_path):
        raise CustodyError("direct start receipt path mismatch")
    if start.get("closurePath") != str(closure_path) or closure.get("closurePath") != str(closure_path):
        raise CustodyError("direct closure receipt path mismatch")
    if start.get("orderPath") != str(order_path.resolve(strict=False)) or start.get("orderSha256") != _sha256(order_path.read_bytes()):
        raise CustodyError("direct order digest mismatch")
    if start.get("resultPath") != str(result_path) or closure.get("resultPath") != str(result_path):
        raise CustodyError("direct result path mismatch")
    observed_result_sha256 = _sha256(result_path.read_bytes()) if result_path.is_file() and not result_path.is_symlink() else None
    if closure.get("resultSha256") != observed_result_sha256:
        raise CustodyError("direct result digest mismatch")
    if closure.get("controllerVerification") == "passed" and observed_result_sha256 is None:
        raise CustodyError("passed direct attempt is missing a result")
    return closure
