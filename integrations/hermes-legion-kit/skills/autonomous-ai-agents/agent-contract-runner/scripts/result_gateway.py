#!/usr/bin/env python3
"""Launch one Codex or Claude attempt and finalize its controller-owned result."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import selectors
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
from agent_artifact_namespace import ArtifactNamespaceError, require_control_path
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
        result_path = policy.control_path(result_value, "outputContract.resultPath")
        launch_result_path = policy.control_path(launch_result_value, "launch.resultJsonPath")
        candidate_path = policy.control_cli_path(candidate_arg, "CLI --candidate")
        start_receipt_path = policy.control_cli_path(start_receipt_arg, "CLI --start-receipt")
        closure_path = policy.control_cli_path(closure_arg, "CLI --closure")
        evidence_dir = policy.control_cli_path(evidence_arg, "CLI --evidence-dir")
        events_path = policy.control_cli_path(events_arg, "CLI --events") if events_arg is not None else None
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


# Three identical Read no-progress results are treated as a fail-closed loop.
CLAUDE_NO_PROGRESS_LIMIT = 3


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
                    "Claude tool loop detected after "
                    f"{CLAUDE_NO_PROGRESS_LIMIT} repeated identical tool calls returned no-progress results"
                )
        else:
            state["signature"] = signature
            state["noProgress"] = 0
    return None


def _claude_tool_history_error(events: list[dict[str, Any]]) -> str | None:
    state = _claude_tool_event_state()
    for event in events:
        error = _observe_claude_tool_event(event, state)
        if error is not None:
            return error
    return None


def _run_child_streaming(
    process: subprocess.Popen[bytes],
    timeout: int,
    grace_seconds: float,
    signal_group: Any,
) -> tuple[bytes, bytes, bool, bool, str | None, str | None]:
    selector = selectors.DefaultSelector()
    streams: dict[int, str] = {}
    chunks: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    line_buffers: dict[str, bytes] = {"stdout": b"", "stderr": b""}
    tool_state = _claude_tool_event_state()
    tool_loop_error: str | None = None
    timed_out = False
    drain_timed_out = False
    termination_signal = None

    for label, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        if stream is None:
            continue
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, label)
        streams[stream.fileno()] = label

    deadline = time.monotonic() + timeout
    drain_deadline: float | None = None
    killed = False

    def request_stop(reason: str, *, timeout_stop: bool = False) -> None:
        nonlocal termination_signal, timed_out, tool_loop_error, drain_deadline
        if timeout_stop:
            timed_out = True
        if reason.startswith("Claude tool loop"):
            tool_loop_error = reason
        if termination_signal is None:
            termination_signal = "SIGTERM"
            signal_group(signal.SIGTERM)
            drain_deadline = time.monotonic() + grace_seconds

    while streams or process.poll() is None:
        now = time.monotonic()
        if drain_deadline is None and now >= deadline:
            request_stop(f"launcher timed out after {timeout}s", timeout_stop=True)
        if drain_deadline is not None and now >= drain_deadline:
            if not killed:
                killed = True
                termination_signal = "SIGKILL"
                signal_group(signal.SIGKILL)
                drain_deadline = time.monotonic() + grace_seconds
            else:
                drain_timed_out = True
                break
        wait_for = 0.1
        if drain_deadline is None:
            wait_for = max(0.0, min(wait_for, deadline - now))
        else:
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
            except OSError:
                chunk = b""
            if not chunk:
                selector.unregister(stream)
                streams.pop(stream.fileno(), None)
                continue
            chunks[label].append(chunk)
            if label != "stdout" or tool_loop_error is not None:
                continue
            line_buffers[label] += chunk
            while b"\n" in line_buffers[label]:
                line, line_buffers[label] = line_buffers[label].split(b"\n", 1)
                try:
                    event = strict_json_load_bytes(line, "Claude stream event")
                except StrictJSONError:
                    continue
                if process.poll() is not None:
                    continue
                loop_error = _observe_claude_tool_event(event, tool_state)
                if loop_error is not None:
                    request_stop(loop_error)
                    break
    selector.close()
    if process.poll() is None:
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            signal_group(signal.SIGKILL)
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                drain_timed_out = True
    return (
        b"".join(chunks["stdout"]),
        b"".join(chunks["stderr"]),
        timed_out,
        drain_timed_out,
        termination_signal,
        tool_loop_error,
    )


def run_child(
    argv: list[str],
    cwd: Path,
    timeout: int,
    grace_seconds: float,
    *,
    detect_claude_tool_loop: bool = False,
) -> dict[str, Any]:
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
    tool_loop_error = None
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
        if detect_claude_tool_loop:
            (
                stdout,
                stderr,
                timed_out,
                drain_timed_out,
                termination_signal,
                tool_loop_error,
            ) = _run_child_streaming(process, timeout, grace_seconds, signal_group)
        else:
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
    if tool_loop_error:
        errors.append(tool_loop_error)
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


def parse_claude_transport(content: bytes) -> tuple[Any, list[str]]:
    try:
        return strict_json_load_bytes(content, "stdout candidate"), []
    except StrictJSONError as document_error:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return None, [str(document_error)]
        lines = text.splitlines()
        if len(lines) < 2:
            return None, [str(document_error)]
        events = []
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                return None, [f"stdout JSONL line {line_number} is empty"]
            try:
                event = strict_json_load_bytes(line.encode("utf-8"), f"stdout JSONL line {line_number}")
            except StrictJSONError as line_error:
                return None, [str(line_error)]
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
) -> tuple[bytes | None, list[str]]:
    transport, parse_errors = parse_claude_transport(content)
    if parse_errors:
        return None, parse_errors
    try:
        _, validator = _load_schema(resolve_schema_path(schema_path))
    except BuilderError as exc:
        raise GatewayError(str(exc)) from exc

    if isinstance(transport, dict) and "resultVersion" in transport:
        validation_errors = validate_candidate(transport, order, validator)
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

    history_error = _claude_tool_history_error(events)
    if history_error is not None:
        return None, [history_error]

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
    elif permission_denials:
        transport_errors.append("Claude terminal permission_denials must be empty")
    inner = terminal.get("result")
    if not isinstance(inner, str) or not inner.strip():
        transport_errors.append("Claude terminal result must be a non-empty JSON string")
        inner_bytes = None
    else:
        inner_bytes = inner.encode("utf-8")
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
        child = run_child(
            argv,
            policy.repo_path,
            order["launch"]["timeoutSeconds"],
            args.termination_grace_seconds,
            detect_claude_tool_loop=order["executor"] == "claude",
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
        controller_errors = [error for error in (child.get("error"), stdout_error, stderr_error) if error]
        if args.candidate_source == "stdout" and not controller_errors:
            extracted_candidate, stdout_errors = extract_stdout_candidate(child["stdout"], order, args.schema, routing)
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
