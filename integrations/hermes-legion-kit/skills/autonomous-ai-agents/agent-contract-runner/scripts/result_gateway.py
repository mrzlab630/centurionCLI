#!/usr/bin/env python3
"""Launch one Codex or Claude attempt and finalize its controller-owned result."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_contract_runner import PathPolicy, RunnerError, validate_order
from agent_result_builder import BuilderError, _load_schema, build_result, resolve_schema_path, validate_candidate
from review_ladder import RoutingError, validate_order_routing
from strict_json import StrictJSONError, strict_json_load_bytes


START_RECEIPT_VERSION = "RESULT_GATEWAY_START_V1"
CLOSURE_VERSION = "RESULT_GATEWAY_CLOSURE_V2"
EVENT_NAMESPACE = "aquila.result_gateway.v1"
RESULT_VERSION = "AGENT_RESULT_JSON_V1"
SUPPORTED_EXECUTORS = {"codex", "claude"}


class GatewayError(Exception):
    """Raised when the controller cannot safely close an executor attempt."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise GatewayError(f"{label} must be a non-empty timestamp string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise GatewayError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise GatewayError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def load_order(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        content = path.read_bytes()
        value = strict_json_load_bytes(content, "order")
    except (OSError, StrictJSONError) as exc:
        raise GatewayError(f"could not load order: {exc}") from exc
    if not isinstance(value, dict):
        raise GatewayError("order must be a JSON object")
    for key in ("orderId", "executor"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise GatewayError(f"order.{key} must be a non-empty string")
    if value.get("orderVersion") != "AGENT_ORDER_JSON_V1":
        raise GatewayError("order.orderVersion must be AGENT_ORDER_JSON_V1")
    if value["executor"] not in SUPPORTED_EXECUTORS:
        raise GatewayError("result gateway supports only codex and claude executors")
    parse_timestamp(value.get("createdAt"), "order.createdAt")
    return value, content


def routing_binding(order: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Return the exact post-validation route and its deterministic digest."""
    try:
        routing = validate_order_routing(order)
    except RoutingError as exc:
        raise GatewayError(f"routing binding failed after order validation: {exc}") from exc
    if routing is None:
        return None, None
    canonical = json.dumps(routing, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return routing, sha256_bytes(canonical)


def atomic_create(path: Path, content: bytes, mode: int = 0o600) -> None:
    if not path.parent.is_dir():
        raise GatewayError(f"parent directory does not exist: {path.parent}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, mode)
        offset = 0
        while offset < len(content):
            written = os.write(fd, content[offset:])
            if written < 1:
                raise OSError("atomic write made no progress")
            offset += written
        os.fsync(fd)
        os.close(fd)
        fd = -1
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise GatewayError(f"path collision: {path}") from exc
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        temporary_path.unlink(missing_ok=True)


def append_event(events_path: Path | None, event: str, **payload: Any) -> None:
    if events_path is None:
        return
    record = {
        "ts": utc_now(),
        "eventNamespace": EVENT_NAMESPACE,
        "event": f"{EVENT_NAMESPACE}.{event}",
        **payload,
    }
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        fd = os.open(events_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            offset = 0
            while offset < len(encoded):
                written = os.write(fd, encoded[offset:])
                if written < 1:
                    raise OSError("event write made no progress")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise GatewayError(f"could not append controller event at {events_path}: {exc}") from exc


def append_event_best_effort(events_path: Path | None, event: str, **payload: Any) -> str | None:
    try:
        append_event(events_path, event, **payload)
    except GatewayError as exc:
        print(f"warning: {exc}", file=sys.stderr)
        return str(exc)
    return None


def probe_writable_directory(path: Path, label: str) -> None:
    if not path.exists():
        raise GatewayError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise GatewayError(f"{label} is not a directory: {path}")
    fd = -1
    probe_path: Path | None = None
    link_path: Path | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=".result-gateway-probe.", dir=path)
        probe_path = Path(name)
        written = os.write(fd, b"probe")
        if written != 5:
            raise OSError("writability probe made incomplete progress")
        os.fsync(fd)
        os.close(fd)
        fd = -1
        link_path = path / f".{probe_path.name}.{secrets.token_hex(8)}.link"
        os.link(probe_path, link_path)
        directory_fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise GatewayError(f"{label} is not writable with create-only receipt semantics: {path}: {exc}") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if link_path is not None:
            link_path.unlink(missing_ok=True)
        if probe_path is not None:
            probe_path.unlink(missing_ok=True)


def preserve_bytes(content: bytes, evidence_dir: Path, label: str) -> Path:
    digest = sha256_bytes(content)
    path = evidence_dir / f"{digest}.{label}.bin"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    try:
        atomic_create(path, content)
    except GatewayError as exc:
        if "path collision" not in str(exc):
            raise
        try:
            existing = path.read_bytes()
        except OSError as read_exc:
            raise GatewayError(f"could not verify existing evidence at {path}: {read_exc}") from read_exc
        if sha256_bytes(existing) != digest:
            raise GatewayError(f"evidence hash collision at {path}") from exc
    return path


def write_stream(path: Path | None, content: bytes, evidence_dir: Path, label: str) -> tuple[dict[str, Any], str | None]:
    digest = sha256_bytes(content)
    record: dict[str, Any] = {
        "requestedPath": str(path) if path is not None else None,
        "path": None,
        "sha256": digest,
        "bytes": len(content),
        "captured": False,
    }
    if path is None:
        fallback = preserve_bytes(content, evidence_dir, label)
        record.update({"path": str(fallback), "captured": True, "fallback": True})
        return record, None
    try:
        atomic_create(path, content)
        record.update({"path": str(path), "captured": True, "fallback": False})
        return record, None
    except (GatewayError, OSError) as exc:
        try:
            fallback = preserve_bytes(content, evidence_dir, label)
        except (GatewayError, OSError) as fallback_exc:
            message = f"{label} capture failed at {path}: {exc}; fallback failed at {evidence_dir}: {fallback_exc}"
            record.update({"fallback": True, "error": message})
            return record, message
        record.update({"path": str(fallback), "captured": True, "fallback": True, "error": str(exc)})
        return record, f"{label} capture failed at {path}: {exc}"


def parse_order_paths(
    order: dict[str, Any],
    policy: PathPolicy,
    candidate_arg: Path,
    start_receipt_arg: Path,
    closure_arg: Path,
    evidence_arg: Path,
    events_arg: Path | None,
) -> tuple[PathPolicy, Path, Path, Path, Path, Path, Path | None, Path | None, Path | None]:
    launch = order.get("launch")
    output = order.get("outputContract")
    if not isinstance(launch, dict) or not isinstance(output, dict):
        raise GatewayError("order launch and outputContract must be objects")
    if output.get("resultVersion") != RESULT_VERSION:
        raise GatewayError(f"outputContract.resultVersion must be {RESULT_VERSION}")
    result_value = output.get("resultPath")
    launch_result_value = launch.get("resultJsonPath")
    if not isinstance(result_value, str) or not isinstance(launch_result_value, str):
        raise GatewayError("result paths must be strings")
    for key in ("stdoutPath", "stderrPath"):
        if launch.get(key) is not None and not isinstance(launch[key], str):
            raise GatewayError(f"launch.{key} must be a string when provided")
    try:
        result_path = policy.order_path(result_value, "outputContract.resultPath")
        launch_result_path = policy.order_path(launch_result_value, "launch.resultJsonPath")
        candidate_path = policy.cli_path(candidate_arg, "CLI --candidate")
        start_receipt_path = policy.cli_path(start_receipt_arg, "CLI --start-receipt")
        closure_path = policy.cli_path(closure_arg, "CLI --closure")
        evidence_dir = policy.cli_path(evidence_arg, "CLI --evidence-dir")
        events_path = policy.cli_path(events_arg, "CLI --events") if events_arg is not None else None
        stdout_path = policy.order_path(launch["stdoutPath"], "launch.stdoutPath") if launch.get("stdoutPath") else None
        stderr_path = policy.order_path(launch["stderrPath"], "launch.stderrPath") if launch.get("stderrPath") else None
    except RunnerError as exc:
        raise GatewayError(str(exc)) from exc
    if result_path != launch_result_path:
        raise GatewayError("launch.resultJsonPath and outputContract.resultPath must resolve to the same path")
    distinct = [result_path, candidate_path, start_receipt_path, closure_path, evidence_dir]
    distinct.extend(path for path in (stdout_path, stderr_path, events_path) if path is not None)
    if len({str(path) for path in distinct}) != len(distinct):
        raise GatewayError("result, candidate, start receipt, closure, evidence, stdout, stderr, and events paths must be distinct")
    file_paths = [result_path, candidate_path, start_receipt_path, closure_path]
    file_paths.extend(path for path in (stdout_path, stderr_path, events_path) if path is not None)
    if any(evidence_dir in path.parents for path in file_paths):
        raise GatewayError("evidence directory must not contain result, candidate, receipt, stream, or event paths")
    return policy, result_path, candidate_path, start_receipt_path, closure_path, evidence_dir, events_path, stdout_path, stderr_path


def preflight_outputs(
    result_path: Path,
    candidate_path: Path,
    start_receipt_path: Path,
    closure_path: Path,
    evidence_dir: Path,
    events_path: Path | None,
    stdout_path: Path | None,
    stderr_path: Path | None,
) -> None:
    create_only = {
        "result": result_path,
        "candidate": candidate_path,
        "start receipt": start_receipt_path,
        "closure": closure_path,
        "stdout": stdout_path,
        "stderr": stderr_path,
    }
    for label, path in create_only.items():
        if path is not None and (path.exists() or path.is_symlink()):
            raise GatewayError(f"{label} path already exists before launch: {path}")
    if events_path is not None and events_path.exists() and not events_path.is_file():
        raise GatewayError(f"events path is not a regular file: {events_path}")
    if events_path is not None and events_path.is_symlink():
        raise GatewayError(f"events path must not be a symlink: {events_path}")
    directories: dict[Path, list[str]] = {evidence_dir: ["evidence directory"]}
    for label, path in {
        **create_only,
        "events": events_path,
    }.items():
        if path is not None:
            directories.setdefault(path.parent, []).append(f"{label} parent")
    for directory, labels in directories.items():
        probe_writable_directory(directory, ", ".join(labels))


def plan_command(order: dict[str, Any]) -> list[str]:
    launch = order.get("launch")
    if not isinstance(launch, dict) or not isinstance(launch.get("command"), str):
        raise GatewayError("order.launch.command must be a string")
    timeout = launch.get("timeoutSeconds")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1:
        raise GatewayError("order.launch.timeoutSeconds must be a positive integer")
    try:
        argv = shlex.split(launch["command"])
    except ValueError as exc:
        raise GatewayError(f"launch.command cannot be parsed safely: {exc}") from exc
    if not argv:
        raise GatewayError("launch.command must not be empty")
    if Path(argv[0]).name != order["executor"]:
        raise GatewayError(f"executor is {order['executor']} but launch.command starts with {Path(argv[0]).name}")
    return argv


def run_child(argv: list[str], cwd: Path, timeout: int, grace_seconds: float) -> dict[str, Any]:
    started_at = utc_now()
    monotonic_started = time.monotonic()
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return {
            "childStarted": False,
            "startedAt": started_at,
            "closedAt": utc_now(),
            "durationMs": int((time.monotonic() - monotonic_started) * 1000),
            "exitCode": None,
            "timedOut": False,
            "drainTimedOut": False,
            "terminationSignal": None,
            "stdout": b"",
            "stderr": b"",
            "error": f"executor command failed to start: {exc}",
        }

    timed_out = False
    drain_timed_out = False
    termination_signal = None
    capture_error = None
    stdout = b""
    stderr = b""

    def signal_group(sig: signal.Signals) -> None:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    def close_pipes() -> None:
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def bounded_wait() -> None:
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                pass

    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as timeout_exc:
        timed_out = True
        termination_signal = "SIGTERM"
        signal_group(signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=grace_seconds)
        except subprocess.TimeoutExpired as term_exc:
            termination_signal = "SIGKILL"
            signal_group(signal.SIGKILL)
            try:
                stdout, stderr = process.communicate(timeout=grace_seconds)
            except subprocess.TimeoutExpired as kill_exc:
                drain_timed_out = True
                stdout = kill_exc.output or term_exc.output or timeout_exc.output or b""
                stderr = kill_exc.stderr or term_exc.stderr or timeout_exc.stderr or b""
                close_pipes()
                bounded_wait()
    except OSError as exc:
        capture_error = f"executor stream capture failed: {exc}"
        termination_signal = "SIGKILL"
        signal_group(signal.SIGKILL)
        close_pipes()
        bounded_wait()
    errors = []
    if timed_out:
        errors.append(f"launcher timed out after {timeout}s")
    if drain_timed_out:
        errors.append(f"post-SIGKILL pipe drain exceeded {grace_seconds}s")
    if capture_error:
        errors.append(capture_error)
    return {
        "childStarted": True,
        "startedAt": started_at,
        "closedAt": utc_now(),
        "durationMs": int((time.monotonic() - monotonic_started) * 1000),
        "exitCode": process.returncode,
        "timedOut": timed_out,
        "drainTimedOut": drain_timed_out,
        "terminationSignal": termination_signal,
        "stdout": stdout or b"",
        "stderr": stderr or b"",
        "error": "; ".join(errors) if errors else None,
    }


def candidate_record(path: Path) -> tuple[dict[str, Any], bytes | None]:
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return {"path": str(path), "exists": False, "sha256": sha256_bytes(b""), "bytes": 0}, None
    except OSError as exc:
        return {"path": str(path), "exists": False, "sha256": None, "bytes": None, "error": str(exc)}, None
    return {"path": str(path), "exists": True, "sha256": sha256_bytes(content), "bytes": len(content)}, content


def parse_strict_candidate(content: bytes, label: str) -> tuple[Any, list[str]]:
    try:
        return strict_json_load_bytes(content, label), []
    except StrictJSONError as exc:
        return None, [str(exc)]


def validate_stdout_candidate(
    content: bytes,
    order: dict[str, Any],
    schema_path: Path | None,
) -> list[str]:
    candidate, parse_errors = parse_strict_candidate(content, "stdout candidate")
    if parse_errors:
        return parse_errors
    try:
        _, validator = _load_schema(resolve_schema_path(schema_path))
    except BuilderError as exc:
        raise GatewayError(str(exc)) from exc
    return [f"stdout candidate validation failed: {error}" for error in validate_candidate(candidate, order, validator)]


def synthetic_failed_result(
    order: dict[str, Any],
    candidate: dict[str, Any],
    stream_records: list[tuple[str, dict[str, Any]]],
    errors: list[str],
    evidence_path: Path | None = None,
) -> dict[str, Any]:
    if evidence_path is not None:
        files_changed = [{"path": str(evidence_path), "action": "added"}]
        artifacts = [
            {
                "path": str(evidence_path),
                "exists": True,
                "type": "malformed-result-evidence",
                "note": f"Original candidate bytes preserved as sha256:{evidence_path.name.split('.', 1)[0]}",
            }
        ]
    else:
        files_changed = []
        artifacts = [
            {
                "path": candidate["path"],
                "exists": bool(candidate.get("exists")),
                "type": "raw-candidate",
                "note": f"Controller-observed candidate sha256:{candidate.get('sha256') or 'unavailable'}",
            }
        ]
    return {
        "resultVersion": RESULT_VERSION,
        "orderId": order["orderId"],
        "executor": order["executor"],
        "status": "failed",
        "summary": "Result Gateway closed the executor attempt without an acceptable candidate result.",
        "filesChanged": files_changed,
        "artifacts": artifacts,
        "proof": [
            {
                "command": "result_gateway controller closure and candidate gate",
                "cwd": order["workspace"]["repoPath"],
                "status": "fail",
                "exitCode": 1,
                "summary": "; ".join(errors),
            }
        ],
        "selfReview": {"performed": True, "findings": errors, "fixesApplied": []},
        "scopeDeviations": [],
        "forbiddenPatternHits": [],
        "remainingRisks": [],
        "questions": [],
        "errors": errors,
        "stdoutSummary": next((f"capturedBytes={record['bytes']}" for label, record in stream_records if label == "stdout"), ""),
        "stderrSummary": next((f"capturedBytes={record['bytes']}" for label, record in stream_records if label == "stderr"), ""),
    }


def finalize_synthetic(
    order_path: Path,
    order: dict[str, Any],
    result_path: Path,
    evidence_dir: Path,
    schema_path: Path | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not result_path.parent.is_dir():
        raise GatewayError(f"result parent does not exist: {result_path.parent}")
    fd, name = tempfile.mkstemp(prefix=".gateway-failure.", suffix=".json", dir=result_path.parent)
    candidate_path = Path(name)
    try:
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        os.fchmod(fd, 0o600)
        offset = 0
        while offset < len(encoded):
            offset += os.write(fd, encoded[offset:])
        os.fsync(fd)
        os.close(fd)
        fd = -1
        return build_result(order_path, candidate_path, result_path, evidence_dir, schema_path)
    except (BuilderError, OSError) as exc:
        raise GatewayError(str(exc)) from exc
    finally:
        if fd >= 0:
            os.close(fd)
        candidate_path.unlink(missing_ok=True)


def finalize_candidate(
    order_path: Path,
    candidate_path: Path,
    result_path: Path,
    evidence_dir: Path,
    schema_path: Path | None,
) -> dict[str, Any]:
    try:
        return build_result(order_path, candidate_path, result_path, evidence_dir, schema_path)
    except (BuilderError, OSError) as exc:
        raise GatewayError(str(exc)) from exc


def start_receipt_payload(
    order_path: Path,
    order: dict[str, Any],
    order_sha256: str,
    run_id: str,
    started_at: str,
    result_path: Path,
    candidate_path: Path,
    candidate_source: str,
    start_receipt_path: Path,
    closure_path: Path,
    evidence_dir: Path,
    stdout_path: Path | None,
    stderr_path: Path | None,
    routing: dict[str, Any] | None,
    routing_sha256: str | None,
) -> dict[str, Any]:
    return {
        "startReceiptVersion": START_RECEIPT_VERSION,
        "eventNamespace": EVENT_NAMESPACE,
        "state": "started",
        "orderId": order["orderId"],
        "executor": order["executor"],
        "orderPath": str(order_path.resolve(strict=False)),
        "orderSha256": order_sha256,
        "runId": run_id,
        "startedAt": started_at,
        "resultPath": str(result_path),
        "candidatePath": str(candidate_path),
        "candidateSource": candidate_source,
        "startReceiptPath": str(start_receipt_path),
        "closurePath": str(closure_path),
        "evidenceDirectory": str(evidence_dir),
        "stdoutPath": str(stdout_path) if stdout_path is not None else None,
        "stderrPath": str(stderr_path) if stderr_path is not None else None,
        "routing": routing,
        "routingSha256": routing_sha256,
    }


def closure_payload(
    order_path: Path,
    order: dict[str, Any],
    order_sha256: str,
    start_receipt_path: Path,
    start_receipt_sha256: str,
    run_id: str,
    gateway_started_at: str,
    argv: list[str],
    child: dict[str, Any],
    result_path: Path,
    result: dict[str, Any],
    candidate: dict[str, Any],
    stdout_record: dict[str, Any],
    stderr_record: dict[str, Any],
    errors: list[str],
    routing: dict[str, Any] | None,
    routing_sha256: str | None,
) -> dict[str, Any]:
    result_bytes = result_path.read_bytes()
    command_fingerprint = sha256_bytes("\0".join(argv).encode("utf-8")) if argv else None
    return {
        "closureVersion": CLOSURE_VERSION,
        "eventNamespace": EVENT_NAMESPACE,
        "orderId": order["orderId"],
        "executor": order["executor"],
        "orderPath": str(order_path.resolve(strict=False)),
        "orderSha256": order_sha256,
        "runId": run_id,
        "startReceiptPath": str(start_receipt_path),
        "startReceiptSha256": start_receipt_sha256,
        "state": "closed",
        "launcherClosed": True,
        "canonicalFinalized": True,
        "childStarted": child["childStarted"],
        "startedAt": gateway_started_at,
        "childStartedAt": child["startedAt"],
        "closedAt": child["closedAt"],
        "durationMs": child["durationMs"],
        "exitCode": child["exitCode"],
        "timedOut": child["timedOut"],
        "drainTimedOut": child["drainTimedOut"],
        "terminationSignal": child["terminationSignal"],
        "command": {"argv0": Path(argv[0]).name if argv else None, "argc": len(argv), "sha256": command_fingerprint},
        "candidate": candidate,
        "stdout": stdout_record,
        "stderr": stderr_record,
        "canonicalResultPath": str(result_path),
        "canonicalResultSha256": sha256_bytes(result_bytes),
        "canonicalStatus": result["status"],
        "controllerErrors": errors,
        "routing": routing,
        "routingSha256": routing_sha256,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--candidate-source", required=True, choices=("file", "stdout"))
    parser.add_argument("--start-receipt", required=True, type=Path)
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--termination-grace-seconds", type=float, default=3.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    order: dict[str, Any] | None = None
    result_path: Path | None = None
    start_receipt_path: Path | None = None
    closure_path: Path | None = None
    events_path: Path | None = None
    child_started = False
    try:
        if not math.isfinite(args.termination_grace_seconds) or args.termination_grace_seconds <= 0:
            raise GatewayError("--termination-grace-seconds must be a finite positive number")
        order, order_bytes = load_order(args.order)
        try:
            _, policy = validate_order(order)
        except RunnerError as exc:
            raise GatewayError(f"order validation failed: {exc}") from exc
        routing, routing_sha256 = routing_binding(order)
        if args.candidate_source == "stdout" and order["executor"] != "claude":
            raise GatewayError("--candidate-source stdout is supported only for claude executors")
        (
            policy,
            result_path,
            candidate_path,
            start_receipt_path,
            closure_path,
            evidence_dir,
            events_path,
            stdout_path,
            stderr_path,
        ) = parse_order_paths(order, policy, args.candidate, args.start_receipt, args.closure, args.evidence_dir, args.events)
        argv = plan_command(order)
        try:
            _load_schema(resolve_schema_path(args.schema))
        except BuilderError as exc:
            raise GatewayError(str(exc)) from exc
        preflight_outputs(
            result_path,
            candidate_path,
            start_receipt_path,
            closure_path,
            evidence_dir,
            events_path,
            stdout_path,
            stderr_path,
        )
        run_id = secrets.token_hex(32)
        gateway_started_at = utc_now()
        order_sha256 = sha256_bytes(order_bytes)
        start_receipt = start_receipt_payload(
            args.order,
            order,
            order_sha256,
            run_id,
            gateway_started_at,
            result_path,
            candidate_path,
            args.candidate_source,
            start_receipt_path,
            closure_path,
            evidence_dir,
            stdout_path,
            stderr_path,
            routing,
            routing_sha256,
        )
        start_receipt_bytes = (json.dumps(start_receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        atomic_create(start_receipt_path, start_receipt_bytes)
        start_receipt_sha256 = sha256_bytes(start_receipt_bytes)
        append_event_best_effort(
            events_path,
            "launch_started",
            orderId=order["orderId"],
            executor=order["executor"],
            candidateSource=args.candidate_source,
            argv0=Path(argv[0]).name,
            argc=len(argv),
            runId=run_id,
            orderSha256=order_sha256,
            startReceiptSha256=start_receipt_sha256,
        )
        child = run_child(argv, policy.repo_path, order["launch"]["timeoutSeconds"], args.termination_grace_seconds)
        child_started = child["childStarted"]
        append_event_best_effort(
            events_path,
            "launch_closed",
            orderId=order["orderId"],
            executor=order["executor"],
            childStarted=child["childStarted"],
            exitCode=child["exitCode"],
            timedOut=child["timedOut"],
            drainTimedOut=child["drainTimedOut"],
            runId=run_id,
        )
        stdout_record, stdout_error = write_stream(stdout_path, child["stdout"], evidence_dir, "stdout")
        stderr_record, stderr_error = write_stream(stderr_path, child["stderr"], evidence_dir, "stderr")
        controller_errors = [error for error in (child.get("error"), stdout_error, stderr_error) if error]
        if args.candidate_source == "stdout" and not controller_errors:
            stdout_errors = validate_stdout_candidate(child["stdout"], order, args.schema)
            if stdout_errors:
                controller_errors.extend(stdout_errors)
            else:
                try:
                    atomic_create(candidate_path, child["stdout"])
                except (GatewayError, OSError) as exc:
                    controller_errors.append(f"stdout candidate materialization failed at {candidate_path}: {exc}")
        candidate, candidate_bytes = candidate_record(candidate_path)
        candidate["source"] = args.candidate_source
        strict_evidence_path = None
        if candidate.get("error"):
            controller_errors.append(f"candidate result could not be read at {candidate_path}: {candidate['error']}")
        if not candidate.get("exists"):
            controller_errors.append(f"{args.candidate_source} candidate result missing after launcher closure: {candidate_path}")
        if args.candidate_source == "file" and candidate_bytes is not None:
            _, file_parse_errors = parse_strict_candidate(candidate_bytes, "file candidate")
            if file_parse_errors:
                strict_evidence_path = preserve_bytes(candidate_bytes, evidence_dir, "candidate-result")
                controller_errors.extend(file_parse_errors)
        if controller_errors:
            failed_payload = synthetic_failed_result(
                order,
                candidate,
                [("stdout", stdout_record), ("stderr", stderr_record)],
                controller_errors,
                strict_evidence_path,
            )
            result = finalize_synthetic(args.order, order, result_path, evidence_dir, args.schema, failed_payload)
        else:
            result = finalize_candidate(args.order, candidate_path, result_path, evidence_dir, args.schema)
        closure = closure_payload(
            args.order,
            order,
            order_sha256,
            start_receipt_path,
            start_receipt_sha256,
            run_id,
            gateway_started_at,
            argv,
            child,
            result_path,
            result,
            candidate,
            stdout_record,
            stderr_record,
            controller_errors,
            routing,
            routing_sha256,
        )
        atomic_create(closure_path, (json.dumps(closure, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        append_event_best_effort(
            events_path,
            "canonical_finalized",
            orderId=order["orderId"],
            executor=order["executor"],
            resultStatus=result["status"],
            resultSha256=closure["canonicalResultSha256"],
            closurePath=str(closure_path),
            runId=run_id,
            startReceiptSha256=start_receipt_sha256,
        )
        print(json.dumps({"status": "closed", "resultStatus": result["status"], "path": str(result_path)}, sort_keys=True))
        if child["timedOut"]:
            return 124
        if controller_errors or child["exitCode"] not in (0, None):
            return 1
        return 0 if result["status"] == "done" else 2
    except (GatewayError, OSError) as exc:
        try:
            append_event(
                events_path,
                "controller_error",
                orderId=order.get("orderId") if order else None,
                executor=order.get("executor") if order else None,
                childStarted=child_started,
                error=str(exc),
            )
        except GatewayError:
            pass
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
