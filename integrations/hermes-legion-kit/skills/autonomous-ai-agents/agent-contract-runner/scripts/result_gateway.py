#!/usr/bin/env python3
"""Launch one Codex or Claude attempt and finalize its controller-owned result."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
import os
import secrets
import selectors
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agent_contract_runner import (
    LoopStateLock,
    LoopStateSnapshot,
    PathPolicy,
    RunnerError,
    append_event as append_runner_event,
    block_loop_state_after_dispatch_failure,
    loop_contract,
    loop_lock_path,
    prepare_loop_dispatch,
    run_verification_gate,
    update_loop_state_after_result,
    validate_codex_launch,
    validate_loop_order,
    validate_order,
    reserve_mission_dispatch,
    verify_workspace_diff,
    workspace_snapshot,
    _mission_file_ref,
    _mission_process_activity,
    _mission_process_identity,
    _mission_time,
    mission_stop_deadline,
    mission_snapshot,
    pending_review_launches,
    MissionReservation,
    run_proof_commands,
    verify_required_proof_checks,
    verify_result,
    check_expected_artifacts,
    verify_required_artifact_checks,
)
from agent_artifact_namespace import ArtifactNamespaceError, require_control_path
from artifact_lineage import LineageError, finalize_lineage, preflight_lineage
from agent_result_builder import BuilderError, ProtocolFailure, _load_schema, _schema_errors, build_result, create_only_finalize, record_protocol_failure, resolve_schema_path, validate_candidate
from order_preflight import PreflightError, _option_values, controller_context, executor_environment, load_tunnel_order, validate_tunnel_launch, validate_claude_proxy_environment
from review_ladder import RoutingError, validate_order_routing
from response_envelope import MAX_CANDIDATE_BYTES, MAX_FRAME_BYTES, MAX_STDERR_BYTES, MAX_STDOUT_BYTES, ResponseEnvelopeError, parse_response_bytes, read_bounded_file, response_state_errors
from accepted_inputs import AcceptedInputError, verify_input_results, verify_manual_report_review
from strict_json import StrictJSONError, strict_json_load_bytes


START_RECEIPT_VERSION = "RESULT_GATEWAY_START_V1"
CLOSURE_VERSION = "RESULT_GATEWAY_CLOSURE_V2"
EVENT_NAMESPACE = "aquila.result_gateway.v1"
RESULT_VERSION = "AGENT_RESULT_JSON_V1"
SUPPORTED_EXECUTORS = {"codex", "claude"}


class GatewayError(Exception):
    """Raised when the controller cannot safely close an executor attempt."""


class ReportRetryable(GatewayError):
    """A stopped, isolated report failed validation; the product remains saved."""


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
        value, content = load_tunnel_order(path)
    except (OSError, StrictJSONError, PreflightError, ResponseEnvelopeError) as exc:
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
        result_path = policy.control_path(result_value, "outputContract.resultPath")
        launch_result_path = policy.control_path(launch_result_value, "launch.resultJsonPath")
        candidate_path = policy.control_cli_path(candidate_arg, "CLI --candidate")
        start_receipt_path = policy.control_cli_path(start_receipt_arg, "CLI --start-receipt")
        closure_path = policy.control_cli_path(closure_arg, "CLI --closure")
        evidence_dir = policy.control_cli_path(evidence_arg, "CLI --evidence-dir")
        events_path = policy.control_cli_path(events_arg, "CLI --events") if events_arg is not None else (
            policy.control_path(str(policy.control_namespace / "events.jsonl"), "monitored process events")
            if launch.get("timeoutSeconds") is None and controller_context(order) is not None else None)
        stdout_path = policy.control_path(launch["stdoutPath"], "launch.stdoutPath") if launch.get("stdoutPath") else None
        stderr_path = policy.control_path(launch["stderrPath"], "launch.stderrPath") if launch.get("stderrPath") else None
    except (RunnerError, ArtifactNamespaceError) as exc:
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
    acceptance_path: Path | None = None,
    proof_path: Path | None = None,
) -> None:
    create_only = {
        "result": result_path,
        "candidate": candidate_path,
        "start receipt": start_receipt_path,
        "closure": closure_path,
        "controller acceptance": acceptance_path,
        "controller proof": proof_path,
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
    if "timeoutSeconds" not in launch or (timeout is None and controller_context(order) is None) or (timeout is not None and (type(timeout) is not int or timeout < 1)):
        raise GatewayError("order.launch.timeoutSeconds must be a positive integer or explicit null for policy 3.0 monitored execution")
    try:
        argv = shlex.split(launch["command"])
    except ValueError as exc:
        raise GatewayError(f"launch.command cannot be parsed safely: {exc}") from exc
    if not argv:
        raise GatewayError("launch.command must not be empty")
    if Path(argv[0]).name != order["executor"]:
        raise GatewayError(f"executor is {order['executor']} but launch.command starts with {Path(argv[0]).name}")
    return argv


# Three identical Read results warrant a warning, not process cancellation.
CLAUDE_NO_PROGRESS_LIMIT = 3
CHILD_OBSERVATION_SECONDS = 30.0


def _claude_tool_event_state() -> dict[str, Any]:
    return {"pending": {}, "signature": None, "noProgress": 0}


def _observe_claude_tool_event(event: Any, state: dict[str, Any]) -> str | None:
    if not isinstance(event, dict):
        return None
    message = event.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    blocks = content if isinstance(content, list) else []
    for block in blocks:
        if (
            not isinstance(block, dict)
            or block.get("type") != "tool_use"
            or block.get("name") != "Read"
        ):
            continue
        tool_use_id = block.get("id")
        if not isinstance(tool_use_id, str) or not tool_use_id:
            continue
        signature = json.dumps(
            {"name": block.get("name"), "input": block.get("input")},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        state["pending"][tool_use_id] = signature
        if signature != state["signature"]:
            state["signature"] = signature
            state["noProgress"] = 0

    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        signature = state["pending"].pop(block.get("tool_use_id"), None)
        if signature is None:
            continue
        tool_use_result = event.get("tool_use_result")
        result_content = block.get("content")
        structured_marker = (
            isinstance(tool_use_result, dict)
            and tool_use_result.get("type") == "file_unchanged"
        )
        message_marker = (
            isinstance(result_content, str)
            and "wasted call" in result_content.lower()
            and "file unchanged since your last read" in result_content.lower()
        )
        if structured_marker and message_marker:
            if signature != state["signature"]:
                state["signature"] = signature
                state["noProgress"] = 0
            state["noProgress"] += 1
            if state["noProgress"] >= CLAUDE_NO_PROGRESS_LIMIT:
                return (
                    "Possible Claude tool loop: "
                    f"{CLAUDE_NO_PROGRESS_LIMIT} repeated identical reads returned no new data; "
                    "continuing within existing authority. The user decides whether to stop."
                )
        else:
            state["signature"] = signature
            state["noProgress"] = 0
    return None


def _claude_tool_history_warning(events: list[dict[str, Any]]) -> str | None:
    state = _claude_tool_event_state()
    for event in events:
        warning = _observe_claude_tool_event(event, state)
        if warning is not None:
            return warning
    return None


def runtime_warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "warning", "message": message}


def emit_runtime_warning(warning: dict[str, str], events_path: Path | None, reservation: Any) -> None:
    append_event_best_effort(events_path, "runtime_warning",
        approvalRef=reservation.state.get("authority", {}).get("approvalRef") if reservation is not None else None,
        **warning)
    print(f"WARNING {warning['code']}: {warning['message']}", file=sys.stderr)


def _run_child_streaming(
    process: subprocess.Popen[bytes],
    timeout: float | None,
    grace_seconds: float,
    signal_group: Any,
    max_stdout: int = MAX_STDOUT_BYTES,
    max_stderr: int = MAX_STDERR_BYTES,
    max_frame: int = MAX_FRAME_BYTES,
    detect_claude_tool_loop: bool = True,
    reservation: Any = None,
    owned_identity: dict[str, Any] | None = None,
    events_path: Path | None = None,
    warnings: list[dict[str, str]] | None = None,
) -> tuple[bytes, bytes, bool, bool, str | None, str | None, bool]:
    selector = selectors.DefaultSelector()
    streams: dict[int, str] = {}
    chunks: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    line_buffers: dict[str, bytes] = {"stdout": b"", "stderr": b""}
    tool_state = _claude_tool_event_state()
    tool_loop_error: str | None = None
    loop_warned = False
    timed_out = False
    drain_timed_out = False
    termination_signal = None
    capture_limited = False
    frame_limited = False

    for label, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        if stream is None:
            continue
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, label)
        streams[stream.fileno()] = label

    started = time.monotonic()
    deadline = started + timeout if timeout is not None else None
    next_observation = started
    last_output_at: str | None = None
    last_output_time = started
    last_probe_cpu_ticks: int | None = None
    last_probe_output_bytes = (0, 0)
    drain_deadline: float | None = None
    drain_started = False
    cleanup_deadline: float | None = None
    killed = False

    def request_stop(reason: str, *, timeout_stop: bool = False) -> None:
        nonlocal termination_signal, timed_out, tool_loop_error, cleanup_deadline, drain_deadline
        if timeout_stop:
            timed_out = True
        if termination_signal is None:
            termination_signal = "SIGTERM"
            if reservation is not None:
                reservation.request_owned_process_stop(owned_identity)
            else:
                signal_group(signal.SIGTERM)
            now = time.monotonic()
            term_seconds = min(max(0.0, grace_seconds), 10.0)
            cleanup_deadline = (now + max(0.0, (_mission_time(reservation.state["stopDeadlineAt"])
                                - datetime.now(timezone.utc)).total_seconds()) if reservation is not None
                                else now + term_seconds + max(0.0, grace_seconds))
            drain_deadline = min(cleanup_deadline, now + term_seconds)

    while streams or process.poll() is None:
        now = time.monotonic()
        if (reservation is not None or events_path is not None) and now >= next_observation:
            probe_error = None
            try:
                identity = _mission_process_identity(process.pid)
                activity = _mission_process_activity(process.pid)
            except (RunnerError, OSError):
                identity = None
                activity = None
                probe_error = "local process probe unavailable"
            process_alive = process.poll() is None
            identity_matches = (identity == owned_identity if owned_identity is not None and identity is not None else None)
            if process_alive and (identity is None or activity is None or identity_matches is False
                                  or activity["startTicks"] != identity["startTicks"]):
                probe_error = probe_error or "local process probe identity unverified"
                activity = None
            cpu_ticks = activity["cpuTicks"] if activity is not None else None
            cpu_delta = (cpu_ticks - last_probe_cpu_ticks
                         if cpu_ticks is not None and last_probe_cpu_ticks is not None else None)
            output_bytes = (len(chunks["stdout"]), len(chunks["stderr"]))
            output_changed = output_bytes != last_probe_output_bytes
            if not process_alive:
                diagnosis = "exited"
                probe_status = "exited"
            elif probe_error is not None:
                diagnosis = "unknown"
                probe_status = "unknown"
            elif output_changed or (cpu_delta is not None and cpu_delta > 0):
                diagnosis = "alive_active"
                probe_status = "alive"
            else:
                diagnosis = "alive_waiting"
                probe_status = "alive"
            observation = {"observedAt": utc_now(), "process": owned_identity or {"pid": process.pid},
                           "processAlive": process_alive,
                           "identityMatches": identity_matches,
                           "probe": {"method": "pid_identity+proc_cpu", "status": probe_status,
                                     "error": probe_error},
                           "processActivity": {"state": activity["state"] if activity else None,
                                                "cpuTicks": cpu_ticks, "cpuDeltaTicks": cpu_delta,
                                                "outputChanged": output_changed},
                           "diagnosis": diagnosis,
                           "modelStatus": "unknown", "hangConfirmed": False,
                           "elapsedMs": int((now - started) * 1000),
                           "stdoutBytes": output_bytes[0], "stderrBytes": output_bytes[1],
                           "lastOutputAt": last_output_at, "silenceSeconds": round(now - last_output_time, 3),
                           "productiveProgress": "unknown", "acceptance": "unverified"}
            if reservation is not None:
                reservation.observe_process(observation)
            append_event_best_effort(events_path, "process_observed", **observation)
            last_probe_cpu_ticks = cpu_ticks
            last_probe_output_bytes = output_bytes
            next_observation = now + CHILD_OBSERVATION_SECONDS
        if reservation is not None and reservation.stop_requested() and termination_signal is None:
            request_stop("mission cancelled or work cutoff reached", timeout_stop=not reservation.state["cancelled"])
        if drain_deadline is None and deadline is not None and now >= deadline:
            request_stop(f"launcher timed out after {timeout}s", timeout_stop=True)
        # EOF while the exact child remains alive is only silence. Once it has
        # exited, inherited pipes must still have a bounded collection phase.
        if process.poll() is not None and streams and not drain_started:
            drain_deadline = now + grace_seconds
            if cleanup_deadline is not None:
                drain_deadline = min(drain_deadline, cleanup_deadline)
            elif reservation is not None and reservation.state.get("stopDeadlineAt"):
                remaining = (_mission_time(reservation.state["stopDeadlineAt"]) - datetime.now(timezone.utc)).total_seconds()
                drain_deadline = min(drain_deadline, now + max(0.0, remaining))
            drain_started = True
        if process.poll() is not None and not streams:
            break
        if drain_deadline is not None and now >= drain_deadline:
            if process.poll() is None and not killed:
                killed = True
                termination_signal = "SIGKILL"
                if reservation is not None:
                    reservation.force_owned_process_stop(owned_identity)
                else:
                    signal_group(signal.SIGKILL)
                drain_started = True
                drain_deadline = cleanup_deadline
                continue
            drain_timed_out = bool(streams) or process.poll() is None
            break
        wait_for = 0.1
        if drain_deadline is None and deadline is not None:
            wait_for = max(0.0, min(wait_for, deadline - now))
        elif drain_deadline is not None:
            wait_for = max(0.0, min(wait_for, drain_deadline - now))
        if not streams:
            try:
                process.wait(timeout=wait_for)
            except subprocess.TimeoutExpired:
                pass
            continue
        ready = selector.select(wait_for)
        for key, _ in ready:
            stream = key.fileobj
            label = key.data
            try:
                chunk = os.read(stream.fileno(), 65536)
            except BlockingIOError:
                continue
            except OSError as exc:
                tool_loop_error = f"executor stream capture failed: {exc}"
                request_stop(tool_loop_error)
                chunk = b""
            if not chunk:
                selector.unregister(stream)
                streams.pop(stream.fileno(), None)
                continue
            limit = max_stdout if label == "stdout" else max_stderr
            if frame_limited and label == "stdout":
                # Once a single stdout frame is known to be oversized, keep at
                # most the triggering read.  The child is already being stopped;
                # draining later chunks would exceed the bounded frame receipt.
                continue
            if len(chunks[label]) + len(chunk) > limit:
                allowed = max(0, limit - len(chunks[label]))
                if allowed:
                    chunks[label].extend(chunk[:allowed])
                capture_limited = True
                request_stop(f"{label} capture exceeded {limit} bytes", timeout_stop=False)
                continue
            chunks[label].extend(chunk)
            last_output_at = utc_now()
            last_output_time = time.monotonic()
            if label != "stdout" or tool_loop_error is not None or capture_limited:
                continue
            line_buffers[label] += chunk
            while b"\n" in line_buffers[label]:
                line, line_buffers[label] = line_buffers[label].split(b"\n", 1)
                if len(line) > max_frame:
                    capture_limited = True
                    frame_limited = True
                    chunks[label] = chunks[label][:max_frame + 65536]
                    request_stop("stdout frame limit exceeded")
                    line_buffers[label] = b""
                    break
                if not detect_claude_tool_loop:
                    continue
                try:
                    event = strict_json_load_bytes(line, "Claude stream event")
                except StrictJSONError:
                    continue
                loop_warning = _observe_claude_tool_event(event, tool_state)
                if loop_warning is not None and not loop_warned:
                    warning = runtime_warning("CLAUDE_TOOL_PROGRESS", loop_warning)
                    if warnings is not None:
                        warnings.append(warning)
                    emit_runtime_warning(warning, events_path, reservation)
                    loop_warned = True
            if len(line_buffers[label]) > max_frame:
                capture_limited = True
                frame_limited = True
                chunks[label] = chunks[label][:max_frame + 65536]
                line_buffers[label] = b""
                request_stop("stdout frame limit exceeded without newline")
    selector.close()
    _close_process_pipes(process)
    if process.poll() is None:
        drain_timed_out = True
    return (
        bytes(chunks["stdout"]),
        bytes(chunks["stderr"]),
        timed_out,
        drain_timed_out,
        termination_signal,
        tool_loop_error,
        capture_limited,
    )


def _close_process_pipes(process: subprocess.Popen[bytes]) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _emergency_kill_and_reap(process: subprocess.Popen[bytes], wait_seconds: float) -> bool:
    """Kill this exact Popen child after identity/capture failure, then reap it."""
    deadline = time.monotonic() + min(max(wait_seconds, 0.0), 10.0)
    try:
        if process.poll() is None:
            process.kill()
    except OSError:
        pass
    while process.poll() is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            continue
    return True


def run_child(
    argv: list[str],
    cwd: Path,
    timeout: float | None,
    grace_seconds: float,
    *,
    detect_claude_tool_loop: bool = False,
    environment: dict[str, str] | None = None,
    reservation: Any = None,
    auxiliary: bool = False,
    events_path: Path | None = None,
) -> dict[str, Any]:
    started_at = utc_now()
    monotonic_started = time.monotonic()
    if reservation is not None:
        timeout = reservation.work_timeout(timeout)
        if not auxiliary:
            reservation.before_spawn()
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            env=environment,
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

    identity = None
    if reservation is not None:
        try:
            identity = _mission_process_identity(process.pid)
            if identity is None and process.poll() is not None:
                if not auxiliary:
                    reservation.intent.update(status="running", processStopped=True)
                    reservation.save()
            else:
                reservation.record_process(process.pid, auxiliary=auxiliary)
                identity = _mission_process_identity(process.pid) or identity
        except BaseException:
            # Popen is our exact unreaped child even if persistence failed.
            try:
                remaining = (mission_stop_deadline(reservation.state) - datetime.now(timezone.utc)).total_seconds()
                _emergency_kill_and_reap(process, remaining)
            finally:
                _close_process_pipes(process)
            raise
    timed_out = False
    drain_timed_out = False
    termination_signal = None
    capture_error = None
    capture_limited = False
    tool_loop_error = None
    warnings: list[dict[str, str]] = []
    stdout = b""
    stderr = b""

    def signal_group(sig: signal.Signals) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    try:
        (
            stdout, stderr, timed_out, drain_timed_out, termination_signal,
            tool_loop_error, capture_limited,
        ) = _run_child_streaming(process, timeout, grace_seconds, signal_group,
                                 detect_claude_tool_loop=detect_claude_tool_loop,
                                 reservation=reservation, owned_identity=identity, events_path=events_path,
                                 warnings=warnings)
    except BaseException as exc:
        capture_error = f"executor stream capture failed: {exc}"
        termination_signal = "SIGKILL"
        try:
            # The Popen handle is the exact child captured by this controller.
            # Keep this fallback safe when identity reads fail or persistence
            # never recorded an identity.
            remaining = ((mission_stop_deadline(reservation.state) - datetime.now(timezone.utc)).total_seconds()
                         if reservation is not None else grace_seconds)
            _emergency_kill_and_reap(process, remaining)
        finally:
            _close_process_pipes(process)
        if not isinstance(exc, OSError):
            raise
    errors = []
    if reservation is not None and reservation.state["cancelled"]:
        errors.append("mission cancelled: " + reservation.state.get("stopReason", "controller stop"))
    if timed_out:
        errors.append(f"launcher timed out after {timeout}s")
    if drain_timed_out:
        errors.append(f"post-SIGKILL pipe drain exceeded {grace_seconds}s")
    if capture_error:
        errors.append(capture_error)
    if tool_loop_error:
        errors.append(tool_loop_error)
    if capture_limited:
        errors.append("executor output capture exceeded the bounded frame/stream limit; captured bytes are incomplete")
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
        "captureLimited": capture_limited,
        "processStopped": process.poll() is not None,
        "warnings": warnings,
    }


def candidate_record(path: Path) -> tuple[dict[str, Any], bytes | None]:
    try:
        content, complete = read_bounded_file(path, MAX_CANDIDATE_BYTES)
    except FileNotFoundError:
        return {"path": str(path), "exists": False, "sha256": sha256_bytes(b""), "bytes": 0}, None
    except (OSError, ResponseEnvelopeError) as exc:
        return {"path": str(path), "exists": False, "sha256": None, "bytes": None, "error": str(exc)}, None
    record = {"path": str(path), "exists": True, "sha256": sha256_bytes(content), "bytes": len(content), "complete": complete}
    if not complete:
        record["error"] = "RESPONSE_LIMIT_ERROR: candidate capture is incomplete or changed while reading"
    return record, content


def parse_strict_candidate(content: bytes, label: str) -> tuple[Any, list[str]]:
    try:
        return parse_response_bytes(content, label).value, []
    except (ResponseEnvelopeError, StrictJSONError) as exc:
        return None, [str(exc)]


def parse_claude_transport(content: bytes) -> tuple[Any, list[str]]:
    # A provider may return the complete canonical response in one clean JSON
    # fence.  Try the shared envelope parser before interpreting Claude's
    # structured event stream so the same boundary semantics apply to both.
    if len(content) > MAX_STDOUT_BYTES:
        return None, ["RESPONSE_LIMIT_ERROR: stdout exceeds byte limit"]
    try:
        parsed = parse_response_bytes(content, "stdout candidate")
        if parsed.transport == "json_fence" and not (isinstance(parsed.value, dict) and "resultVersion" in parsed.value):
            return None, ["RESPONSE_FORMAT_ERROR: a fenced stdout document must be a canonical result"]
        return parsed.value, []
    except ResponseEnvelopeError as document_error:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return None, [str(document_error)]
        lines = text.splitlines()
        if len(lines) < 2:
            return None, [str(document_error)]
        events = []
        for line_number, line in enumerate(lines, start=1):
            if len(line.encode("utf-8")) > MAX_FRAME_BYTES:
                return None, ["RESPONSE_LIMIT_ERROR: JSONL frame exceeds byte limit"]
            if not line.strip():
                return None, [f"stdout JSONL line {line_number} is empty"]
            try:
                event = parse_response_bytes(line.encode("utf-8"), f"stdout JSONL line {line_number}", allowed_transports=["raw_json"]).value
            except ResponseEnvelopeError as line_error:
                return None, [str(document_error), str(line_error)]
            events.append(event)
        return events, []


def claude_runtime_model_errors(events: list[dict[str, Any]], expected_model: str | None) -> list[str]:
    observed: list[tuple[str, Any]] = []
    for index, event in enumerate(events, start=1):
        if "model" in event:
            observed.append((f"event {index} model", event["model"]))
        message = event.get("message")
        if isinstance(message, dict) and "model" in message:
            observed.append((f"event {index} message.model", message["model"]))
        if "modelUsage" in event:
            model_usage = event["modelUsage"]
            if not isinstance(model_usage, dict):
                observed.append((f"event {index} modelUsage", None))
            else:
                observed.extend((f"event {index} modelUsage key", model) for model in model_usage)

    if not observed:
        return ["Claude runtime model metadata is missing or empty"]

    errors = []
    for label, model in observed:
        if not isinstance(model, str) or not model.strip():
            errors.append(f"Claude runtime model metadata {label} must be a non-empty string")
        elif expected_model is None:
            errors.append(f"Claude runtime model {model!r} cannot be verified without routing.model")
        elif model != expected_model:
            errors.append(f"Claude runtime model {model!r} does not match routed model {expected_model!r}")
    return errors


def extract_stdout_candidate(
    content: bytes,
    order: dict[str, Any],
    schema_path: Path | None,
    routing: dict[str, Any] | None,
    extraction: dict[str, Any] | None = None,
    native_override: bool | None = None,
) -> tuple[bytes | None, list[str]]:
    transport, parse_errors = parse_claude_transport(content)
    if parse_errors:
        return None, parse_errors
    state_errors = response_state_errors(transport)
    if state_errors:
        return None, state_errors
    try:
        _, validator = _load_schema(resolve_schema_path(schema_path))
    except BuilderError as exc:
        raise GatewayError(str(exc)) from exc

    if isinstance(transport, dict) and "resultVersion" in transport:
        if "structured_output" in transport or "result" in transport:
            return None, ["Claude stdout contains ambiguous canonical and wrapper candidates"]
        if _option_values(shlex.split(order.get("launch", {}).get("command", "")), {"--json-schema"}):
            return None, ["Claude native mode requires the selected structured_output wrapper"]
        validation_errors = validate_candidate(transport, order, validator)
        if extraction is not None:
            extraction.update(field="document", eventIndex=None)
        return content if not validation_errors else None, [
            f"stdout candidate validation failed: {error}" for error in validation_errors
        ]

    if isinstance(transport, dict):
        events = [transport]
    elif isinstance(transport, list):
        if any(not isinstance(event, dict) for event in transport):
            return None, ["Claude stdout transport events must all be JSON objects"]
        events = transport
    else:
        return None, ["Claude stdout transport must be a canonical result object, event object, event array, or JSONL"]

    history_warning = _claude_tool_history_warning(events)
    if history_warning is not None and extraction is not None:
        extraction.setdefault("warnings", []).append(runtime_warning("CLAUDE_TOOL_PROGRESS", history_warning))

    terminal_indexes = [index for index, event in enumerate(events) if event.get("type") == "result"]
    if len(terminal_indexes) != 1:
        return None, [f"Claude stdout transport must contain exactly one terminal result event; found {len(terminal_indexes)}"]
    terminal_index = terminal_indexes[0]
    if terminal_index != len(events) - 1:
        return None, ["Claude terminal result must be the final event"]
    terminal = events[terminal_index]

    transport_errors = claude_runtime_model_errors(
        events,
        routing.get("model") if isinstance(routing, dict) and isinstance(routing.get("model"), str) else None,
    )
    if terminal.get("subtype") != "success":
        transport_errors.append("Claude terminal subtype must be success")
    if terminal.get("is_error") is not False:
        transport_errors.append("Claude terminal is_error must be false")
    permission_denials = terminal.get("permission_denials")
    if not isinstance(permission_denials, list):
        transport_errors.append("Claude terminal permission_denials must be an array")
    elif permission_denials and extraction is not None:
        extraction.setdefault("warnings", []).append(runtime_warning("CLAUDE_PERMISSION_DENIALS",
            f"Claude recorded {len(permission_denials)} denied tool requests; inspect their impact on "
            "the requested outcome. Historical denials alone do not invalidate a completed result."))
    structured = terminal.get("structured_output")
    text_result = terminal.get("result")
    native = bool(_option_values(shlex.split(order.get("launch", {}).get("command", "")), {"--json-schema"})) if native_override is None else native_override
    if extraction is not None:
        extraction.update(field="structured_output" if native else "result", eventIndex=terminal_index)
    # Native Claude can emit both its authoritative structured projection and
    # explanatory text. Select the source fixed before launch; never fall back
    # to that text when the selected projection is missing or invalid.
    if native:
        if not isinstance(structured, dict):
            transport_errors.append("Claude native mode requires structured_output object")
            inner_bytes = None
        else:
            try:
                inner_bytes = json.dumps(structured, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            except UnicodeEncodeError:
                transport_errors.append("Claude structured_output contains invalid Unicode")
                inner_bytes = None
    elif structured is not None:
        transport_errors.append("Claude structured_output was not selected before launch")
        inner_bytes = None
    elif not isinstance(text_result, str) or not text_result.strip():
        transport_errors.append("Claude terminal result must be a non-empty JSON string")
        inner_bytes = None
    else:
        try:
            inner_bytes = text_result.encode("utf-8")
        except UnicodeEncodeError as exc:
            transport_errors.append(f"Claude terminal result is not valid UTF-8: {exc}")
            inner_bytes = None
    if transport_errors or inner_bytes is None:
        return None, sorted(set(transport_errors))

    candidate, inner_parse_errors = parse_strict_candidate(inner_bytes, "Claude terminal inner result")
    if inner_parse_errors:
        return None, inner_parse_errors
    validation_errors = validate_candidate(candidate, order, validator)
    if validation_errors:
        return None, [f"stdout candidate validation failed: {error}" for error in validation_errors]
    return inner_bytes, []


def synthetic_failed_result(
    order: dict[str, Any],
    candidate: dict[str, Any],
    stream_records: list[tuple[str, dict[str, Any]]],
    errors: list[str],
    evidence_path: Path | None = None,
) -> dict[str, Any]:
    if evidence_path is not None:
        artifacts = [
            {
                "path": str(evidence_path),
                "exists": True,
                "type": "malformed-result-evidence",
                "note": f"Original candidate bytes preserved as sha256:{evidence_path.name.split('.', 1)[0]}",
            }
        ]
    else:
        artifacts = [
            {
                "path": candidate["path"],
                "exists": bool(candidate.get("exists")),
                "type": "raw-candidate",
                "note": f"Controller-observed candidate sha256:{candidate.get('sha256') or 'unavailable'}",
            }
        ]
    payload = {
        "resultVersion": RESULT_VERSION,
        "orderId": order["orderId"],
        "executor": order["executor"],
        "status": "failed",
        "summary": "Result Gateway closed the executor attempt without an acceptable candidate result.",
        "filesChanged": [],
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
    expected = order["outputContract"].get("handoff")
    if expected is not None:
        payload["handoff"] = expected
    for artifact in artifacts:
        if artifact["exists"]:
            path = Path(artifact["path"])
            if path.is_file() and not path.is_symlink():
                artifact["sha256"] = sha256_bytes(path.read_bytes())
                artifact["mediaType"] = "application/octet-stream"
    return payload


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
    try:
        _, validator = _load_schema(resolve_schema_path(schema_path))
        errors = _schema_errors(validator, payload)
        if errors:
            raise BuilderError("internal failed-result schema error: " + "; ".join(errors))
        # This is a controller failure statement. Its evidence is bound in the
        # closure; do not mislabel a synthetic payload as executor response bytes.
        create_only_finalize(result_path, payload)
        return payload
    except (BuilderError, OSError) as exc:
        raise GatewayError(str(exc)) from exc


def finalize_candidate(
    order_path: Path,
    candidate_path: Path,
    result_path: Path,
    evidence_dir: Path,
    schema_path: Path | None,
    *, protocol_binding: dict[str, Any] | None = None, expected_order_sha256: str | None = None,
    expected_candidate_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        return build_result(order_path, candidate_path, result_path, evidence_dir, schema_path,
                            protocol_binding=protocol_binding, expected_order_sha256=expected_order_sha256,
                            expected_candidate_sha256=expected_candidate_sha256)
    except ProtocolFailure:
        raise
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
    result: dict[str, Any] | None,
    candidate: dict[str, Any],
    stdout_record: dict[str, Any],
    stderr_record: dict[str, Any],
    errors: list[str],
    routing: dict[str, Any] | None,
    routing_sha256: str | None,
) -> dict[str, Any]:
    result_bytes = result_path.read_bytes() if result is not None else None
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
        "canonicalFinalized": result is not None,
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
        "canonicalResultSha256": sha256_bytes(result_bytes) if result_bytes is not None else None,
        "canonicalStatus": result["status"] if result is not None else None,
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
    recovery = parser.add_mutually_exclusive_group()
    recovery.add_argument("--recover-report", action="store_true", help="Recover reports within the approved budget; never rerun product")
    recovery.add_argument("--recover-report-from", type=Path, help="Collect a controller-authorized manually reviewed JSON report without a model")
    return parser


def _accepted_review(reservation: Any) -> str | None:
    return next((key for key, intent in reservation.state["intents"].items()
                 if intent.get("candidateIntentId") == reservation.meta["intentId"] and
                 intent["action"] == "review" and intent["status"] == "accepted"), None)


def _report_capture_resumable(reservation: Any) -> bool:
    """Recognize only the post-observation, pre-verification report boundary."""
    intent = reservation.intent
    ordinal = intent.get("reportAttemptsUsed", 0)
    report_id = reservation.meta["intentId"] + f":report:{ordinal}"
    report = reservation.state["intents"].get(report_id)
    child = report.get("child") if isinstance(report, dict) else None
    return bool(
        intent.get("status") == "captured"
        and "verification" not in intent
        and "terminalTemplate" not in intent
        and intent.get("reportIntentId") == report_id
        and type(ordinal) is int and ordinal > 0
        and intent.get("processStopped") is True
        and "protocolRefs" in intent and "recoveryProof" in intent
        and isinstance(report, dict)
        and report.get("action") == "report"
        and report.get("originalIntentId") == reservation.meta["intentId"]
        and report.get("status") == "running"
        and report.get("processStopped") is True
        and isinstance(child, dict)
        and child.get("processStopped") is True
        and child.get("exitCode") == 0
        and not any(child.get(key) for key in ("timedOut", "drainTimedOut", "captureLimited"))
    )


def report_capability(reservation: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Only an explicitly approved, pinned Q6 receipt enables this adapter.

    The integration fixture supplies a fake CLI. Root supplies a real deny-probe
    receipt in mission authority after Q6; a worker context claim is ignored.
    """
    ref = reservation.state["authority"].get("reportCapabilityRef")
    if not isinstance(ref, dict) or _mission_file_ref(Path(ref["path"])) != ref:
        raise GatewayError("report recovery disabled: no pinned Q6 capability receipt")
    raw, complete = read_bounded_file(Path(ref["path"]), 1024 * 1024)
    cap = strict_json_load_bytes(raw, "report capability")
    if not complete or cap.get("version") != "CENTURION_NO_TOOLS_REPORT_V1" or cap.get("probe") != {
            "status": "passed", "toolsDenied": True, "mcpDisabled": True, "hooksDisabled": True,
            "isolatedConfig": True, "productUnchanged": True}:
        raise GatewayError("report capability lacks the required Q6 deny proof")
    for key in ("cliRef", "configRef"):
        if _mission_file_ref(Path(cap[key]["path"])) != cap[key]:
            raise GatewayError("report CLI/config changed since capability probe")
    if not os.access(cap["cliRef"]["path"], os.X_OK):
        raise GatewayError("report CLI is not executable")
    if cap.get("route") != {"executor": "claude", "model": "claude-opus-5-5", "effort": "high"}:
        raise GatewayError("unsupported report capability route")
    mode = cap.get("launchMode", "bare")
    if mode not in {"bare", "native-profile-readonly"}:
        raise GatewayError("unsupported report capability launch mode")
    if mode == "native-profile-readonly":
        for key in ("sandboxRef", "profileRef"):
            if not isinstance(cap.get(key), dict) or _mission_file_ref(Path(cap[key]["path"])) != cap[key]:
                raise GatewayError("report isolation/profile changed since capability probe")
        if not os.access(cap["sandboxRef"]["path"], os.X_OK):
            raise GatewayError("report sandbox is not executable")
        native_home = Path(cap.get("nativeHome", ""))
        if (not native_home.is_absolute() or not native_home.is_dir() or native_home.is_symlink()
                or Path(cap["profileRef"]["path"]) != native_home / ".claude.json"
                or Path(cap["sandboxRef"]["path"]).name != "bwrap"):
            raise GatewayError("invalid report native profile isolation boundary")
        validate_claude_proxy_environment({"ANTHROPIC_BASE_URL": cap.get("baseUrl", "")})
    config, complete = read_bounded_file(Path(cap["configRef"]["path"]), 1024 * 1024)
    if not complete or strict_json_load_bytes(config, "isolated report settings") != {"disableAllHooks": True}:
        raise GatewayError("report settings must disable all hooks and contain no other settings")
    # `configRef` is immutable input settings. Claude owns the runtime scratch
    # directory and may persist native state there even with --bare; recovery
    # must validate the capability and scratch boundary without relaunching or
    # requiring that directory to be empty.
    scratch_dir = Path(cap.get("scratchDir", cap.get("configDir", "")))
    if not scratch_dir.is_dir() or scratch_dir.is_symlink():
        raise GatewayError("report runtime scratch directory is unavailable")
    try:
        for index, path in enumerate(scratch_dir.rglob("*")):
            if index >= 4096:
                raise GatewayError("report runtime scratch inspection limit exceeded")
            if path.is_symlink():
                raise GatewayError("report runtime scratch contains a symlink")
            if path.name.lower() in {"settings.json", "settings.local.json"} or any(
                marker in path.name.lower() for marker in ("hook", "mcp", "plugin")
            ):
                raise GatewayError("report runtime scratch contains a hooks/MCP/plugin entry")
            if not (path.is_file() or path.is_dir()):
                raise GatewayError("report runtime scratch contains an unsupported entry")
            if path.is_file() and path.suffix == ".json":
                # bwrap creates the empty mount target on the writable scratch
                # filesystem; the native profile itself is mounted read-only.
                if mode == "native-profile-readonly" and path.name == ".claude.json":
                    if path.stat().st_size != 0:
                        raise GatewayError("report native profile mount target was modified")
                    continue
                raw, complete = read_bounded_file(path, 1024 * 1024)
                if not complete:
                    raise GatewayError("report runtime scratch JSON inspection limit exceeded")
                pending = [strict_json_load_bytes(raw, "report runtime scratch JSON")]
                while pending:
                    item = pending.pop()
                    if isinstance(item, dict):
                        if any(key in {"hooks", "mcpServers", "enabledPlugins", "extraKnownMarketplaces", "pluginDirs"}
                               and value not in (None, False, {}, []) for key, value in item.items()):
                            raise GatewayError("report runtime scratch contains hooks/MCP/plugin configuration")
                        pending.extend(item.values())
                    elif isinstance(item, list):
                        pending.extend(item)
    except OSError as exc:
        raise GatewayError(f"report runtime scratch cannot be inspected: {exc}") from exc
    cap["scratchDir"] = str(scratch_dir)
    return cap, ref


def report_launch(cap: dict[str, Any], schema: dict[str, Any], prompt: str) -> tuple[list[str], dict[str, str]]:
    """Build only the capability-tested native launch, without arbitrary argv."""
    env = executor_environment("claude", dict(os.environ))
    validate_claude_proxy_environment(env)
    scratch = cap["scratchDir"]
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "CLAUDE_CONFIG_DIR"):
        env[key] = scratch
    env.update(CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_AUTOUPDATER="1")
    argv = [cap["cliRef"]["path"], "--model", cap["route"]["model"], "--effort", "high",
            "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--settings", cap["configRef"]["path"], "--setting-sources", "", "--no-session-persistence",
            "--output-format", "json", "--json-schema", json.dumps(schema), "-p", prompt]
    if cap.get("launchMode", "bare") == "bare":
        argv.insert(1, "--bare")
    else:
        # Existing client state is mounted read-only; no credential extraction,
        # fabricated API key, writable live home, hooks or inherited MCP config.
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        if env["ANTHROPIC_BASE_URL"] != cap["baseUrl"]:
            raise GatewayError("report local proxy changed since capability probe")
        native_home = Path(cap["nativeHome"])
        wrapper = [cap["sandboxRef"]["path"], "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
                   "--unshare-pid", "--die-with-parent", "--bind", scratch, scratch]
        for name in (".claude", ".codex", ".agents"):
            wrapper.extend(["--tmpfs", str(native_home / name)])
        wrapper.extend(["--ro-bind", "/dev/null", str(native_home / "AGENTS.md"), "--chdir", scratch,
                        "--ro-bind", cap["profileRef"]["path"], str(Path(scratch) / ".claude.json")])
        argv = wrapper + argv
    return argv, env


def report_projection(reservation: Any) -> dict[str, Any]:
    """Allowlisted facts only: raw/provider errors/env never enter this prompt."""
    order, intent = reservation.order, reservation.intent
    before, after = intent["workspaceBaseline"], intent["workspaceAfter"]
    changes = [{"path": path, "action": "added" if path not in before else "deleted" if path not in after else "modified"}
               for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
    artifact_paths = {row["path"] for row in intent["snapshot"]["files"] if row["sha256"] is not None}
    artifact_paths.update(item["path"] for item in order["expectedArtifacts"]
                          if reservation.policy.resolve_under_repo(item["path"]) != reservation.policy.resolve_under_repo(order["outputContract"]["resultPath"]))
    artifacts = []
    for value in sorted(artifact_paths):
        path = reservation.policy.order_path(value, "report artifact fact")
        if not path.is_file():
            continue  # Required missing artifacts are rejected by controller proof.
        ref = _mission_file_ref(path)
        artifacts.append({"path": ref["path"], "exists": True, "sha256": ref["sha256"],
                          "type": "observed-product", "mediaType": _report_media_type(path),
                          "note": "Controller-observed artifact; report executor did not create it."})
    checks = [{key: check[key] for key in ("command", "cwd", "status", "exitCode")}
              | {"summary": "Previously observed controller check; not rerun by report executor."}
              for check in intent["recoveryProof"]]
    return {"mode": "report_only_no_tools", "instruction": "Report the saved product only. Do not implement or invent evidence.",
            "order": {key: order[key] for key in ("orderId", "executor", "objective", "acceptanceCriteria", "nonGoals")},
            "handoff": order["outputContract"]["handoff"], "productSnapshot": intent["snapshot"],
            "filesChanged": changes, "artifacts": artifacts,
            "workspaceDiff": [{"path": row["path"], "before": before.get(row["path"]), "after": after.get(row["path"])} for row in changes],
            "proofArgv": [check["argv"] for check in order["proofCommands"]],
            "originalOrderSha256": intent["orderRef"]["sha256"], "rawSha256": intent["protocolCandidateSha256"],
            "controllerProof": checks}


def _report_media_type(path: Path) -> str:
    """Extension metadata, not content proof; ignore host MIME customizations."""
    media_type, encoding = mimetypes.MimeTypes(filenames=()).guess_type(path.name, strict=True)
    return media_type if media_type and encoding is None else "application/octet-stream"


def validate_report_facts(result: dict[str, Any], projection: dict[str, Any]) -> None:
    """The report may phrase a summary; it cannot invent execution facts."""
    if result["filesChanged"] != projection["filesChanged"]:
        raise GatewayError("report filesChanged differs from observed workspace diff")
    keys = ("command", "cwd", "status", "exitCode")
    if [{k: row.get(k) for k in keys} for row in result["proof"]] != [{k: row[k] for k in keys} for row in projection["controllerProof"]]:
        raise GatewayError("report proof differs from saved controller observations")
    keys = ("path", "exists", "sha256", "type", "mediaType")
    expected = {row["path"]: {k: row[k] for k in keys} for row in projection["artifacts"]}
    actual = {row["path"]: {k: row.get(k) for k in keys} for row in result["artifacts"]}
    # Older projections supplied a generic binary placeholder for every file.
    # Accept that original value or the standard extension-derived descriptor.
    # This adjusts only a comparison copy; raw/candidate/canonical bytes and the
    # saved projection remain unchanged. Explicit concrete types stay exact.
    for path, row in actual.items():
        saved = expected.get(path)
        if (saved is not None and saved["mediaType"] == "application/octet-stream"
                and row["mediaType"] == _report_media_type(Path(path))):
            row["mediaType"] = saved["mediaType"]
    if len(actual) != len(result["artifacts"]) or actual != expected:
        raise GatewayError("report artifacts differ from saved controller observations")


def _reject_report(reservation: Any, report: dict[str, Any], namespace: Path,
                   code: str, candidate: bytes, *, retryable: bool = True) -> None:
    comparable = candidate
    try:
        value = strict_json_load_bytes(candidate, "invalid report fingerprint")
        if isinstance(value, dict):
            value = value.get("structured_output", value)
        comparable = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    except StrictJSONError:
        pass
    fingerprint = sha256_bytes(code.encode() + b"\0" + comparable)
    report.update(status="rejected", failureCode=code, failureFingerprint=fingerprint)
    evidence = {"version": "CENTURION_REPORT_FAILURE_V1", "intentId": report["intentId"],
        "failureCode": code, "candidateSha256": sha256_bytes(candidate), "fingerprint": fingerprint,
        "processStopped": report.get("processStopped"), "productReplayed": False}
    failure = namespace / "failure.json"
    if not failure.exists():
        atomic_create(failure, (json.dumps(evidence, sort_keys=True) + "\n").encode())
    report["failureRef"] = _mission_file_ref(failure)
    reservation.save()
    error = ReportRetryable if retryable else GatewayError
    raise error("report validation failed: " + code + "; saved product is unchanged")


def recover_reports(reservation: Any, args: Any, paths: dict[str, Any], routing: Any) -> int:
    """Retry changed report candidates, preserving budget, custody and product."""
    while True:
        try:
            return recover_report(reservation, args, paths, routing)
        except ReportRetryable:
            if getattr(args, "recover_report_from", None) is not None:
                raise
            # recover_report checks identical failures, budget and stopped effects
            # before reserving another ordinal. A restart collects the same turn.


def recover_report(reservation: Any, args: Any, paths: dict[str, Any], routing: Any) -> int:
    """Collect one durable reporting ordinal, never another product attempt."""
    intent = reservation.intent
    capture_resume = _report_capture_resumable(reservation)
    if intent["status"] not in {"reportable", "captured"} or (intent["status"] == "captured" and not capture_resume):
        raise GatewayError("report recovery requires a saved complete product protocol failure")
    for ref in intent["protocolRefs"].values():
        if _mission_file_ref(Path(ref["path"])) != ref:
            raise GatewayError("original recovery custody changed")
    if workspace_snapshot(reservation.state) != intent["workspaceAfter"]:
        raise GatewayError("product changed before report recovery")
    if not isinstance(intent.get("recoveryProof"), list):
        raise GatewayError("report recovery requires saved successful controller proof")
    verify_required_proof_checks(intent["recoveryProof"])
    if "report" not in reservation.state["authority"]["allowedActions"]:
        raise GatewayError("mission has no report recovery authority")
    ordinal = intent["reportAttemptsUsed"]
    ordinal_key = reservation.meta["intentId"] + f":report:{ordinal}"
    report = reservation.state["intents"].get(ordinal_key) if ordinal else None
    if ordinal and report is None:
        raise GatewayError("saved report attempt is missing")
    manual_source = getattr(args, "recover_report_from", None)
    if report is not None and report["status"] == "rejected":
        if not report.get("processStopped"):
            raise GatewayError("report effect is unknown; reconcile it before any retry")
        rejected = [row for row in reservation.state["intents"].values()
                    if row.get("originalIntentId") == reservation.meta["intentId"] and row.get("failureFingerprint")]
        if manual_source is None and len({row["failureFingerprint"] for row in rejected}) < len(rejected):
            raise GatewayError("report recovery made no progress: identical invalid response repeated; manual review remains available")
        previous = report
        report = None
    else:
        previous = None
    if report is None:
        ordinal += 1
        ordinal_key = reservation.meta["intentId"] + f":report:{ordinal}"
    namespace = reservation.policy.control_namespace / f"report-{ordinal}"
    mode = report.get("mode", "model") if report is not None else ("manual_review" if manual_source is not None else "model")
    manual_fields = {}
    if mode == "manual_review":
        authority = reservation.state["authority"]
        source = reservation.policy.control_path(manual_source or report["manualCandidateRef"]["path"], "manual report candidate")
        source_ref = _mission_file_ref(source)
        manual_fields = {"mode": mode, "manualReviewRef": authority.get("manualReportReviewRef"),
                         "manualReportAuthorityRef": authority.get("manualReportAuthorityRef"), "manualCandidateRef": source_ref}
        verify_manual_report_review(reservation.policy.repo_path, reservation.order["orderId"],
            dict(manual_fields, originalRefs=intent["protocolRefs"], snapshot=intent["snapshot"], candidateRef=source_ref))
        cap, cap_ref = None, None
    else:
        cap, cap_ref = report_capability(reservation)
    if report is None:
        if capture_resume:
            raise GatewayError("report capture custody is incomplete")
        reservation.work_timeout(1)
        from agent_result_builder import native_result_schema
        projection = report_projection(reservation)
        if previous is not None:
            projection["previousReportFailure"] = {"ordinal": ordinal - 1, "code": previous.get("failureCode", "report_process_failed"),
                "instruction": "Correct this report validation failure using only the supplied observed facts and schema."}
        prompt = json.dumps(projection, sort_keys=True)
        if mode == "model":
            remaining = reservation.state["budget"]["maxModelLaunches"] - reservation.state["budget"]["modelLaunchesUsed"]
            if remaining < 1 + pending_review_launches(reservation.state):
                reservation.state.update(status="blocked", blocker={"decisionOwner": "customer", "reasonCode": "model_launch_budget",
                    "reason": "report launch budget exhausted or reserved for mandatory review; saved product retained"})
                reservation.save()
                raise GatewayError("report launch budget exhausted or reserved for mandatory review")
            scratch = Path(cap["scratchDir"])
            if ordinal == 1:
                if any(scratch.iterdir()):
                    raise GatewayError("report first launch requires fresh runtime scratch")
            else:
                scratch = scratch / f"attempt-{ordinal}"
                scratch.mkdir(mode=0o700, exist_ok=False)
            argv, env = report_launch(dict(cap, scratchDir=str(scratch)), native_result_schema(reservation.order, routing), prompt)
        else:
            raw, complete = read_bounded_file(source, MAX_CANDIDATE_BYTES)
            if not complete:
                raise GatewayError("manual report candidate exceeds size limit")
            candidate_value = strict_json_load_bytes(raw, "manually reviewed report")
            _, validator = _load_schema(resolve_schema_path(args.schema))
            if validate_candidate(candidate_value, reservation.order, validator):
                raise GatewayError("manually reviewed report does not satisfy the original result contract")
            validate_report_facts(candidate_value, projection)
        namespace.mkdir(mode=0o700, exist_ok=False)
        report = {"intentId": ordinal_key, "taskId": reservation.meta["taskId"], "action": "report",
            "orderId": reservation.order["orderId"], "orderSha256": intent["orderSha256"], "executor": "claude",
            "status": "reserved", "effect": "not_started", "processStopped": False, "reportAttemptsUsed": 0,
            "idempotencyKey": [reservation.state["missionId"], reservation.meta["taskId"],
                               reservation.state["tasks"][reservation.meta["taskId"]]["productAttemptsUsed"], ordinal],
            "capabilityRef": cap_ref, "originalIntentId": reservation.meta["intentId"],
            "snapshot": intent["snapshot"], "beforeSnapshot": intent["snapshot"], "projection": projection,
            "mode": mode, "modelLaunch": mode == "model", **manual_fields}
        reservation.state["intents"][ordinal_key] = report
        intent.update(reportAttemptsUsed=ordinal, reportIntentId=ordinal_key)
        reservation.state["budget"]["modelLaunchesUsed"] += int(mode == "model")
        reservation.save()  # no refund after this point, including a spawn failure
        atomic_create(namespace / "start.json", (json.dumps({"version":"CENTURION_REPORT_START_V1", "orderId":reservation.order["orderId"],
            "originalRefs":intent["protocolRefs"], "capabilityRef":cap_ref, "snapshot":intent["snapshot"],
            "idempotencyKey":report["idempotencyKey"], "projectionSha256":sha256_bytes(prompt.encode()),
            "mode": mode, **manual_fields})+"\n").encode())
        # The original command is never consulted for this report dispatch.
        if mode == "model":
            rr = MissionReservation(reservation.order, reservation.policy, reservation.state, reservation.path, reservation.lock, "launch")
            rr.meta = dict(reservation.meta, intentId=ordinal_key, action="report")
            rr.intent = report
            child = run_child(argv, scratch, rr.work_timeout(None if reservation.order["launch"]["timeoutSeconds"] is None else 120), 10,
                              environment=env, reservation=rr, detect_claude_tool_loop=True, events_path=paths.get("events"))
        else:
            child = {"stdout": raw, "stderr": b"", "exitCode": 0, "processStopped": True, "error": None}
            report["status"] = "running"  # Controller collection, no model process.
        atomic_create(namespace / "stdout.bin", child["stdout"])
        atomic_create(namespace / "stderr.bin", child["stderr"])
        stopped = child.get("processStopped", False)
        report.update(processStopped=stopped, effect="observed" if stopped else "unknown_effect")
        report["child"] = {key: child.get(key) for key in ("exitCode", "timedOut", "drainTimedOut", "captureLimited", "processStopped")}
        atomic_create(namespace / "child.json", (json.dumps(report["child"], sort_keys=True)+"\n").encode())
        reservation.save()
        if child["error"] or child["exitCode"] != 0 or not stopped:
            report["status"] = "rejected" if stopped else "unknown_effect"
            reservation.save()
            raise GatewayError("report turn failed; saved product retained, never replay it")
    else:
        if report.get("capabilityRef") != cap_ref:
            raise GatewayError("saved report capability binding changed")
        if any(report.get(key) != value for key, value in manual_fields.items()):
            raise GatewayError("saved manual review binding changed")
        if report["status"] in {"running", "dispatching"} and (namespace / "child.json").exists():
            saved = json.loads((namespace / "child.json").read_bytes())
            if report.get("process") and _mission_process_identity(report["process"]["pid"]) == report["process"]:
                raise GatewayError("report child still open; never relaunch")
            report.update(child=saved, processStopped=saved.get("processStopped"))
        if report["status"] not in {"running", "dispatching"} or not report.get("processStopped") or report["child"].get("exitCode") != 0 or any(report["child"].get(k) for k in ("timedOut", "drainTimedOut", "captureLimited")):
            raise GatewayError("report already reserved/open/failed; collect existing custody only, never relaunch")
    # Revalidate immutable inputs and reject configuration injected by the CLI
    # itself before accepting its output, as well as on restart collection.
    if mode == "model":
        report_capability(reservation)
    # Restart can collect these exact saved bytes, never create a second turn.
    stdout, complete = read_bounded_file(namespace / "stdout.bin", MAX_STDOUT_BYTES)
    if not complete:
        raise GatewayError("report raw capture incomplete")
    candidate_path = namespace / "candidate.json"
    if mode == "manual_review":
        if sha256_bytes(stdout) != report["manualCandidateRef"]["sha256"] or len(stdout) != report["manualCandidateRef"]["bytes"]:
            raise GatewayError("saved manual report differs from the reviewed bytes")
        extracted, errors = stdout, []
    else:
        extracted, errors = extract_stdout_candidate(stdout, reservation.order, args.schema, dict(routing, model="claude-opus-5-5"), {}, native_override=True)
    if errors or extracted is None:
        if workspace_snapshot(reservation.state) != intent["workspaceAfter"]:
            raise GatewayError("product changed during invalid report; no automatic retry")
        _reject_report(reservation, report, namespace, "invalid_result_contract", stdout)
    try:
        validate_report_facts(strict_json_load_bytes(extracted, "report facts"), report["projection"])
    except GatewayError:
        if workspace_snapshot(reservation.state) != intent["workspaceAfter"]:
            raise GatewayError("product changed during report; no automatic retry")
        _reject_report(reservation, report, namespace, "report_facts_differ_from_observations", extracted)
    if not candidate_path.exists():
        if capture_resume:
            raise GatewayError("saved report candidate is missing")
        atomic_create(candidate_path, extracted)
    elif candidate_path.read_bytes() != extracted:
        raise GatewayError("saved report candidate changed")
    if workspace_snapshot(reservation.state) != intent["workspaceAfter"]:
        raise GatewayError("report changed product workspace")
    result_path = paths["result"]
    if capture_resume and intent.get("resultRef") != _mission_file_ref(result_path):
        raise GatewayError("saved canonical result observation changed")
    if not result_path.exists():
        result = finalize_candidate(args.order, candidate_path, result_path, paths["evidence"], args.schema,
                                    expected_order_sha256=intent["orderRef"]["sha256"], expected_candidate_sha256=sha256_bytes(extracted))
    else:
        result, _ = verify_result(result_path, reservation.order, reservation.policy)
    candidate_result = strict_json_load_bytes(extracted, "saved report candidate")
    canonical_result = {key: value for key, value in result.items() if key != "responseEnvelope"}
    if canonical_result != candidate_result:
        raise GatewayError("canonical result differs from saved report candidate")
    if capture_resume:
        if intent.get("resultStatus") != result.get("status"):
            raise GatewayError("saved canonical result observation changed")
    else:
        reservation.observe_result(result, result_path, process_stopped=True)
    verification = {}
    verify_workspace_diff(reservation, result)
    _, artifacts = verify_result(result_path, reservation.order, reservation.policy)
    checks = check_expected_artifacts(reservation.order, reservation.policy, artifacts, result_path)
    verify_required_artifact_checks(checks)
    verification.update(artifacts=checks, proof=intent["recoveryProof"],
        inputResults=verify_input_results(reservation.order, reservation.policy.repo_path), resultSha256=intent["resultRef"]["sha256"],
        productSnapshotSha256=intent["snapshot"]["sha256"], criteria=reservation.order["acceptanceCriteria"])
    report["status"] = "captured"
    report.update(resultRef=intent["resultRef"], resultStatus=result["status"], effect="observed", snapshot=intent["snapshot"])
    reporting = {"version":"CENTURION_REPORT_RECOVERY_V1", "orderId":reservation.order["orderId"],
        "originalRefs":intent["protocolRefs"], "capabilityRef":cap_ref, "snapshot":intent["snapshot"],
        "idempotencyKey":report["idempotencyKey"], "candidateRef":_mission_file_ref(candidate_path),
        "stdoutRef":_mission_file_ref(namespace/"stdout.bin"), "stderrRef":_mission_file_ref(namespace/"stderr.bin"),
        "startRef":_mission_file_ref(namespace/"start.json"), "canonicalResultSha256":intent["resultRef"]["sha256"], "status":"passed",
        **({"mode": mode, **manual_fields} if "mode" in json.loads((namespace/"start.json").read_bytes()) else {})}
    reporting_path = namespace / "closure.json"
    if not reporting_path.exists():
        atomic_create(reporting_path, (json.dumps(reporting, sort_keys=True)+"\n").encode())
    elif json.loads(reporting_path.read_bytes()) != reporting:
        raise GatewayError("report closure collision")
    original_start = json.loads(paths["start"].read_bytes())
    terminal = {"version":"AQUILA_CONTROLLER_ACCEPTANCE_V1", "orderId":reservation.order["orderId"],
        "runId":original_start["runId"], "orderSha256":intent["orderRef"]["sha256"],
        "startReceiptSha256":_mission_file_ref(paths["start"])["sha256"],
        "closureSha256":_mission_file_ref(paths["closure"])["sha256"], "canonicalResultSha256":intent["resultRef"]["sha256"],
        "status":"passed", "reason":None, "completedAt":utc_now(), "reporting":_mission_file_ref(reporting_path)}
    proof = dict(terminal, version="AQUILA_CONTROLLER_VERIFICATION_V1", scope="post_execution_proof", observedChecks=verification)
    proof_path = reservation.policy.control_namespace / "controller-proof.json"
    if not proof_path.exists():
        atomic_create(proof_path, (json.dumps(proof,sort_keys=True)+"\n").encode())
    terminal["proofReceiptSha256"] = _mission_file_ref(proof_path)["sha256"]
    intent.update(verification=verification, terminalTemplate=terminal,
                  captureRefs={"proof":_mission_file_ref(proof_path), "reporting":_mission_file_ref(reporting_path), **intent["protocolRefs"]})
    reservation.save()
    return _resume_captured(reservation, reservation.policy.control_namespace / "controller-acceptance.json")


def _resume_captured(reservation: Any, acceptance_path: Path) -> int:
    """Collect persisted proof/review; never rerun implementation or proof."""
    intent = reservation.intent
    if intent["status"] != "captured" or "verification" not in intent:
        print(json.dumps({"status": intent["status"], "replayAllowed": False}))
        return 1
    for ref in intent["captureRefs"].values():
        if _mission_file_ref(Path(ref["path"])) != ref:
            raise GatewayError("captured custody changed before review acceptance")
    if workspace_snapshot(reservation.state) != intent["workspaceAfter"]:
        raise GatewayError("workspace changed while awaiting review; refreshed criterion proof required")
    review = _accepted_review(reservation)
    if reservation.meta["action"] == "product" and reservation.state["tasks"][reservation.meta["taskId"]]["verificationProfile"] != "V0" and review is None:
        print(json.dumps({"status": "awaiting_review", "replayAllowed": False}))
        return 0
    reservation.require_acceptance_ready(review)
    terminal = intent["terminalTemplate"]
    if acceptance_path.exists():
        if json.loads(acceptance_path.read_bytes()) != terminal:
            raise GatewayError("existing terminal acceptance differs from captured candidate")
    else:
        atomic_create(acceptance_path, (json.dumps(terminal, indent=2, sort_keys=True) + "\n").encode())
    reservation.accept(intent["verification"], acceptance_path, review)
    print(json.dumps({"status": "accepted", "path": intent["resultRef"]["path"], "replayed": False}))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    order: dict[str, Any] | None = None
    result_path: Path | None = None
    start_receipt_path: Path | None = None
    closure_path: Path | None = None
    acceptance_path: Path | None = None
    proof_path: Path | None = None
    events_path: Path | None = None
    child_started = False
    loop_lock: LoopStateLock | None = None
    loop_snapshot: LoopStateSnapshot | None = None
    reservation = None
    old_signals = {}
    try:
        if not math.isfinite(args.termination_grace_seconds) or args.termination_grace_seconds <= 0:
            raise GatewayError("--termination-grace-seconds must be a finite positive number")
        order, order_bytes = load_order(args.order)
        is_v3 = controller_context(order) is not None
        if not is_v3:
            raise GatewayError("Gateway-only active entrypoint requires policyVersion=3.0")
        try:
            _, policy = validate_order(order)
        except RunnerError as exc:
            raise GatewayError(f"order validation failed: {exc}") from exc
        try:
            verify_input_results(order, policy.repo_path)
        except AcceptedInputError as exc:
            raise GatewayError(f"accepted input verification failed before launch: {exc}") from exc
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
        acceptance_path = require_control_path(
            policy.control_namespace / "controller-acceptance.json", policy.control_namespace, "controller acceptance"
        )
        proof_path = require_control_path(
            policy.control_namespace / "controller-proof.json", policy.control_namespace, "controller proof"
        )
        if len({path for path in (result_path, candidate_path, start_receipt_path, closure_path, evidence_dir, events_path, stdout_path, stderr_path, proof_path, acceptance_path) if path is not None}) != len([path for path in (result_path, candidate_path, start_receipt_path, closure_path, evidence_dir, events_path, stdout_path, stderr_path, proof_path, acceptance_path) if path is not None]):
            raise GatewayError("controller proof and acceptance paths must be distinct from gateway outputs")
        if evidence_dir in acceptance_path.parents or evidence_dir in proof_path.parents:
            raise GatewayError("controller proof and acceptance paths must be outside evidence directory")
        if routing is not None and routing["executionProfile"] == "advisory":
            advisory_paths = validate_codex_launch(
                order["launch"]["command"], routing["model"], routing["reasoningEffort"], advisory=True
            )
            assert advisory_paths is not None
            output_path, _ = advisory_paths
            if policy.control_path(output_path, "Astra advisory --output-last-message") != candidate_path:
                raise GatewayError("Astra advisory output-last-message must match gateway candidate path")
        argv = plan_command(order)
        if is_v3:
            policy.control_cli_path(args.order, "3.0 original order")
            preflight_warnings = validate_tunnel_launch(order, policy, candidate_path, args.candidate_source, args.schema, routing)
            if order["executor"] == "claude":
                validate_claude_proxy_environment(dict(os.environ))
        try:
            _load_schema(resolve_schema_path(args.schema))
        except BuilderError as exc:
            raise GatewayError(str(exc)) from exc
        reservation = reserve_mission_dispatch(order, policy, resume_only=args.recover_report or args.recover_report_from is not None)
        def cancel_handler(signum, frame):
            reservation.cancel(f"Gateway signal {signum}")
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_signals[sig] = signal.signal(sig, cancel_handler)
        if reservation.disposition == "accepted":
            print(json.dumps({"status": "accepted", "acceptance": reservation.intent["acceptanceRef"], "replayed": False}))
            return 0
        if reservation.disposition == "open":
            if (args.recover_report or args.recover_report_from is not None) and (reservation.intent["status"] == "reportable" or _report_capture_resumable(reservation)):
                return recover_reports(reservation, args, {"result":result_path, "evidence":evidence_dir, "events":events_path,
                    "start":start_receipt_path, "closure":closure_path}, routing)
            return _resume_captured(reservation, acceptance_path)
        if reservation.disposition != "launch":
            print(json.dumps({"status": reservation.intent["status"], "replayAllowed": False}))
            return 1
        for warning in preflight_warnings:
            append_event_best_effort(events_path, "risk_warning", orderId=order["orderId"],
                approvalRef=reservation.state["authority"]["approvalRef"], **warning)
            print(f"WARNING {warning['code']}: {warning['message']}", file=sys.stderr)
        try:
            lineage_config = preflight_lineage(order, policy.repo_path)
        except LineageError as exc:
            raise GatewayError(f"lineage preflight failed: {exc}") from exc
        if lineage_config is not None:
            if not any(isinstance(proof, dict) and proof.get("required") is True for proof in order["proofCommands"]):
                raise GatewayError("lineage requires at least one required controller proof command")
            for path in (*lineage_config["artifactPaths"], *lineage_config["deletedPaths"]):
                policy.order_path(path, "order.lineage product path")
            for name in ("lineage-manifest.json", "lineage-anchor.json"):
                target = policy.control_namespace / name
                if target.exists() or target.is_symlink():
                    raise GatewayError(f"lineage output already exists before launch: {target}")
        preflight_outputs(
            result_path,
            candidate_path,
            start_receipt_path,
            closure_path,
            evidence_dir,
            events_path,
            stdout_path,
            stderr_path,
            acceptance_path,
            proof_path,
        )
        if not is_v3 and loop_contract(order) is not None:
            if events_path is None:
                raise GatewayError("--events is required for Loop V1 gateway dispatch")
            state_path = validate_loop_order(order, policy)
            loop_lock = LoopStateLock(loop_lock_path(state_path)).acquire()
            append_runner_event(events_path, "aquila_loop_state_lock_acquired", orderId=order["orderId"], statePath=str(state_path), lockPath=str(loop_lock.path))
            prepare_loop_dispatch(order, policy)
            append_runner_event(events_path, "aquila_loop_dispatch_preflight_passed", orderId=order["orderId"], phase=order["loopContract"]["phase"])
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
        child = run_child(
            argv,
            policy.repo_path,
            order["launch"]["timeoutSeconds"],
            args.termination_grace_seconds,
            detect_claude_tool_loop=order["executor"] == "claude",
            environment=executor_environment(order["executor"], dict(os.environ)) if is_v3 else None,
            reservation=reservation,
            events_path=events_path,
        )
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
        for stream in (stdout_record, stderr_record):
            stream["complete"] = not child.get("captureLimited", False) and not child["drainTimedOut"] and stream.get("captured") is True
        controller_errors = [error for error in (child.get("error"), stdout_error, stderr_error) if error]
        extraction = {"version": "CLAUDE_OUTPUT_V1", "rawSha256": stdout_record["sha256"]}
        if args.candidate_source == "stdout" and not controller_errors:
            extracted_candidate, stdout_errors = extract_stdout_candidate(child["stdout"], order, args.schema, routing, extraction)
            for warning in extraction.get("warnings", []):
                if warning not in child.get("warnings", []):
                    emit_runtime_warning(warning, events_path, reservation)
            if stdout_errors:
                controller_errors.extend(stdout_errors)
            else:
                try:
                    if extracted_candidate is None:
                        raise GatewayError("stdout candidate extraction returned no bytes without an error")
                    atomic_create(candidate_path, extracted_candidate)
                except (GatewayError, OSError) as exc:
                    controller_errors.append(f"stdout candidate materialization failed at {candidate_path}: {exc}")
        candidate, candidate_bytes = candidate_record(candidate_path)
        if candidate.get("exists") and not candidate_path.is_symlink():
            candidate_path.chmod(0o600)
        candidate["source"] = args.candidate_source
        if args.candidate_source == "stdout":
            candidate["extraction"] = extraction
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
        protocol_receipt = None
        protocol_binding = {"runId": run_id, "startReceiptPath": str(start_receipt_path),
                            "startReceiptSha256": start_receipt_sha256, "routingSha256": routing_sha256}
        if controller_errors and is_v3:
            raw = child["stdout"] if args.candidate_source == "stdout" else candidate_bytes or b""
            protocol_receipt = record_protocol_failure(
                order, order_bytes, evidence_dir, raw, controller_errors,
                complete=(stdout_record["complete"] if args.candidate_source == "stdout" else bool(candidate.get("complete", False))),
                binding=protocol_binding,
            )
            result = None
        elif controller_errors:
            failed_payload = synthetic_failed_result(
                order,
                candidate,
                [("stdout", stdout_record), ("stderr", stderr_record)],
                controller_errors,
                strict_evidence_path,
            )
            result = finalize_synthetic(args.order, order, result_path, evidence_dir, args.schema, failed_payload)
        else:
            try:
                result = finalize_candidate(args.order, candidate_path, result_path, evidence_dir, args.schema,
                                            protocol_binding=protocol_binding, expected_order_sha256=order_sha256,
                                            expected_candidate_sha256=candidate["sha256"])
            except ProtocolFailure as exc:
                protocol_receipt = exc.receipt
                controller_errors.append("candidate failed strict protocol validation")
                result = None
            except GatewayError as exc:
                if not is_v3:
                    raise
                controller_errors.append(str(exc))
                protocol_receipt = record_protocol_failure(order, order_bytes, evidence_dir, candidate_bytes or b"",
                    controller_errors, complete=bool(candidate.get("complete", False)), binding=protocol_binding)
                result = None
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
        closure_bytes = (json.dumps(closure, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if protocol_receipt is not None:
            closure["protocolFailure"] = {"path": str(protocol_receipt), "sha256": sha256_bytes(protocol_receipt.read_bytes())}
            closure_bytes = (json.dumps(closure, indent=2, sort_keys=True) + "\n").encode("utf-8")
        closure_sha256 = sha256_bytes(closure_bytes)
        atomic_create(closure_path, closure_bytes)
        if result is None:
            identity_mismatch = False
            if candidate_bytes is not None:
                parsed, parse_errors = parse_strict_candidate(candidate_bytes, "recovery identity")
                if not parse_errors and isinstance(parsed, dict):
                    identity_mismatch = any(parsed.get(key, order[key]) != order[key] for key in ("orderId", "executor"))
            if (child.get("processStopped") and not child["error"] and child["exitCode"] == 0 and not identity_mismatch
                    and candidate.get("complete") and reservation.meta["action"] == "product"):
                reservation.intent.update(status="reportable", processStopped=True, effect="observed_protocol_failure",
                    snapshot=mission_snapshot(reservation.state, [reservation.meta["taskId"]]),
                    workspaceAfter=workspace_snapshot(reservation.state), orderRef=_mission_file_ref(args.order),
                    protocolCandidateSha256=candidate["sha256"],
                    protocolRefs={key:_mission_file_ref(path) for key,path in (("order",args.order), ("start",start_receipt_path),
                        ("closure",closure_path), ("protocol",protocol_receipt), ("candidate",candidate_path))})
                reservation.state["status"] = "verifying"
                reservation.save()
                # Controller proof is observed before report-only recovery, not invented by the report model.
                recovery_proof = run_proof_commands(order, policy, reservation)
                verify_required_proof_checks(recovery_proof)
                if workspace_snapshot(reservation.state) != reservation.intent["workspaceAfter"]:
                    raise GatewayError("workspace changed during recovery proof")
                reservation.intent["recoveryProof"] = recovery_proof
                reservation.save()
            else:
                reservation.fail("protocol failure; no product replay", process_stopped=child.get("processStopped", False))
            if loop_lock is not None and events_path is not None:
                block_loop_state_after_dispatch_failure(order, policy, events_path, RunnerError("protocol failure; no product replay"))
            append_event_best_effort(events_path, "protocol_failure", orderId=order["orderId"], runId=run_id,
                                     receiptPath=str(protocol_receipt), canonicalFinalized=False)
            print(json.dumps({"status": "protocol_failure", "receiptPath": str(protocol_receipt),
                              "closurePath": str(closure_path), "canonicalFinalized": False}, sort_keys=True))
            return 124 if child["timedOut"] else 1
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
        verification: dict[str, Any] = {}
        rejection_reason: str | None = None
        if child["timedOut"]:
            rejection_reason = "executor timed out"
        elif controller_errors:
            rejection_reason = "; ".join(controller_errors)
        elif child["exitCode"] not in (0, None):
            rejection_reason = f"executor exit code {child['exitCode']}"
        elif result["status"] != "done":
            rejection_reason = f"executor result status {result['status']}"
        elif is_v3 and routing is not None and routing["executionProfile"] == "terminal_review" and result["executorExtensions"]["review"]["verdict"] != "pass":
            rejection_reason = f"review verdict {result['executorExtensions']['review']['verdict']}"
        else:
            try:
                reservation.observe_result(result, result_path, process_stopped=child.get("processStopped", False))
                verification["workspaceDiff"] = verify_workspace_diff(reservation, result)
                run_verification_gate(
                    order, result_path, events_path, policy, "verification_passed", verification,
                    event_sink=append_event_best_effort,
                    reservation=reservation,
                )
                if workspace_snapshot(reservation.state) != reservation.intent["workspaceAfter"]:
                    raise RunnerError("workspace changed during proof")
                if verification["resultSha256"] != closure["canonicalResultSha256"]:
                    raise RunnerError("canonical result changed after Gateway closure")
                if sha256_bytes(args.order.read_bytes()) != order_sha256:
                    raise RunnerError("order bytes changed after Gateway launch")
                if sha256_bytes(start_receipt_path.read_bytes()) != start_receipt_sha256:
                    raise RunnerError("start receipt changed after Gateway launch")
                if sha256_bytes(closure_path.read_bytes()) != closure_sha256:
                    raise RunnerError("closure receipt changed after Gateway finalization")
            except (RunnerError, RoutingError) as exc:
                rejection_reason = str(exc)
        # A valid, fully captured result that fails acceptance is still a known
        # effect. Persist its identity and observed workspace before rejecting
        # the intent, so a bounded correction can be issued without replaying
        # an unknown child effect. Protocol failures remain reportable/unknown.
        if (rejection_reason is not None and child.get("processStopped") and child["exitCode"] == 0
                and not child["timedOut"] and not controller_errors):
            try:
                if reservation.intent["status"] in {"dispatching", "running"}:
                    reservation.observe_result(result, result_path, process_stopped=True)
                    verification["workspaceDiff"] = verify_workspace_diff(reservation, result)
            except (RunnerError, RoutingError) as exc:
                rejection_reason = f"{rejection_reason}; rejected-result custody failed: {exc}"
        proof_receipt = {
            "version": "AQUILA_CONTROLLER_VERIFICATION_V1",
            "orderId": order["orderId"],
            "runId": run_id,
            "orderSha256": order_sha256,
            "startReceiptSha256": start_receipt_sha256,
            "closureSha256": closure_sha256,
            "canonicalResultSha256": closure["canonicalResultSha256"],
            "status": "rejected" if rejection_reason is not None else "passed",
            "scope": "post_execution_proof",
            "reason": rejection_reason,
            "observedChecks": verification,
            "completedAt": utc_now(),
        }
        proof_bytes = (json.dumps(proof_receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        proof_sha256 = sha256_bytes(proof_bytes)
        atomic_create(proof_path, proof_bytes)
        lineage_result = None
        if rejection_reason is None and lineage_config is not None:
            try:
                lineage_result = finalize_lineage(
                    order, policy.repo_path, args.order, result_path,
                    {"start": start_receipt_path, "closure": closure_path, "acceptance": proof_path},
                )
            except (LineageError, OSError) as exc:
                rejection_reason = f"lineage finalization failed: {exc}"
        if rejection_reason is None and loop_lock is not None:
            try:
                assert events_path is not None
                loop_snapshot = LoopStateSnapshot(state_path)
                update_loop_state_after_result(order, policy, result, result_path, events_path)
            except RunnerError as exc:
                if loop_snapshot is not None:
                    loop_snapshot.rollback()
                    loop_snapshot = None
                rejection_reason = str(exc)
        if rejection_reason is not None and loop_lock is not None and child_started:
            assert events_path is not None
            try:
                block_loop_state_after_dispatch_failure(order, policy, events_path, RunnerError(rejection_reason))
            except RunnerError as exc:
                rejection_reason += f"; loop state block failed: {exc}"
        if rejection_reason is None:
            try:
                verification["inputResults"] = verify_input_results(order, policy.repo_path)
                if sha256_bytes(args.order.read_bytes()) != order_sha256:
                    raise GatewayError("order changed before terminal acceptance")
                if sha256_bytes(start_receipt_path.read_bytes()) != start_receipt_sha256:
                    raise GatewayError("start receipt changed before terminal acceptance")
                if sha256_bytes(closure_path.read_bytes()) != closure_sha256:
                    raise GatewayError("closure receipt changed before terminal acceptance")
                if sha256_bytes(result_path.read_bytes()) != closure["canonicalResultSha256"]:
                    raise GatewayError("result changed before terminal acceptance")
                if sha256_bytes(proof_path.read_bytes()) != proof_sha256:
                    raise GatewayError("proof receipt changed before terminal acceptance")
                if is_v3:
                    for record, limit in ((candidate, MAX_CANDIDATE_BYTES), (stdout_record, MAX_STDOUT_BYTES), (stderr_record, MAX_STDERR_BYTES)):
                        raw, complete = read_bounded_file(Path(record["path"]), limit)
                        if not complete or sha256_bytes(raw) != record["sha256"] or len(raw) != record["bytes"]:
                            raise GatewayError("raw capture changed before terminal acceptance")
            except (GatewayError, OSError, AcceptedInputError) as exc:
                rejection_reason = str(exc)
                if loop_snapshot is not None:
                    loop_snapshot.rollback()
                    loop_snapshot = None
                if loop_lock is not None and child_started:
                    assert events_path is not None
                    block_loop_state_after_dispatch_failure(order, policy, events_path, RunnerError(rejection_reason))
        terminal_acceptance = {
            "version": "AQUILA_CONTROLLER_ACCEPTANCE_V1",
            "orderId": order["orderId"],
            "runId": run_id,
            "orderSha256": order_sha256,
            "startReceiptSha256": start_receipt_sha256,
            "closureSha256": closure_sha256,
            "canonicalResultSha256": closure["canonicalResultSha256"],
            "proofReceiptSha256": proof_sha256,
            "lineageAnchorSha256": lineage_result["anchorSha256"] if lineage_result is not None else None,
            "status": "rejected" if rejection_reason is not None else "passed",
            "reason": rejection_reason,
            "completedAt": utc_now(),
        }
        if rejection_reason is None:
            reservation.intent.update(verification=verification, terminalTemplate=terminal_acceptance,
                captureRefs={name: _mission_file_ref(path) for name, path in
                    (("order", args.order), ("start", start_receipt_path), ("closure", closure_path),
                     ("proof", proof_path), ("result", result_path), ("candidate", candidate_path),
                     ("stdout", stdout_path), ("stderr", stderr_path)) if path is not None})
            reservation.save()
            return _resume_captured(reservation, acceptance_path)
        reservation.fail("controller rejected candidate", process_stopped=child.get("processStopped", False))
        try:
            atomic_create(acceptance_path, (json.dumps(terminal_acceptance, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        except (GatewayError, OSError, AcceptedInputError):
            if loop_snapshot is not None:
                loop_snapshot.rollback()
                loop_snapshot = None
                if child_started:
                    assert events_path is not None
                    block_loop_state_after_dispatch_failure(order, policy, events_path, RunnerError("terminal acceptance write failed"))
            raise
        if loop_snapshot is not None:
            loop_snapshot.discard()
            loop_snapshot = None
        append_event_best_effort(
            events_path,
            "controller_verification_closed",
            orderId=order["orderId"],
            status="rejected" if rejection_reason is not None else "passed",
            reason=rejection_reason,
            acceptancePath=str(acceptance_path),
            lineage=lineage_result,
        )
        print(json.dumps({"status": "closed", "resultStatus": result["status"], "controllerVerification": "rejected" if rejection_reason is not None else "passed", "lineage": lineage_result, "path": str(result_path)}, sort_keys=True))
        if child["timedOut"]:
            return 124
        if controller_errors or child["exitCode"] not in (0, None):
            return 1
        if rejection_reason is not None:
            return 1 if result["status"] == "done" else 2
        return 0
    except (GatewayError, BuilderError, PreflightError, ResponseEnvelopeError, StrictJSONError, RunnerError, RoutingError, LineageError, AcceptedInputError, OSError) as exc:
        if reservation is not None and reservation.disposition == "launch" and not reservation.write_failed:
            try:
                # In this held transaction a reserved intent has not reached
                # before_spawn(). A local preflight error has no unknown effect.
                # Dispatching/running intents still require actual child proof.
                not_started = (reservation.intent.get("status") == "reserved"
                               and reservation.intent.get("effect") == "not_started"
                               and not reservation.intent.get("process"))
                reservation.fail("Gateway custody or verification failed",
                                 process_stopped=not_started or locals().get("child", {}).get("processStopped", False))
            except (RunnerError, OSError):
                pass
        if child_started and loop_lock is not None and order is not None and events_path is not None and "policy" in locals():
            try:
                block_loop_state_after_dispatch_failure(order, policy, events_path, RunnerError(str(exc)))
            except RunnerError:
                pass
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
    finally:
        for sig, handler in old_signals.items():
            signal.signal(sig, handler)
        if reservation is not None:
            reservation.close()
        if loop_lock is not None:
            loop_lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
