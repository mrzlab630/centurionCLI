#!/usr/bin/env python3
"""Small AGENT_ORDER_JSON_V1 runner for local Aquila/Hermes delegation."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import secrets
import select
import shlex
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from attempt_ledger import LedgerError, append_attempt, load_attempt_history
from agent_artifact_namespace import (
    ArtifactNamespaceError,
    artifact_namespace,
    require_control_path,
    require_no_symlink_components,
)
from direct_custody import CustodyError, close_direct_attempt, finalize_direct_attempt, start_direct_attempt
from review_ladder import (
    PROFILE_RANK,
    REVIEWER_BY_PROFILE,
    REVIEWER_FALLBACK_BY_PROFILE,
    RoutingError,
    validate_order_routing,
    validate_terminal_review_result,
)
from strict_json import StrictJSONError, strict_json_load_path
from accepted_inputs import AcceptedInputError, verify_input_results
from response_envelope import ResponseEnvelopeError, parse_response_bytes, validate_handoff_order, validate_response_handoff, response_state_errors, valid_media_type


ORDER_VERSION = "AGENT_ORDER_JSON_V1"
RESULT_VERSION = "AGENT_RESULT_JSON_V1"
ALLOWED_EXECUTORS = {"codex", "claude", "agy", "hermes_delegate_task", "other"}
RESULT_STATUSES = {"done", "blocked", "failed"}
FILE_ACTIONS = {"added", "modified", "deleted", "renamed", "none"}
PROOF_STATUSES = {"pass", "fail", "not_run"}
LOOP_VERSION = "AQUILA_LOOP_V1"
LOOP_STATE_VERSION = "AQUILA_LOOP_STATE_V1"
LOOP_PHASES = {"execute", "verify"}
LOOP_WORK_STATUSES = {"ready", "awaiting_verification", "blocked", "completed"}
LOOP_VERIFICATION_STATUSES = {"pending", "pass", "fail", "blocked"}
MISSION_STATE_VERSION = "CENTURION_MISSION_STATE_V1"
MISSION_POLICY = "3.0"
MISSION_TERMINAL = {"completed", "failed", "stopped"}
MISSION_OPEN_INTENTS = {"reserved", "dispatching", "running", "captured", "reportable"}
MISSION_RESERVE_SECONDS = 30
ATTEMPT_LEDGER_ENV = "AQUILA_ATTEMPT_LEDGER"
REQUIRED_ORDER_FIELDS = [
    "orderVersion",
    "orderId",
    "createdAt",
    "controller",
    "executor",
    "roleForTask",
    "riskLevel",
    "workspace",
    "launch",
    "objective",
    "context",
    "allowedPaths",
    "forbiddenPaths",
    "forbiddenActions",
    "nonGoals",
    "acceptanceCriteria",
    "expectedArtifacts",
    "proofCommands",
    "outputContract",
    "stopConditions",
    "notesForExecutor",
]
REQUIRED_RESULT_LISTS = [
    "filesChanged",
    "artifacts",
    "proof",
    "scopeDeviations",
    "forbiddenPatternHits",
    "remainingRisks",
    "questions",
    "errors",
]


class RunnerError(Exception):
    """Raised for validation or execution failures that should be reported."""


class CommandTimeoutError(RunnerError):
    """Raised when the executor times out after producing partial output."""

    def __init__(self, timeout: int, stdout: str, stderr: str) -> None:
        super().__init__(f"executor command timed out after {timeout}s")
        self.timeout = timeout
        self.stdout = stdout
        self.stderr = stderr


class CommandStartError(RunnerError):
    """Raised when no executor process could be started."""


class LoopStateLock:
    """Controller-owned nonblocking lock for one complete Loop V1 transaction."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle = None

    def acquire(self) -> "LoopStateLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd: int | None = None
        try:
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
            os.chmod(self.path, 0o600)
            self._handle = os.fdopen(fd, "r+", encoding="utf-8")
            fd = None
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            if fd is not None:
                os.close(fd)
            self.release()
            raise RunnerError(f"loop state lock is already held: {self.path}") from exc
        except OSError as exc:
            if fd is not None:
                os.close(fd)
            self.release()
            raise RunnerError(f"cannot acquire loop state lock {self.path}: {exc}") from exc
        return self

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


class LoopStateSnapshot:
    """Keep the prior inode available until the final acceptance receipt exists."""

    def __init__(self, state_path: Path) -> None:
        if state_path.is_symlink() or not state_path.is_file():
            raise RunnerError(f"loop state must be a regular file: {state_path}")
        self.state_path = state_path
        self.backup = state_path.with_name(f".{state_path.name}.pre-acceptance-{secrets.token_hex(12)}")
        try:
            os.link(state_path, self.backup, follow_symlinks=False)
        except OSError as exc:
            raise RunnerError(f"cannot snapshot loop state before acceptance: {exc}") from exc

    def rollback(self) -> None:
        try:
            os.replace(self.backup, self.state_path)
        except OSError as exc:
            raise RunnerError(f"cannot restore loop state after acceptance failure: {exc}") from exc

    def discard(self) -> None:
        try:
            self.backup.unlink(missing_ok=True)
        except OSError:
            pass


class PathPolicy:
    """Resolve order paths and enforce exact / trailing-** path rules."""

    def __init__(self, repo_path: Path, allowed_paths: list[Any], forbidden_paths: list[Any], order_id: str) -> None:
        self.repo_path = repo_path.expanduser().resolve()
        if not self.repo_path.is_dir():
            raise RunnerError(f"workspace.repoPath must be an existing directory: {self.repo_path}")
        try:
            self.control_namespace = artifact_namespace(self.repo_path, order_id)
            require_no_symlink_components(self.control_namespace)
        except ArtifactNamespaceError as exc:
            raise RunnerError(str(exc)) from exc
        self.allowed = self._compile_patterns(allowed_paths, "allowedPaths")
        self.forbidden = self._compile_patterns(forbidden_paths, "forbiddenPaths")

    def _compile_patterns(self, patterns: list[Any], label: str) -> list[tuple[str, Path]]:
        compiled = []
        for index, value in enumerate(patterns):
            if not isinstance(value, str) or not value.strip():
                raise RunnerError(f"{label}[{index}] must be a non-empty string")
            raw = value.strip()
            recursive = raw.endswith("/**")
            base = raw[:-3] if recursive else raw
            path = self.resolve_under_repo(base)
            compiled.append(("recursive" if recursive else "exact", path))
        return compiled

    def resolve_under_repo(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.repo_path / path
        return path.resolve(strict=False)

    def resolve_cli_path(self, value: str | Path) -> Path:
        return Path(value).expanduser().resolve(strict=False)

    def _matches(self, path: Path, patterns: list[tuple[str, Path]]) -> bool:
        for mode, pattern in patterns:
            if mode == "exact" and path == pattern:
                return True
            if mode == "recursive" and (path == pattern or pattern in path.parents):
                return True
        return False

    def require_allowed(self, path: Path, label: str) -> Path:
        resolved = path.resolve(strict=False)
        if self._matches(resolved, self.forbidden):
            raise RunnerError(f"{label} is forbidden by forbiddenPaths: {resolved}")
        if not self._matches(resolved, self.allowed):
            raise RunnerError(f"{label} is not covered by allowedPaths: {resolved}")
        return resolved

    def order_path(self, value: str | Path, label: str) -> Path:
        return self.require_allowed(self.resolve_under_repo(value), label)

    def cli_path(self, value: str | Path, label: str) -> Path:
        return self.require_allowed(self.resolve_cli_path(value), label)

    def control_path(self, value: str | Path, label: str) -> Path:
        path = self.require_allowed(self.resolve_under_repo(value), label)
        try:
            return require_control_path(path, self.control_namespace, label)
        except ArtifactNamespaceError as exc:
            raise RunnerError(str(exc)) from exc

    def control_cli_path(self, value: str | Path, label: str) -> Path:
        path = self.require_allowed(self.resolve_cli_path(value), label)
        try:
            return require_control_path(path, self.control_namespace, label)
        except ArtifactNamespaceError as exc:
            raise RunnerError(str(exc)) from exc


def prepare_order_namespace(policy: PathPolicy) -> Path:
    """Create and validate the controller evidence namespace before dispatch.

    Result Gateway deliberately does not call this helper: a Gateway invoked
    without controller preparation must continue to reject a missing evidence
    directory.
    """
    namespace = policy.control_namespace
    try:
        require_no_symlink_components(namespace)
        namespace.mkdir(parents=True, exist_ok=True)
        require_no_symlink_components(namespace)
        evidence = require_control_path(namespace / "evidence", namespace, "order evidence directory")
        if evidence.exists() and evidence.is_symlink():
            raise RunnerError(f"order evidence directory must not be a symlink: {evidence}")
        evidence.mkdir(exist_ok=True)
        if not evidence.is_dir():
            raise RunnerError(f"order evidence directory is not a directory: {evidence}")
        fd, probe = tempfile.mkstemp(prefix=".order-evidence-probe.", dir=evidence)
        os.close(fd)
        Path(probe).unlink(missing_ok=True)
    except (ArtifactNamespaceError, OSError) as exc:
        raise RunnerError(f"could not prepare order evidence directory: {exc}") from exc
    return evidence

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_event(events_path: Path | None, event: str, **payload: Any) -> None:
    if events_path is None:
        return
    events_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": utc_now(), "event": event, **payload}
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def append_committed_loop_event(events_path: Path, event: str, **payload: Any) -> None:
    try:
        append_event(events_path, event, **payload)
    except OSError as exc:
        print(f"warning: loop event could not be recorded: {exc}", file=sys.stderr)


def load_json(path: Path) -> Any:
    try:
        return strict_json_load_path(path, f"JSON file {path}")
    except FileNotFoundError as exc:
        raise RunnerError(f"file not found: {path}") from exc
    except StrictJSONError as exc:
        raise RunnerError(str(exc)) from exc


def load_routing_history() -> tuple[dict[str, Any], ...]:
    """Load the controller-owned attempt ledger without modifying it."""
    configured = os.environ.get(ATTEMPT_LEDGER_ENV)
    if configured is None:
        ledger_path = Path.home() / ".hermes" / "ledger" / "attempts.jsonl"
        missing_ok = True
    else:
        if not configured.strip():
            raise RunnerError(f"{ATTEMPT_LEDGER_ENV} must be a non-empty path")
        ledger_path = Path(configured).expanduser()
        missing_ok = False
    try:
        return load_attempt_history(ledger_path, missing_ok=missing_ok)
    except (OSError, LedgerError) as exc:
        raise RunnerError(f"attempt ledger load failed for {ledger_path}: {exc}") from exc


def normalize_stream(content: str | bytes | None) -> str:
    if content is None:
        return ""
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return content


def paths_equal(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def result_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise RunnerError(f"cannot hash result {path}: {exc}") from exc


def argv_summary(argv: list[str]) -> dict[str, Any]:
    return {"argv0": Path(argv[0]).name if argv else None, "argc": len(argv)}


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RunnerError(f"{label} must be a JSON object")
    return value


def require_nonempty_string(obj: dict[str, Any], key: str, label: str | None = None) -> None:
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        raise RunnerError(f"{label or key} must be a non-empty string")


def require_list(obj: dict[str, Any], key: str) -> None:
    if not isinstance(obj.get(key), list):
        raise RunnerError(f"{key} must be a list")


def require_string_value(obj: dict[str, Any], key: str, label: str) -> None:
    if not isinstance(obj.get(key), str):
        raise RunnerError(f"{label} must be a string")


def canonical_proof_argv(proof: dict[str, Any], label: str, *, required: bool) -> list[str] | None:
    """Validate argv and require one deterministic shlex canonicalization."""
    argv_value = proof.get("argv")
    if argv_value is None:
        if required:
            raise RunnerError(f"{label}.argv is required for Loop V1 proof commands")
        return None
    if not isinstance(argv_value, list) or not argv_value:
        raise RunnerError(f"{label}.argv must be a non-empty array")
    if any(not isinstance(token, str) or not token.strip() for token in argv_value):
        raise RunnerError(f"{label}.argv must contain only non-empty strings")
    try:
        parsed_command = shlex.split(proof["command"])
    except ValueError as exc:
        raise RunnerError(f"{label}.command cannot be parsed safely: {exc}") from exc
    if not parsed_command or shlex.join(parsed_command) != shlex.join(argv_value):
        raise RunnerError(f"{label}.command and {label}.argv mismatch under shlex canonicalization")
    return argv_value


def parse_reasoning_effort_scalar(raw_value: str) -> str:
    """Parse only the bounded scalar accepted by Codex routing metadata."""
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,16}", value):
        raise RunnerError("Codex model_reasoning_effort must be a bounded scalar")
    return value


def validate_codex_launch(command: str, model: str, effort: str, *, advisory: bool = False) -> tuple[str, str] | None:
    """Bind the recorded route to the CLI invocation before either dispatcher starts."""
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise RunnerError(f"launch.command cannot be parsed safely: {exc}") from exc
    exec_index = 2 if argv[1:2] == ["--no-daemon"] else 1
    if len(argv) <= exec_index or Path(argv[0]).name != "codex" or argv[exec_index] != "exec":
        raise RunnerError("Codex launch.command must start with codex exec and explicit model/effort flags")
    models: list[str] = []
    efforts: list[str] = []
    sandboxes: list[str] = []
    output_paths: list[str] = []
    working_dirs: list[str] = []
    value_options = {
        "-C", "--cd", "-s", "--sandbox", "-o", "--output-last-message",
        "--output-schema", "--color", "--thread-source", "--add-dir",
        "-i", "--image", "--enable", "--disable",
    }
    boolean_options = {
        "--strict-config", "--json", "--skip-git-repo-check", "--ephemeral",
        "--ignore-rules", "--worktree", "--approve-for-me",
        "--dangerously-bypass-approvals-and-sandbox", "--dangerously-bypass-hook-trust",
    }
    index = exec_index + 1
    while index < len(argv):
        token = argv[index]
        if token == "--":
            break
        if not token.startswith("-") or token == "-":
            index += 1  # This argv element is prompt text; later options still apply.
            continue
        name, separator, attached = token.partition("=")
        if advisory and name not in {"--model", "-m", "-c", "--config", "-s", "--sandbox", "-C", "--cd", "-o", "--output-last-message", "--output-schema", "--json"} and not token.startswith(("-m", "-c", "-s", "-C", "-o")):
            raise RunnerError(f"Astra advisory launch has an unsupported option: {token}")
        if name in {"--oss", "--local-provider", "--profile", "-p", "--ignore-user-config"} or token.startswith("-p"):
            raise RunnerError("Codex launch.command must not override the selected provider or profile")
        if token in {"--model", "-m", "-c", "--config"}:
            if index + 1 >= len(argv):
                raise RunnerError("Codex launch.command has an option without a value")
            value = argv[index + 1]
            index += 2
        elif name in {"--model", "--config"} and separator:
            value = attached
            index += 1
        elif token.startswith("-m") or token.startswith("-c"):
            name, value = token[:2], token[2:].removeprefix("=")
            index += 1
        elif token in value_options:
            if index + 1 >= len(argv):
                raise RunnerError("Codex launch.command has an option without a value")
            value = argv[index + 1]
            if advisory:
                if token in {"-s", "--sandbox"}:
                    sandboxes.append(value)
                elif token in {"-o", "--output-last-message"}:
                    output_paths.append(value)
                elif token in {"-C", "--cd"}:
                    working_dirs.append(value)
            index += 2
            continue
        elif (name in value_options and separator) or (token[:2] in {"-C", "-s", "-o", "-i"} and len(token) > 2):
            if advisory:
                value = attached if separator else token[2:]
                if name in {"-s", "--sandbox"} or token.startswith("-s"):
                    sandboxes.append(value)
                elif name in {"-o", "--output-last-message"} or token.startswith("-o"):
                    output_paths.append(value)
                elif name in {"-C", "--cd"} or token.startswith("-C"):
                    working_dirs.append(value)
            index += 1
            continue
        elif token in boolean_options:
            index += 1
            continue
        else:
            raise RunnerError(f"Codex launch.command has an unsupported option: {token}")
        if name in {"--model", "-m"}:
            models.append(value)
            continue
        key, equals, raw_value = value.partition("=")
        if not equals:
            raise RunnerError("Codex launch.command -c/--config requires key=value")
        key = key.strip().strip('"\'')
        if key in {"model", "model_provider"}:
            raise RunnerError("Codex launch.command must not override model or provider via -c")
        if advisory and key != "model_reasoning_effort":
            raise RunnerError("Astra advisory launch permits only the reasoning effort config override")
        if key == "model_reasoning_effort":
            efforts.append(parse_reasoning_effort_scalar(raw_value))
    if models != [model] or efforts != [effort]:
        raise RunnerError("Codex launch.command --model and -c model_reasoning_effort must match routing.model and routing.reasoningEffort exactly")
    if advisory:
        if sandboxes != ["read-only"]:
            raise RunnerError("Astra advisory launch requires exactly one read-only sandbox")
        if len(output_paths) != 1 or len(working_dirs) != 1:
            raise RunnerError("Astra advisory launch requires one output-last-message and one working directory")
        return output_paths[0], working_dirs[0]
    return None


def validate_gemini_launch(command: str, model: str, effort: str) -> None:
    """Bind the explicit Gemini route to agy's documented session flags."""
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise RunnerError(f"launch.command cannot be parsed safely: {exc}") from exc
    if not argv or Path(argv[0]).name != "agy":
        raise RunnerError("Gemini launch.command must start with agy")
    values = {"--model": [], "--effort": []}
    value_options = {
        "--input-format", "--output-format", "--json-schema", "--log-file",
        "--mode", "--print-timeout", "--add-dir",
    }
    print_options = {"-p", "--print", "--prompt"}
    boolean_options = {"--sandbox", "--disable-slash-commands"}
    index = 1
    while index < len(argv):
        token = argv[index]
        name, equals, attached = token.partition("=")
        if token == "--":
            break
        if not token.startswith("-"):
            index += 1
            continue
        if name in values or name in value_options or name in print_options:
            if equals:
                value = attached
            elif index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                index += 1
                value = argv[index]
            elif name in print_options:
                value = ""  # Print mode may read the bounded order from stdin.
            else:
                raise RunnerError(f"Gemini launch option {name} requires a value")
            if name in values:
                values[name].append(value)
        elif token not in boolean_options:
            raise RunnerError(f"Gemini launch has an unsupported or session-changing option: {token}")
        index += 1
    if values["--model"] != [model] or values["--effort"] != [effort]:
        raise RunnerError("Gemini launch --model and --effort must match the recorded route exactly")


def validate_claude_launch(command: str, model: str, fallback_model: str | None, effort: str | None = None) -> None:
    """Bind Claude's primary and ordered fallback models to the actual argv."""
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise RunnerError(f"launch.command cannot be parsed safely: {exc}") from exc
    if not argv or Path(argv[0]).name != "claude":
        raise RunnerError("Claude launch.command must start with claude")

    values = {"--model": [], "--fallback-model": [], "--effort": []}
    prompt_started = False
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == "--":
            break
        if prompt_started:
            break
        if not token.startswith("-") or token == "-":
            prompt_started = True
            index += 1
            continue
        name, separator, attached = token.partition("=")
        if name in values:
            if separator:
                value = attached
            elif index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                index += 1
                value = argv[index]
            else:
                raise RunnerError(f"Claude launch option {name} requires a value")
            values[name].append(value)
        index += 1

    if values["--model"] != [model]:
        raise RunnerError("Claude launch.command must contain exactly one --model matching routing.model")
    if values["--fallback-model"] != ([] if fallback_model is None else [fallback_model]):
        raise RunnerError(
            "Claude fallback must match the explicit legacy contract; active 3.0 has no fallback"
        )
    if effort is not None and values["--effort"] != [effort]:
        raise RunnerError("Claude launch.command requires exactly one --effort matching routing.reasoningEffort")


def validate_files_changed(items: list[Any], policy: PathPolicy) -> None:
    for index, item in enumerate(items):
        file_obj = require_object(item, f"filesChanged[{index}]")
        require_nonempty_string(file_obj, "path", f"filesChanged[{index}].path")
        policy.order_path(file_obj["path"], f"filesChanged[{index}].path")
        if file_obj.get("action") not in FILE_ACTIONS:
            raise RunnerError(
                f"filesChanged[{index}].action must be one of: "
                + ", ".join(sorted(FILE_ACTIONS))
            )


def validate_artifacts(items: list[Any], policy: PathPolicy, *, typed: bool = False) -> list[Path]:
    artifact_paths = []
    for index, item in enumerate(items):
        artifact_obj = require_object(item, f"artifacts[{index}]")
        require_nonempty_string(artifact_obj, "path", f"artifacts[{index}].path")
        artifact_path = policy.order_path(artifact_obj["path"], f"artifacts[{index}].path")
        artifact_paths.append(artifact_path)
        if not isinstance(artifact_obj.get("exists"), bool):
            raise RunnerError(f"artifacts[{index}].exists must be boolean")
        actual_exists = artifact_path.exists()
        if artifact_obj["exists"] != actual_exists:
            raise RunnerError(
                f"artifacts[{index}].exists artifact existence mismatch for {artifact_path}: "
                f"reported {artifact_obj['exists']}, filesystem {actual_exists}"
            )
        require_string_value(artifact_obj, "type", f"artifacts[{index}].type")
        require_string_value(artifact_obj, "note", f"artifacts[{index}].note")
        if (typed and actual_exists) or "sha256" in artifact_obj or "mediaType" in artifact_obj:
            digest, media_type = artifact_obj.get("sha256"), artifact_obj.get("mediaType")
            if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise RunnerError("RESPONSE_SCHEMA_ERROR: artifact.sha256 must be a lowercase SHA-256 digest")
            if not valid_media_type(media_type):
                raise RunnerError("RESPONSE_SCHEMA_ERROR: artifact.mediaType must be a media type")
            source = Path(artifact_obj["path"]).expanduser()
            if not source.is_absolute():
                source = policy.repo_path / source
            if any(component.is_symlink() for component in (source, *source.parents)):
                raise RunnerError("RESPONSE_SCHEMA_ERROR: typed artifact contains a symlink")
            if not artifact_path.is_file() or hashlib.sha256(artifact_path.read_bytes()).hexdigest() != digest:
                raise RunnerError("RESPONSE_SCHEMA_ERROR: typed artifact SHA-256 mismatch")
    return artifact_paths


def validate_response_envelope(result: dict[str, Any], policy: PathPolicy, order: dict[str, Any]) -> None:
    """Validate controller-owned raw/normalized response binding when present."""
    if "responseEnvelope" not in result:
        return
    envelope_obj = require_object(result["responseEnvelope"], "responseEnvelope")
    if set(envelope_obj) != {"version", "transport", "rawEvidencePath", "rawSha256", "rawBytes", "normalizedCandidatePath", "normalizedSha256", "normalizedBytes"}:
        raise RunnerError("RESPONSE_SCHEMA_ERROR: responseEnvelope has invalid fields")
    if envelope_obj.get("version") != "AGENT_RESPONSE_ENVELOPE_V1":
        raise RunnerError("responseEnvelope.version must be AGENT_RESPONSE_ENVELOPE_V1")
    if envelope_obj.get("transport") not in ("raw_json", "json_fence"):
        raise RunnerError("responseEnvelope.transport is invalid")
    contents = []
    for field in ("rawEvidencePath", "normalizedCandidatePath"):
        require_nonempty_string(envelope_obj, field, f"responseEnvelope.{field}")
        path = Path(envelope_obj[field]).expanduser()
        if not path.is_absolute():
            raise RunnerError(f"responseEnvelope.{field} must be an absolute path")
        if any(component.is_symlink() for component in (path, *path.parents)):
            raise RunnerError(f"responseEnvelope.{field} contains a symlink")
        try:
            require_control_path(path, policy.control_namespace, f"responseEnvelope.{field}")
        except ArtifactNamespaceError as exc:
            raise RunnerError(str(exc)) from exc
        if not path.is_file() or path.is_symlink():
            raise RunnerError(f"responseEnvelope.{field} must be a regular file")
        contents.append(path.read_bytes())
    for field in ("rawSha256", "normalizedSha256"):
        value = envelope_obj.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise RunnerError(f"responseEnvelope.{field} must be a lowercase SHA-256 digest")
    for content, prefix in zip(contents, ("raw", "normalized")):
        if type(envelope_obj[prefix + "Bytes"]) is not int or len(content) != envelope_obj[prefix + "Bytes"]:
            raise RunnerError(f"responseEnvelope {prefix} byte count mismatch")
        if hashlib.sha256(content).hexdigest() != envelope_obj[prefix + "Sha256"]:
            raise RunnerError(f"responseEnvelope {prefix} evidence digest mismatch")
    try:
        parsed = parse_response_bytes(contents[0], allowed_transports=order["outputContract"].get("acceptedTransports"))
    except ResponseEnvelopeError as exc:
        raise RunnerError(str(exc)) from exc
    if parsed.transport != envelope_obj["transport"] or parsed.normalized_bytes != contents[1]:
        raise RunnerError("responseEnvelope raw-to-normalized binding mismatch")
    payload = {key: value for key, value in result.items() if key != "responseEnvelope"}
    if json.dumps(parsed.value, sort_keys=True) != json.dumps(payload, sort_keys=True):
        raise RunnerError("responseEnvelope candidate-to-result binding mismatch")


def validate_proof(items: list[Any]) -> None:
    for index, item in enumerate(items):
        proof_obj = require_object(item, f"proof[{index}]")
        require_nonempty_string(proof_obj, "command", f"proof[{index}].command")
        require_nonempty_string(proof_obj, "cwd", f"proof[{index}].cwd")
        if proof_obj.get("status") not in PROOF_STATUSES:
            raise RunnerError(
                f"proof[{index}].status must be one of: "
                + ", ".join(sorted(PROOF_STATUSES))
            )
        exit_code = proof_obj.get("exitCode")
        if type(exit_code) is not int and exit_code is not None:
            raise RunnerError(f"proof[{index}].exitCode must be integer or null")
        if proof_obj["status"] == "pass" and (type(exit_code) is not int or exit_code != 0):
            raise RunnerError(f"proof[{index}].status=pass requires exitCode=0")
        require_string_value(proof_obj, "summary", f"proof[{index}].summary")


def validate_done_semantics(result: dict[str, Any]) -> None:
    """Require terminal done results to carry complete, successful acceptance evidence."""
    if result.get("status") != "done":
        return
    proof = result.get("proof")
    if not isinstance(proof, list) or not proof:
        raise RunnerError("done result requires at least one proof entry")
    if any(not isinstance(item, dict) or item.get("status") != "pass" or type(item.get("exitCode")) is not int or item.get("exitCode") != 0 for item in proof):
        raise RunnerError("done result requires every proof[].status=pass with exitCode=0")
    self_review = result.get("selfReview")
    if not isinstance(self_review, dict) or self_review.get("performed") is not True:
        raise RunnerError("done result requires selfReview.performed=true")
    for field in ("scopeDeviations", "forbiddenPatternHits"):
        if result.get(field):
            raise RunnerError(f"done result must not include {field}")


def require_order_lists(order: dict[str, Any]) -> None:
    for key in [
        "context",
        "allowedPaths",
        "forbiddenPaths",
        "forbiddenActions",
        "nonGoals",
        "acceptanceCriteria",
        "expectedArtifacts",
        "proofCommands",
        "stopConditions",
        "notesForExecutor",
    ]:
        require_list(order, key)


def validate_order(order: dict[str, Any]) -> tuple[list[str], PathPolicy]:
    missing = [field for field in REQUIRED_ORDER_FIELDS if field not in order]
    if missing:
        raise RunnerError(f"order missing required fields: {', '.join(missing)}")

    if order["orderVersion"] != ORDER_VERSION:
        raise RunnerError(f"orderVersion must be {ORDER_VERSION}")
    if order["controller"] != "Aquila":
        raise RunnerError("controller must be Aquila")
    if order["executor"] not in ALLOWED_EXECUTORS:
        raise RunnerError("executor must be one of: " + ", ".join(sorted(ALLOWED_EXECUTORS)))
    if order["executor"] == "other" and os.environ.get("AGENT_CONTRACT_RUNNER_ALLOW_OTHER") != "1":
        raise RunnerError("executor other requires AGENT_CONTRACT_RUNNER_ALLOW_OTHER=1")
    if order["riskLevel"] not in {"low", "medium", "high"}:
        raise RunnerError("riskLevel must be low, medium, or high")

    try:
        from agent_artifact_namespace import validate_order_id
        validate_order_id(order["orderId"])
    except ArtifactNamespaceError as exc:
        raise RunnerError(str(exc)) from exc

    for key in ["orderId", "createdAt", "roleForTask", "objective"]:
        require_nonempty_string(order, key)
    require_order_lists(order)
    mission = mission_context(order)
    if mission is not None:
        if not isinstance(order.get("loopContract"), dict):
            raise RunnerError("policy 3.0 orders require loopContract.statePath")
        if order["loopContract"].get("loopId") != mission["missionId"]:
            raise RunnerError("mission loopContract.loopId must match missionId")

    workspace = require_object(order["workspace"], "workspace")
    for key in ["repoPath", "branchOrWorktree", "projectName"]:
        require_nonempty_string(workspace, key, f"workspace.{key}")
    policy = PathPolicy(Path(workspace["repoPath"]), order["allowedPaths"], order["forbiddenPaths"], order["orderId"])

    launch = require_object(order["launch"], "launch")
    for key in ["surface", "command", "resultJsonPath"]:
        require_nonempty_string(launch, key, f"launch.{key}")
    timeout = launch.get("timeoutSeconds")
    if "timeoutSeconds" not in launch or (timeout is None and mission is None) or (timeout is not None and (type(timeout) is not int or timeout < 1)):
        raise RunnerError("launch.timeoutSeconds must be a positive integer or explicit null for policy 3.0 monitored execution")
    policy.control_path(launch["resultJsonPath"], "launch.resultJsonPath")
    for key in ["stdoutPath", "stderrPath"]:
        if key in launch:
            if not isinstance(launch.get(key), str) or not launch[key].strip():
                raise RunnerError(f"launch.{key} must be a non-empty string when present")
            policy.control_path(launch[key], f"launch.{key}")
    if "candidateJsonPath" in launch:
        require_nonempty_string(launch, "candidateJsonPath", "launch.candidateJsonPath")
        policy.control_path(launch["candidateJsonPath"], "launch.candidateJsonPath")

    output_contract = require_object(order["outputContract"], "outputContract")
    if output_contract.get("resultVersion") != RESULT_VERSION:
        raise RunnerError(f"outputContract.resultVersion must be {RESULT_VERSION}")
    require_nonempty_string(output_contract, "resultPath", "outputContract.resultPath")
    policy.control_path(output_contract["resultPath"], "outputContract.resultPath")
    if not isinstance(output_contract.get("stdoutAllowed"), bool):
        raise RunnerError("outputContract.stdoutAllowed must be boolean")
    if "proseAllowedAfterJson" not in output_contract:
        raise RunnerError("outputContract must include proseAllowedAfterJson")
    if not isinstance(output_contract["proseAllowedAfterJson"], bool):
        raise RunnerError("outputContract.proseAllowedAfterJson must be boolean")
    accepted_transports = output_contract.get("acceptedTransports")
    if accepted_transports is not None:
        if not isinstance(accepted_transports, list) or not accepted_transports or any(
            not isinstance(item, str) or item not in {"raw_json", "json_fence"} for item in accepted_transports
        ):
            raise RunnerError("outputContract.acceptedTransports must contain raw_json and/or json_fence")
    try:
        routing_for_handoff = validate_order_routing(order)
    except RoutingError as exc:
        raise RunnerError(f"routing validation failed: {exc}") from exc
    handoff_errors = validate_handoff_order(order, routing_for_handoff)
    if handoff_errors:
        raise RunnerError("; ".join(handoff_errors))

    if not order["acceptanceCriteria"]:
        raise RunnerError("acceptanceCriteria must not be empty")

    for index, artifact in enumerate(order["expectedArtifacts"]):
        artifact_obj = require_object(artifact, f"expectedArtifacts[{index}]")
        require_nonempty_string(artifact_obj, "path", f"expectedArtifacts[{index}].path")
        policy.order_path(artifact_obj["path"], f"expectedArtifacts[{index}].path")
        require_nonempty_string(artifact_obj, "type", f"expectedArtifacts[{index}].type")
        if not isinstance(artifact_obj.get("required"), bool):
            raise RunnerError(f"expectedArtifacts[{index}].required must be boolean")

    loop_order = "loopContract" in order
    for index, proof in enumerate(order["proofCommands"]):
        proof_obj = require_object(proof, f"proofCommands[{index}]")
        require_nonempty_string(proof_obj, "command", f"proofCommands[{index}].command")
        require_nonempty_string(proof_obj, "cwd", f"proofCommands[{index}].cwd")
        cwd = _mission_path({"workspace":str(policy.repo_path)}, proof_obj["cwd"]) if mission is not None else policy.order_path(proof_obj["cwd"], f"proofCommands[{index}].cwd")
        if not cwd.is_dir():
            raise RunnerError(f"proofCommands[{index}].cwd must be an existing directory: {cwd}")
        if not isinstance(proof_obj.get("required"), bool):
            raise RunnerError(f"proofCommands[{index}].required must be boolean")
        canonical_proof_argv(proof_obj, f"proofCommands[{index}]", required=loop_order)

    notes = ["built_in_order_validation_passed"]
    try:
        routing = validate_order_routing(order)
        if routing is not None:
            history = load_routing_history()
            routing = validate_order_routing(order, history)
            notes.append(f"aquila_attempt_history_loaded:{len(history)}")
    except RoutingError as exc:
        raise RunnerError(f"routing validation failed: {exc}") from exc
    if routing is not None:
        if routing["model"] == "gemini-3.8-flash":
            validate_gemini_launch(launch["command"], routing["model"], routing["reasoningEffort"])
        if order["executor"] == "claude":
            validate_claude_launch(
                launch["command"],
                routing["model"],
                None if mission is not None else REVIEWER_FALLBACK_BY_PROFILE.get(routing["verificationProfile"]),
                routing["reasoningEffort"] if mission is not None else None,
            )
        if order["executor"] == "codex":
            advisory = routing["executionProfile"] == "advisory"
            advisory_paths = validate_codex_launch(launch["command"], routing["model"], routing["reasoningEffort"], advisory=advisory)
            if advisory:
                assert advisory_paths is not None
                output_path, working_dir = advisory_paths
                policy.control_path(output_path, "Astra advisory --output-last-message")
                if "loopContract" in order and mission is None:
                    raise RunnerError("Astra advisory cannot own a product implementation loop")
                if order["proofCommands"]:
                    raise RunnerError("Astra advisory cannot run controller proof commands")
                if policy.resolve_under_repo(working_dir) != policy.repo_path:
                    raise RunnerError("Astra advisory working directory must match workspace.repoPath")
                for index, (_, allowed_path) in enumerate(policy.allowed):
                    if allowed_path != policy.control_namespace:
                        policy.control_path(allowed_path, f"Astra advisory allowedPaths[{index}]")
                for index, artifact in enumerate(order["expectedArtifacts"]):
                    policy.control_path(artifact["path"], f"Astra advisory expectedArtifacts[{index}]")
        notes.append(
            "aquila_routing_validated:"
            f"{routing['verificationProfile']}:{routing['reviewer']}:{routing['executionProfile']}"
        )
    elif mission is not None:
        raise RunnerError("policy 3.0 requires explicit canonical routing; no legacy fallback")
    if "loopContract" in order:
        if routing is not None and mission is None:
            phase = require_object(order["loopContract"], "loopContract").get("phase")
            expected_execution_profile = "terminal_review" if phase == "verify" else "implementation"
            if routing["executionProfile"] != expected_execution_profile:
                raise RunnerError(
                    f"loop {phase} phase requires routing.executionProfile={expected_execution_profile}"
                )
        validate_loop_order(order, policy)
        notes.append("aquila_loop_v1_semantics_passed")
    return notes, policy


def loop_contract(order: dict[str, Any]) -> dict[str, Any] | None:
    value = order.get("loopContract")
    return value if isinstance(value, dict) else None


def validate_loop_order(order: dict[str, Any], policy: PathPolicy) -> Path:
    contract = loop_contract(order)
    if contract is None:
        raise RunnerError("loopContract must be an object")
    if mission_context(order) is not None:
        # 3.0 owns mission/task/attempt counters in its explicitly versioned
        # state, not duplicated Loop V1 workItem/iteration/candidate fields.
        require_nonempty_string(contract, "statePath", "loopContract.statePath")
        path = _mission_path({"workspace": str(policy.repo_path)}, contract["statePath"])
        if any(policy._matches(target, policy.allowed) or policy._matches(target, policy.forbidden)
               for target in (path, loop_lock_path(path))):
            raise RunnerError("mission state/lock must be outside executor allowedPaths and controller forbiddenPaths")
        return path
    if contract.get("version") != LOOP_VERSION:
        raise RunnerError(f"loopContract.version must be {LOOP_VERSION}")
    if contract.get("controller") != "Aquila":
        raise RunnerError("loopContract.controller must be Aquila")
    if contract.get("phase") not in LOOP_PHASES:
        raise RunnerError("loopContract.phase must be execute or verify")
    for key in ["loopId", "statePath"]:
        if not isinstance(contract.get(key), str) or not contract[key].strip():
            raise RunnerError(f"loopContract.{key} must be a non-empty string")
    work = require_object(contract.get("workItem"), "loopContract.workItem")
    for key in ["workItemId", "project", "objective"]:
        require_nonempty_string(work, key, f"loopContract.workItem.{key}")
    iteration = require_object(contract.get("iteration"), "loopContract.iteration")
    for key in ["current", "max"]:
        if not isinstance(iteration.get(key), int) or iteration[key] < 1:
            raise RunnerError(f"loopContract.iteration.{key} must be a positive integer")
    if iteration["current"] > iteration["max"]:
        raise RunnerError("loopContract.iteration.current cannot exceed max")
    budgets = require_object(contract.get("budgets"), "loopContract.budgets")
    if not isinstance(budgets.get("maxWallSeconds"), int) or budgets["maxWallSeconds"] < 1:
        raise RunnerError("loopContract.budgets.maxWallSeconds must be a positive integer")
    for key in ["executorStateWrites", "scheduleNextIteration", "selfApprove"]:
        if contract.get(key) is not False:
            raise RunnerError(f"loopContract.{key} must be false")
    state_path = policy.resolve_under_repo(contract["statePath"])
    if policy._matches(state_path, policy.allowed):
        raise RunnerError("loopContract.statePath must be outside executor allowedPaths")
    if policy._matches(state_path, policy.forbidden):
        raise RunnerError("loopContract.statePath must not be forbidden to the controller")
    lock_path = state_path.with_name(state_path.name + ".lock")
    if policy._matches(lock_path, policy.allowed):
        raise RunnerError("loop state lock path must be outside executor allowedPaths")
    if policy._matches(lock_path, policy.forbidden):
        raise RunnerError("loop state lock path must not be forbidden to the controller")
    if contract["phase"] == "verify":
        candidate = require_object(contract.get("candidate"), "loopContract.candidate")
        for key in ["orderId", "executor", "resultPath"]:
            require_nonempty_string(candidate, key, f"loopContract.candidate.{key}")
        verification = require_object(contract.get("verification"), "loopContract.verification")
        if verification.get("blind") is not True:
            raise RunnerError("loopContract.verification.blind must be true")
        if verification.get("candidateOrderId") != candidate["orderId"] or verification.get("candidateExecutor") != candidate["executor"]:
            raise RunnerError("loopContract verification candidate identity must match candidate")
        if order["executor"] == candidate["executor"]:
            raise RunnerError("verifier executor must differ from candidate executor")
    return state_path


def loop_lock_path(state_path: Path) -> Path:
    return state_path.with_name(state_path.name + ".lock")


def validate_loop_state(state: dict[str, Any], contract: dict[str, Any], state_path: Path) -> None:
    if state.get("stateVersion") != LOOP_STATE_VERSION:
        raise RunnerError(f"stateVersion must be {LOOP_STATE_VERSION}")
    if state.get("controller") != "Aquila":
        raise RunnerError("loop state controller must be Aquila")
    if state.get("loopId") != contract["loopId"]:
        raise RunnerError("loop/state loopId mismatch")
    if state.get("project") != contract["workItem"]["project"]:
        raise RunnerError("loop/state project mismatch")
    if Path(state.get("statePath", "")).expanduser().resolve(strict=False) != state_path:
        raise RunnerError("loop/state statePath mismatch")
    work = require_object(state.get("workItem"), "loop state workItem")
    if work.get("workItemId") != contract["workItem"]["workItemId"] or work.get("objective") != contract["workItem"]["objective"]:
        raise RunnerError("loop/state work item mismatch")
    iteration = require_object(state.get("iteration"), "loop state iteration")
    if iteration.get("current") != contract["iteration"]["current"] or iteration.get("max") != contract["iteration"]["max"]:
        raise RunnerError("loop/state iteration mismatch")
    budgets = require_object(state.get("budgets"), "loop state budgets")
    if budgets.get("maxWallSeconds") != contract["budgets"]["maxWallSeconds"]:
        raise RunnerError("loop/state maxWallSeconds mismatch")
    if work.get("status") not in LOOP_WORK_STATUSES:
        raise RunnerError("loop state workItem.status is invalid")
    verification = require_object(state.get("verification"), "loop state verification")
    if verification.get("status") not in LOOP_VERIFICATION_STATUSES:
        raise RunnerError("loop state verification.status is invalid")
    if not isinstance(state.get("failures"), list) or not isinstance(state.get("transitions"), list):
        raise RunnerError("loop state failures and transitions must be lists")


def load_loop_state(order: dict[str, Any], policy: PathPolicy) -> tuple[dict[str, Any], Path]:
    contract = loop_contract(order)
    assert contract is not None
    state_path = validate_loop_order(order, policy)
    state = require_object(load_json(state_path), "loop state")
    validate_loop_state(state, contract, state_path)
    return state, state_path


def atomic_write_loop_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    mode = state_path.stat().st_mode & 0o777 if state_path.exists() else 0o600
    fd, temp_name = tempfile.mkstemp(prefix=f".{state_path.name}.", dir=str(state_path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, state_path)
        directory_fd = os.open(state_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def mission_context(order: dict[str, Any], *, required: bool = False) -> dict[str, Any] | None:
    """Controller metadata, never inferred from executor text or routing policy."""
    from order_preflight import controller_context, PreflightError
    try:
        meta = controller_context(order, required=required)
    except PreflightError as exc:
        raise RunnerError(str(exc)) from exc
    if meta is None:
        return None
    for key in ("missionId", "approvalRef", "taskId", "intentId", "action", "strategyId"):
        require_nonempty_string(meta, key, f"mission context.{key}")
    if meta["action"] not in {"product", "review", "advisory", "report"}:
        raise RunnerError("unknown mission action")
    require_object(meta.get("dependencyRevisions"), "mission context.dependencyRevisions")
    return meta


def _mission_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _mission_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise RunnerError("mission timestamp must be a timezone-bearing string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise RunnerError(f"invalid mission timestamp: {exc}") from exc


def _mission_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise RunnerError(f"{label} must be an integer >= {minimum}")
    return value


def _mission_strings(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise RunnerError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise RunnerError(f"{label} contains duplicates")
    return value


def _mission_path(state: dict[str, Any], value: str) -> Path:
    root = Path(state["workspace"]).resolve()
    raw = Path(value)
    path = raw if raw.is_absolute() else root / raw
    try:
        require_no_symlink_components(path)
    except ArtifactNamespaceError as exc:
        raise RunnerError(str(exc)) from exc
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise RunnerError("mission path escapes workspace")
    return resolved


def _mission_path_subset(state: dict[str, Any], requested: list[str], approved: list[str]) -> bool:
    def rule(value: str) -> tuple[Path, bool]:
        recursive = value.endswith("/**")
        base = value[:-3] if recursive else value
        if any(c in base for c in "*?[") or ".." in Path(base).parts:
            raise RunnerError("mission paths support only exact paths and trailing /**")
        return _mission_path(state, base), recursive
    parents = [rule(value) for value in approved]
    for value in requested:
        path, recursive = rule(value)
        if not any((path == parent and (wide or not recursive)) or (wide and parent in path.parents)
                   for parent, wide in parents):
            return False
    return True


def validate_mission_state(state: dict[str, Any], state_path: Path) -> None:
    if state.get("stateVersion") != MISSION_STATE_VERSION or state.get("policyVersion") != MISSION_POLICY:
        raise RunnerError("not an explicitly prepared 3.0 mission state; migration is never implicit")
    if state.get("controller") != "Aquila" or state.get("statePath") != str(state_path):
        raise RunnerError("mission controller/statePath mismatch")
    for key in ("missionId", "workspace", "strategyId"):
        require_nonempty_string(state, key)
    if state.get("status") not in {"ready", "running", "verifying", "blocked", *MISSION_TERMINAL}:
        raise RunnerError("invalid mission status")
    if type(state.get("cancelled")) is not bool:
        raise RunnerError("mission cancelled must be boolean")
    authority = require_object(state.get("authority"), "mission authority")
    for key in ("approvalRef", "goal"):
        require_nonempty_string(authority, key)
    for key in ("nonGoals", "criteria", "allowedActions", "allowedPaths", "forbiddenPaths"):
        _mission_strings(authority.get(key), f"authority.{key}", nonempty=key in {"criteria", "allowedActions", "allowedPaths"})
    if state.get("authoritySha256") != _mission_digest(authority):
        raise RunnerError("mission authority binding changed")
    budget = require_object(state.get("budget"), "mission budget")
    require_nonempty_string(budget, "startedAt", "mission budget.startedAt")
    started_at = _mission_time(budget["startedAt"])
    if "deadlineAt" not in budget:
        raise RunnerError("mission budget.deadlineAt must be explicit (timestamp or null)")
    deadline = _mission_time(budget["deadlineAt"]) if budget["deadlineAt"] is not None else None
    used = _mission_int(budget.get("modelLaunchesUsed"), "modelLaunchesUsed")
    maximum = _mission_int(budget.get("maxModelLaunches"), "maxModelLaunches", 1)
    _mission_int(budget.get("reportLaunchReserve", 0), "reportLaunchReserve")
    if used > maximum or (deadline is not None and deadline <= started_at + timedelta(seconds=30)):
        raise RunnerError("invalid mission budget/deadline")
    if state.get("stopDeadlineAt") and deadline is not None and _mission_time(state["stopDeadlineAt"]) > deadline:
        raise RunnerError("termination reserve cannot extend the original mission deadline")
    if state.get("stopDeadlineAt"):
        _mission_time(state["stopDeadlineAt"])
    if state["cancelled"] and state["status"] != "stopped":
        raise RunnerError("cancelled mission must remain stopped")
    _mission_int(state.get("strategySwitchesUsed"), "strategySwitchesUsed")
    if state["strategySwitchesUsed"] > 1:
        raise RunnerError("only one strategy switch is allowed")
    tasks = require_object(state.get("tasks"), "mission tasks")
    intents = require_object(state.get("intents"), "mission intents")
    completion_actions = authority.get("taskCompletionActions")
    if completion_actions is not None and (not isinstance(completion_actions, dict) or set(completion_actions) != set(tasks)):
        raise RunnerError("task completion action coverage changed")
    require_list(state, "observations")
    if used != sum(intent.get("modelLaunch", True) is True for intent in intents.values()):
        raise RunnerError("launch counters disagree with persisted intents")
    covered: set[str] = set()
    for task_id, task in tasks.items():
        require_object(task, "mission task")
        require_nonempty_string(task, "objective")
        completion_action = task.get("completionAction", "product")
        if completion_action not in ("product", "advisory"):
            raise RunnerError("task completionAction must be product or advisory")
        if completion_action != (completion_actions.get(task_id) if completion_actions is not None else "product"):
            raise RunnerError("task completion action binding changed")
        if completion_action not in authority["allowedActions"]:
            raise RunnerError("task completion action lacks mission authority")
        for key in ("acceptanceCriteria", "allowedPaths", "productPaths", "dependencies"):
            _mission_strings(task.get(key), f"task.{key}", nonempty=key in {"acceptanceCriteria", "allowedPaths", "productPaths"})
        covered.update(task["acceptanceCriteria"])
        if not set(task["acceptanceCriteria"]).issubset(authority["criteria"]):
            raise RunnerError("task criteria expand mission")
        if not _mission_path_subset(state, task["allowedPaths"], authority["allowedPaths"]) or not _mission_path_subset(state, task["productPaths"], task["allowedPaths"]):
            raise RunnerError("task paths expand authority")
        for path in task["productPaths"]:
            if path.endswith("/**"):
                raise RunnerError("productPaths must enumerate final product files")
            if authority["forbiddenPaths"] and _mission_path_subset(state, [path], authority["forbiddenPaths"]):
                raise RunnerError("required product path is forbidden")
        if any(dep not in tasks or dep == task_id for dep in task["dependencies"]):
            raise RunnerError("unknown or self task dependency")
        if task.get("verificationProfile") not in {"V0", "V1", "V2", "V3"}:
            raise RunnerError("task verification profile is required")
        if task.get("status") not in {"ready", "running", "verifying", "accepted"}:
            raise RunnerError("invalid task status")
        acceptance = task.get("acceptance")
        if task["status"] == "accepted":
            acceptance = require_object(acceptance, "task acceptance")
            accepted_intent = intents.get(acceptance.get("intentId"))
            if (not isinstance(accepted_intent, dict) or accepted_intent.get("status") != "accepted" or
                    accepted_intent.get("action") != completion_action or accepted_intent.get("taskId") != task_id or
                    acceptance.get("criteria") != task["acceptanceCriteria"] or
                    acceptance.get("snapshotSha256") != accepted_intent.get("snapshot", {}).get("sha256") or
                    acceptance.get("revision") != acceptance.get("snapshotSha256")):
                raise RunnerError("task acceptance is not bound to its declared completion action")
        elif acceptance is not None:
            raise RunnerError("unaccepted task cannot carry acceptance")
        count = _mission_int(task.get("productAttemptsUsed"), "task.productAttemptsUsed")
        limit = _mission_int(task.get("maxProductAttempts"), "task.maxProductAttempts", 1)
        if count > limit or count != sum(i.get("taskId") == task_id and i.get("action") == "product" for i in intents.values()):
            raise RunnerError("product attempt counter disagrees with intents")
        require_list(task, "requiredProof")
        require_list(task, "expectedArtifacts")
        if not task["requiredProof"]:
            raise RunnerError("task requires controller proof")
        for proof in task["requiredProof"]:
            if not isinstance(proof, dict) or proof.get("required") is not True:
                raise RunnerError("task requiredProof must be required")
            canonical_proof_argv(proof, "task.requiredProof", required=True)
            if not _mission_path(state, proof["cwd"]).is_dir():
                raise RunnerError("proof cwd must be an existing workspace directory")
    if covered != set(authority["criteria"]) or not tasks:
        raise RunnerError("all mission criteria must retain task coverage")
    def walk(task_id: str, visiting: set[str]) -> None:
        if task_id in visiting:
            raise RunnerError("cyclic task dependencies")
        for dep in tasks[task_id]["dependencies"]:
            walk(dep, visiting | {task_id})
    for task_id in tasks:
        walk(task_id, set())
    for intent_id, intent in intents.items():
        require_object(intent, "mission intent")
        if intent.get("intentId") != intent_id or intent.get("taskId") not in tasks:
            raise RunnerError("invalid intent identity")
        if intent.get("action") not in {"product", "review", "advisory", "report"} or intent.get("status") not in {*MISSION_OPEN_INTENTS, "accepted", "rejected", "unknown_effect"}:
            raise RunnerError("invalid intent action/status")
        _mission_int(intent.get("reportAttemptsUsed"), "reportAttemptsUsed")
        if type(intent.get("modelLaunch", True)) is not bool or (
                intent.get("modelLaunch") is False and
                (intent.get("action") != "report" or not intent.get("manualReviewRef"))):
            raise RunnerError("only an authorized manual report may omit a model launch")
        if intent["action"] == "product" and intent["reportAttemptsUsed"] != sum(
                child.get("action") == "report" and child.get("originalIntentId") == intent_id
                for child in intents.values()):
            raise RunnerError("report attempt counter disagrees with persisted intents")
        if intent["status"] in {"captured", "accepted"}:
            if intent.get("processStopped") is not True or intent.get("effect") != "observed":
                raise RunnerError("captured/accepted intent requires observed effect and stopped process")
            ref = require_object(intent.get("resultRef"), "intent result reference")
            if _mission_file_ref(Path(ref["path"])) != ref:
                raise RunnerError("captured result reference bytes changed")
        if intent["status"] == "accepted":
            _check_mission_refs(intent)
    if state["status"] == "completed" and (any(t["status"] != "accepted" for t in tasks.values()) or
            any(i["status"] in {*MISSION_OPEN_INTENTS, "unknown_effect"} for i in intents.values()) or
            any(_mission_process_identity(p["pid"]) == p for i in intents.values() for p in i.get("proofProcesses", [])) or not state.get("completion")):
        raise RunnerError("completed mission has unaccepted criteria/open effects or missing final proof")


def initialize_mission(spec: dict[str, Any], state_path: Path) -> dict[str, Any]:
    """Explicit controller preparation only; never used by resume or dispatch."""
    state_path = state_path.absolute()
    if spec:
        require_nonempty_string(spec, "workspace", "mission workspace")
        state_path = _mission_path({"workspace": spec["workspace"]}, str(state_path))
    try:
        require_no_symlink_components(state_path)
    except ArtifactNamespaceError as exc:
        raise RunnerError(str(exc)) from exc
    lock = LoopStateLock(loop_lock_path(state_path)).acquire()
    try:
        if state_path.exists() or state_path.is_symlink():
            raise RunnerError("mission state already exists; no reset or implicit migration")
        if spec.get("policyVersion") != MISSION_POLICY:
            raise RunnerError("new approved mission must explicitly select policyVersion=3.0")
        state = copy.deepcopy(spec)
        for key in ("status", "intents", "observations", "modelLaunchesUsed", "stateVersion"):
            if key in spec:
                raise RunnerError(f"mission preparation cannot import mutable field {key}")
        state.update(stateVersion=MISSION_STATE_VERSION, controller="Aquila", statePath=str(state_path),
                     status="ready", intents={}, observations=[], cancelled=False, strategySwitchesUsed=0)
        state["workspace"] = str(Path(state["workspace"]).resolve())
        if not Path(state["workspace"]).is_dir():
            raise RunnerError("mission workspace does not exist")
        if "modelLaunchesUsed" in state["budget"]:
            raise RunnerError("mission preparation cannot reset imported launch counters")
        # Only explicit preparation gets the new default; loading old state
        # never changes an approved deadline or migrates historical receipts.
        state["budget"].setdefault("deadlineAt", None)
        state["budget"]["modelLaunchesUsed"] = 0
        state["budget"]["startedAt"] = utc_now()
        for task in state["tasks"].values():
            if any(key in task for key in ("productAttemptsUsed", "acceptance", "status")):
                raise RunnerError("mission preparation cannot import task counters/acceptance")
            task.setdefault("completionAction", "product")
            task.update(productAttemptsUsed=0, status="ready", acceptance=None)
        completion_actions = {task_id: task["completionAction"] for task_id, task in state["tasks"].items()}
        if state["authority"].get("taskCompletionActions", completion_actions) != completion_actions:
            raise RunnerError("task completion action binding changed")
        state["authority"]["taskCompletionActions"] = completion_actions
        state["authoritySha256"] = _mission_digest(state["authority"])
        state["budget"].setdefault("reportLaunchReserve", 1 if state["authority"].get("reportCapabilityRef") else 0)
        validate_mission_state(state, state_path)
        minimum = len(state["tasks"]) + pending_review_launches(state) + state["budget"]["reportLaunchReserve"]
        if state["budget"]["maxModelLaunches"] < minimum:
            raise RunnerError("mission budget cannot cover initial work, mandatory reviews and report recovery reserve")
        atomic_write_loop_state(state_path, state)
        return state
    finally:
        lock.release()


def load_mission_state(order: dict[str, Any], policy: PathPolicy) -> tuple[dict[str, Any], Path]:
    meta = mission_context(order, required=True)
    contract = require_object(order.get("loopContract"), "mission loopContract")
    path = _mission_path({"workspace": str(policy.repo_path)}, contract.get("statePath", ""))
    if policy._matches(path, policy.allowed) or policy._matches(loop_lock_path(path), policy.allowed):
        raise RunnerError("mission state/lock must be outside executor allowedPaths")
    if policy._matches(path, policy.forbidden) or policy._matches(loop_lock_path(path), policy.forbidden):
        raise RunnerError("mission state/lock forbidden to controller")
    state = require_object(load_json(path), "mission state")
    validate_mission_state(state, path)
    if state["missionId"] != meta["missionId"] or contract.get("loopId") != state["missionId"]:
        raise RunnerError("mission binding mismatch")
    if str(policy.repo_path) != state["workspace"] or meta["approvalRef"] != state["authority"]["approvalRef"]:
        raise RunnerError("mission workspace/approval binding mismatch")
    return state, path


def mission_work_timeout(state: dict[str, Any], requested: float | None) -> float | None:
    if requested is not None and (isinstance(requested, bool) or not isinstance(requested, (int, float)) or not 0 < requested < float("inf")):
        raise RunnerError("mission requested timeout must be null or positive and finite")
    if state["cancelled"] or state.get("stopDeadlineAt") or state["status"] in MISSION_TERMINAL or state["status"] == "blocked":
        raise RunnerError("mission dispatch is closed")
    if state["budget"]["deadlineAt"] is None:
        return float(requested) if requested is not None else None
    remaining = (_mission_time(state["budget"]["deadlineAt"]) - datetime.now(timezone.utc)).total_seconds() - MISSION_RESERVE_SECONDS
    if remaining <= 0:
        raise RunnerError("mission work cutoff reached (30-second reserve)")
    return min(float(requested), remaining) if requested is not None else remaining


def mission_stop_deadline(state: dict[str, Any]) -> datetime:
    """Cleanup stays bounded even when productive work has no wall deadline."""
    deadlines = [datetime.now(timezone.utc) + timedelta(seconds=MISSION_RESERVE_SECONDS)]
    for value in (state.get("stopDeadlineAt"), state["budget"]["deadlineAt"]):
        if value is not None:
            deadlines.append(_mission_time(value))
    return min(deadlines)


def mission_snapshot(state: dict[str, Any], task_ids: list[str] | None = None) -> dict[str, Any]:
    paths = sorted({path for task_id in (task_ids or list(state["tasks"])) for path in state["tasks"][task_id]["productPaths"]})
    rows = []
    for value in paths:
        path = _mission_path(state, value)
        if path.exists() and not path.is_file():
            raise RunnerError("product snapshot requires regular files")
        content = path.read_bytes() if path.exists() else None
        rows.append({"path": str(path), "sha256": hashlib.sha256(content).hexdigest() if content is not None else None,
                     "bytes": len(content) if content is not None else 0})
    return {"files": rows, "sha256": _mission_digest(rows)}


def workspace_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Dirty baseline using the existing guard walk/exclusion approach.

    Hash chunks, lstat modes and symlink targets; never follow directory links.
    Control custody and the explicit mission store are not product bytes.
    """
    root = Path(state["workspace"])
    ignored = {".git", "node_modules", "dist", "build", "coverage", ".venv", "vendor", "__pycache__"}
    control = root / ".centurion" / "agents_results"
    store = Path(state["statePath"])
    # Generated directories are skipped only when they contain no tracked product
    # path. A dirty baseline may deliberately keep source under `build/` or `dist/`.
    tracked: set[Path] = set()
    # Only the declared workspace root establishes the fail-closed Git scope;
    # temporary fixture parents may themselves live under another repository.
    known_git = (root / ".git").exists()
    try:
        # Bound both Git wall time and bytes retained in controller memory.
        with tempfile.TemporaryFile() as output:
            completed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                stdout=output, stderr=subprocess.DEVNULL, timeout=5, check=False)
            output.seek(0)
            raw = output.read(8 * 1024 * 1024 + 1)
        if completed.returncode:
            if known_git:
                raise RunnerError("workspace Git inspection failed; scope snapshot unavailable")
        elif len(raw) > 8 * 1024 * 1024:
            raise RunnerError("workspace Git inspection byte limit exceeded")
        else:
            tracked = {root / os.fsdecode(value) for value in raw.split(b"\0") if value}
    except (OSError, subprocess.TimeoutExpired) as exc:
        if known_git:
            raise RunnerError(f"workspace Git inspection failed; scope snapshot unavailable: {exc}") from exc
    scoped = {root / value if not Path(value).is_absolute() else Path(value)
              for task in state.get("tasks", {}).values() for value in task.get("productPaths", [])}
    included = tracked | scoped
    rows = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        dirs[:] = sorted(name for name in dirs if (
            name not in ignored
            or any(path == base / name or path.is_relative_to(base / name) or (base / name).is_relative_to(path)
                   for path in included)
        ) and name != ".git" and base / name != control)
        links = [name for name in dirs if (base / name).is_symlink()]
        dirs[:] = [name for name in dirs if name not in links]
        for name in sorted(files + links):
            path = base / name
            if path in {store, loop_lock_path(store)} or (path.parent == store.parent and path.name.startswith(store.name + ".")):
                continue
            st = path.lstat()
            if path.is_symlink():
                digest = hashlib.sha256(os.readlink(path).encode()).hexdigest()
                kind = "symlink"
            elif path.is_file():
                hasher = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(65536), b""):
                        hasher.update(chunk)
                digest, kind = hasher.hexdigest(), "file"
            else:
                raise RunnerError("unsupported workspace entry")
            rows[str(path)] = {"sha256": digest, "mode": st.st_mode, "kind": kind}
    return rows


def verify_workspace_diff(reservation: Any, result: dict[str, Any]) -> list[dict[str, Any]]:
    before = reservation.intent["workspaceBaseline"]
    after = workspace_snapshot(reservation.state)
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    declared = {str(reservation.policy.resolve_under_repo(item["path"])) for item in result["filesChanged"]
                if reservation.policy.control_namespace not in reservation.policy.resolve_under_repo(item["path"]).parents}
    if reservation.meta["action"] != "product" and changed:
        raise RunnerError("non-product dispatch changed workspace")
    rows = []
    for value in changed:
        reservation.policy.order_path(value, "observed workspace diff")
        if value not in declared:
            raise RunnerError(f"unreported workspace change: {value}")
        rows.append({"path": value, "before": before.get(value), "after": after.get(value)})
    reservation.intent["workspaceAfter"] = after
    reservation.intent["workspaceDiff"] = rows
    return rows


def _mission_file_ref(path: Path) -> dict[str, Any]:
    try:
        require_no_symlink_components(path)
    except ArtifactNamespaceError as exc:
        raise RunnerError(str(exc)) from exc
    if not path.is_file():
        raise RunnerError(f"mission evidence is not a regular file: {path}")
    data = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _check_mission_refs(intent: dict[str, Any]) -> None:
    for key in ("resultRef", "acceptanceRef"):
        ref = intent.get(key)
        if not isinstance(ref, dict) or _mission_file_ref(Path(ref["path"])) != ref:
            raise RunnerError("accepted intent evidence bytes changed or missing")


def _validate_mission_scope(order: dict[str, Any], policy: PathPolicy, state: dict[str, Any]) -> dict[str, Any]:
    meta = mission_context(order, required=True)
    if meta["taskId"] not in state["tasks"]:
        raise RunnerError("unknown mission task")
    task = state["tasks"][meta["taskId"]]
    authority = state["authority"]
    try:
        route = validate_order_routing(order)
    except RoutingError as exc:
        raise RunnerError(f"mission routing invalid: {exc}") from exc
    if route is None:
        raise RunnerError("policy 3.0 requires canonical routing without legacy fallback")
    expected_profile = {"product": "implementation", "review": "terminal_review", "advisory": "advisory", "report": "implementation"}[meta["action"]]
    if route["executionProfile"] != expected_profile or PROFILE_RANK[route["verificationProfile"]] < PROFILE_RANK[task["verificationProfile"]]:
        raise RunnerError("mission action/verification profile does not match approved task")
    if task["verificationProfile"] == "V0" and route["verificationProfile"] != "V0" and meta["action"] == "product":
        raise RunnerError("higher verification floor requires explicit task preparation; no V0 acceptance bypass")
    if meta["action"] not in authority["allowedActions"]:
        raise RunnerError("requested action lacks mission authority")
    if meta["action"] == "product" and task.get("completionAction", "product") != "product":
        raise RunnerError("product dispatch cannot complete an advisory-only task")
    if meta["strategyId"] != state["strategyId"]:
        raise RunnerError("stale mission strategy")
    if order["objective"] != task["objective"] or order["acceptanceCriteria"] != task["acceptanceCriteria"]:
        raise RunnerError("task objective/acceptance criteria changed or weakened")
    if not set(authority["nonGoals"]).issubset(order["nonGoals"]):
        raise RunnerError("mission nonGoals were removed")
    product_rules = []
    for value in order["allowedPaths"]:
        base = policy.resolve_under_repo(value[:-3] if value.endswith("/**") else value)
        if base == policy.control_namespace or policy.control_namespace in base.parents:
            continue
        product_rules.append(value)
    advisory = meta["action"] in {"advisory", "review"}
    if advisory:
        if meta["action"] == "review":
            candidate = state["intents"].get(meta.get("candidateIntentId"))
            existing = state["intents"].get(meta["intentId"], {})
            accepted_collection = (existing.get("status") == "accepted"
                                   and existing.get("orderSha256") == _mission_digest(order)
                                   and existing.get("candidateIntentId") == meta.get("candidateIntentId"))
            if (not candidate or candidate.get("action") != "product" or candidate.get("taskId") != meta["taskId"]
                    or (candidate.get("status") != "captured"
                        and not (accepted_collection and candidate.get("status") == "accepted"))):
                raise RunnerError("review requires captured candidate intent")
            expected = {Path(row["path"]).resolve() for row in candidate["snapshot"]["files"]}
            product_patterns = [(mode, pattern) for mode, pattern in policy.allowed
                                if pattern != policy.control_namespace and policy.control_namespace not in pattern.parents]
            if any(mode != "exact" for mode, _ in product_patterns) or {p for _, p in product_patterns} != expected:
                raise RunnerError("review allowedPaths must contain exactly captured product files plus custody namespace")
            for path in expected:
                policy.order_path(path, "review candidate product path")
        elif product_rules or order["proofCommands"]:
            raise RunnerError("advisory cannot write product scope or run product proof")
        if order["proofCommands"]:
            raise RunnerError("read-only advisory/review cannot run product proof")
        for item in order["expectedArtifacts"]:
            policy.control_path(item["path"], "advisory artifact")
    if not advisory and (not product_rules or not _mission_path_subset(state, product_rules, task["allowedPaths"])):
        raise RunnerError("requested paths expand task authority or empty product scope")
    if not advisory and not _mission_path_subset(state, task["productPaths"], product_rules):
        raise RunnerError("scope narrowing removed required product/proof coverage")
    if not _mission_path_subset(state, authority["forbiddenPaths"], order["forbiddenPaths"]):
        raise RunnerError("mission forbidden paths were removed")
    if not advisory and (order["proofCommands"] != task["requiredProof"] or order["expectedArtifacts"] != task["expectedArtifacts"]):
        raise RunnerError("required proof/artifact coverage changed")
    deps = meta["dependencyRevisions"]
    if set(deps) != set(task["dependencies"]):
        raise RunnerError("dependency revision binding is incomplete")
    for dep, revision in deps.items():
        accepted = state["tasks"][dep].get("acceptance")
        if not accepted or revision != accepted["revision"] or mission_snapshot(state, [dep])["sha256"] != accepted["snapshotSha256"]:
            raise RunnerError("dependency is unaccepted or revision/snapshot is stale")
    return task


def _mission_process_identity(pid: int) -> dict[str, Any] | None:
    if type(pid) is not int or pid <= 0:
        raise RunnerError("mission process PID must be a positive integer")
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RunnerError("mission process identity cannot be read; effect remains unknown") from exc
    try:
        fields = raw[raw.rindex(")") + 2:].split()
        if fields[0] == "Z":
            return None
        return {"pid": pid, "startTicks": fields[19], "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
    except (OSError, ValueError, IndexError) as exc:
        raise RunnerError("mission process identity cannot be verified; effect remains unknown") from exc


def _mission_process_activity(pid: int) -> dict[str, Any] | None:
    """Read non-authoritative process activity without changing its identity."""
    if type(pid) is not int or pid <= 0:
        raise RunnerError("mission process PID must be a positive integer")
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RunnerError("mission process activity cannot be read; liveness remains unknown") from exc
    try:
        fields = raw[raw.rindex(")") + 2:].split()
        if fields[0] == "Z":
            return None
        return {
            "pid": pid,
            "startTicks": fields[19],
            "state": fields[0],
            "cpuTicks": int(fields[11]) + int(fields[12]),
        }
    except (OSError, ValueError, IndexError) as exc:
        raise RunnerError("mission process activity cannot be verified; liveness remains unknown") from exc


def _terminate_mission_process(identity: dict[str, Any], deadline_at: str, *, signal_to_send: signal.Signals = signal.SIGTERM,
                               wait: bool = True) -> bool:
    """Signal a pinned PID, never a reused PID or unverified process group."""
    pid = identity["pid"]
    current = _mission_process_identity(pid)
    if current is None:
        return True
    if current != identity or not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        return False
    try:
        pidfd = os.pidfd_open(pid)
    except ProcessLookupError:
        return True
    try:
        if _mission_process_identity(pid) != identity:
            return False
        remaining = (_mission_time(deadline_at) - datetime.now(timezone.utc)).total_seconds()
        if wait and remaining <= 0:
            return False
        signal.pidfd_send_signal(pidfd, signal_to_send)
        if not wait:
            return True
        if select.select([pidfd], [], [], min(10, remaining))[0]:
            return True
        remaining = (_mission_time(deadline_at) - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return False
        signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        return bool(select.select([pidfd], [], [], remaining)[0])
    except ProcessLookupError:
        return True
    finally:
        os.close(pidfd)


class MissionReservation:
    """One Gateway transaction. The held LoopStateLock is the only writer lock."""

    def __init__(self, order: dict[str, Any], policy: PathPolicy, state: dict[str, Any], path: Path,
                 lock: LoopStateLock, disposition: str) -> None:
        self.order, self.policy, self.state, self.path, self.lock = order, policy, state, path, lock
        self.meta = mission_context(order, required=True)
        self.intent = state["intents"][self.meta["intentId"]]
        self.disposition = disposition
        self.closed = False
        self.write_failed = False

    def save(self) -> None:
        if self.closed or self.write_failed or self.lock._handle is None:
            raise RunnerError("mission reservation is closed")
        validate_mission_state(self.state, self.path)
        try:
            atomic_write_loop_state(self.path, self.state)
        except OSError:
            # replace may have succeeded before fsync failed. Do not roll back
            # spent counters; poison acceptance/effect, then abandon this object.
            self.write_failed = True
            if self.intent["status"] == "accepted":
                task = self.state["tasks"][self.meta["taskId"]]
                if self.meta["action"] == task.get("completionAction", "product"):
                    task.update(status="verifying", acceptance=None)
            self.intent.update(status="unknown_effect", effect="unknown_effect")
            if self.state["status"] not in MISSION_TERMINAL:
                self.state.update(status="blocked", blocker={"decisionOwner": "controller", "reason": "state write failed; unknown commit outcome"})
            try:
                atomic_write_loop_state(self.path, self.state)
            except OSError:
                pass
            raise

    def append_telemetry(self, ledger_path: Path, row: dict[str, Any]) -> dict[str, Any]:
        """Ledger observes committed state; it cannot reserve/refund authority."""
        persisted, _ = load_mission_state(self.order, self.policy)
        intent = persisted["intents"][self.meta["intentId"]]
        observed = dict(row, policyVersion=MISSION_POLICY, missionId=persisted["missionId"], taskId=self.meta["taskId"],
                        dispatchIntentId=self.meta["intentId"], attemptKind=intent["action"], orderId=intent["orderId"],
                        modelLaunchesUsed=persisted["budget"]["modelLaunchesUsed"],
                        productAttemptsUsed=persisted["tasks"][self.meta["taskId"]]["productAttemptsUsed"],
                        reportAttemptsUsed=intent["reportAttemptsUsed"])
        return append_attempt(ledger_path, observed)

    def close(self) -> None:
        self.disposition = "closed"
        self.lock.release()
        self.closed = True

    def work_timeout(self, requested_seconds: float | None) -> float | None:
        if self.closed or self.write_failed or self.lock._handle is None:
            raise RunnerError("mission reservation is closed")
        return mission_work_timeout(self.state, requested_seconds)

    def observe_process(self, observation: dict[str, Any]) -> None:
        """Latest controller liveness evidence, never productive progress/proof."""
        self.intent["processObservation"] = observation
        self.save()

    def stop_requested(self) -> bool:
        try:
            self.work_timeout(1)
        except RunnerError:
            return True
        return False

    def before_spawn(self) -> None:
        if self.disposition != "launch" or self.intent["status"] != "reserved":
            raise RunnerError("intent is not a fresh launch reservation; never replay")
        self.work_timeout(self.order["launch"]["timeoutSeconds"])
        self.intent.update(status="dispatching", effect="unknown_effect")
        self.save()

    def record_process(self, pid: int, *, auxiliary: bool = False) -> None:
        if self.intent["status"] not in ({"captured", "reportable", "accepted"} if auxiliary else {"dispatching"}):
            raise RunnerError("process requires persisted dispatch barrier")
        identity = _mission_process_identity(pid)
        if identity is None:
            raise RunnerError("child identity unavailable; do not accept or replay")
        if auxiliary:
            self.intent.setdefault("proofProcesses", []).append(identity)
        else:
            self.intent.update(status="running", process=identity, processStopped=False)
        self.save()

    def terminate_owned_process(self, identity: dict[str, Any] | None = None) -> bool:
        identity = identity or self.intent.get("process")
        if "stopDeadlineAt" not in self.state:
            self.state["stopDeadlineAt"] = mission_stop_deadline(self.state).isoformat()
            self.save()
        stopped = bool(identity) and _terminate_mission_process(identity, self.state["stopDeadlineAt"])
        self.intent["processStopped"] = stopped
        if not stopped:
            self.intent.update(status="unknown_effect", effect="unknown_effect")
        self.save()
        return stopped

    def request_owned_process_stop(self, identity: dict[str, Any] | None = None) -> bool:
        """Request TERM without blocking the stream reader; cleanup remains bounded by stopDeadlineAt."""
        identity = identity or self.intent.get("process")
        if "stopDeadlineAt" not in self.state:
            self.state["stopDeadlineAt"] = mission_stop_deadline(self.state).isoformat()
            self.save()
        sent = bool(identity) and _terminate_mission_process(identity, self.state["stopDeadlineAt"], wait=False)
        self.intent["terminationRequested"] = True
        self.intent["processStopped"] = not sent and _mission_process_identity(identity["pid"]) is None if identity else False
        self.save()
        return sent

    def force_owned_process_stop(self, identity: dict[str, Any] | None = None) -> bool:
        """Escalate a still-owned child to SIGKILL without waiting inside the reader."""
        identity = identity or self.intent.get("process")
        return bool(identity) and _terminate_mission_process(
            identity, self.state["stopDeadlineAt"],
            signal_to_send=signal.SIGKILL, wait=False)

    def cancel(self, reason: str) -> None:
        if self.state["status"] in {"completed", "failed"}:
            raise RunnerError("terminal mission cannot be reactivated or rewritten by cancellation")
        stop_deadline = self.state.get("stopDeadlineAt") or mission_stop_deadline(self.state).isoformat()
        self.state.update(cancelled=True, status="stopped", stopReason=reason,
                          stopDeadlineAt=stop_deadline)
        self.save()

    def observe_result(self, result: dict[str, Any], result_path: Path, *, process_stopped: bool) -> None:
        if self.intent["status"] not in {"dispatching", "running", "reportable"}:
            raise RunnerError("result observation requires an open dispatch")
        if not process_stopped or (self.intent.get("process") and _mission_process_identity(self.intent["process"]["pid"]) == self.intent["process"]):
            raise RunnerError("child stop is unconfirmed")
        result_path = self.policy.control_path(result_path, "mission canonical result")
        if result_path != self.policy.resolve_under_repo(self.order["outputContract"]["resultPath"]):
            raise RunnerError("mission result path binding mismatch")
        canonical, _ = verify_result(result_path, self.order, self.policy)
        if canonical != result:
            raise RunnerError("canonical result does not match observation")
        if self.meta["action"] in {"review", "advisory"} and mission_snapshot(self.state, [self.meta["taskId"]]) != self.intent["beforeSnapshot"]:
            raise RunnerError("review/advisory mutated product bytes")
        self.intent.update(status="captured", processStopped=True, effect="observed", resultStatus=result["status"],
                           resultRef=_mission_file_ref(result_path), snapshot=mission_snapshot(self.state, [self.meta["taskId"]]))
        if self.state["status"] not in MISSION_TERMINAL:
            self.state["status"] = "verifying"
            self.state["tasks"][self.meta["taskId"]]["status"] = "verifying"
        self.save()

    def fail(self, reason: str, *, process_stopped: bool = False) -> None:
        if self.intent["status"] == "accepted":
            raise RunnerError("accepted intent cannot be rewritten")
        if self.intent.get("process") and _mission_process_identity(self.intent["process"]["pid"]) == self.intent["process"]:
            process_stopped = False
        observed = self.intent.get("effect") == "observed"
        known_not_started = self.intent["status"] == "reserved"
        self.intent.update(status="rejected" if (observed or known_not_started) and process_stopped else "unknown_effect",
                           processStopped=process_stopped, failure=reason)
        if self.state["status"] not in MISSION_TERMINAL:
            self.state.update(status="blocked", blocker={"decisionOwner": "controller", "reason": reason})
        self.save()

    def accept(self, proof_checks: dict[str, Any], acceptance_path: Path, review: Any = None) -> dict[str, Any]:
        self.work_timeout(1)
        if self.intent["status"] != "captured" or self.intent.get("resultStatus") != "done" or not self.intent.get("processStopped"):
            raise RunnerError("acceptance requires a stopped, captured done result")
        task = self.state["tasks"][self.meta["taskId"]]
        _validate_mission_scope(self.order, self.policy, self.state)
        snapshot = mission_snapshot(self.state, [self.meta["taskId"]])
        if snapshot != self.intent["snapshot"]:
            raise RunnerError("product changed after candidate snapshot; reproof required")
        _validate_mission_proof(proof_checks, self.order["proofCommands"], snapshot["sha256"], task["acceptanceCriteria"])
        self.require_acceptance_ready(review)
        acceptance_path = self.policy.control_path(acceptance_path, "mission controller acceptance")
        receipt = require_object(load_json(acceptance_path), "controller acceptance")
        if receipt.get("status") != "passed" or receipt.get("orderId") != self.order["orderId"] or receipt.get("canonicalResultSha256") != self.intent["resultRef"]["sha256"]:
            raise RunnerError("controller acceptance receipt binding failed")
        if _mission_file_ref(Path(self.intent["resultRef"]["path"])) != self.intent["resultRef"]:
            raise RunnerError("result bytes changed before acceptance")
        if self.meta["action"] == "review":
            self.intent["review"] = self._validated_review()
        self.intent.update(status="accepted", acceptanceRef=_mission_file_ref(acceptance_path), proof=proof_checks)
        if self.intent.get("reportIntentId"):
            report = self.state["intents"][self.intent["reportIntentId"]]
            report.update(status="accepted", processStopped=True, effect="observed", resultRef=self.intent["resultRef"],
                          acceptanceRef=self.intent["acceptanceRef"], snapshot=self.intent["snapshot"])
        _check_mission_refs(self.intent)
        if self.meta["action"] == task.get("completionAction", "product"):
            task.update(status="accepted", acceptance={"intentId": self.meta["intentId"], "revision": snapshot["sha256"],
                                                       "snapshotSha256": snapshot["sha256"], "criteria": list(task["acceptanceCriteria"])})
        self.save()
        return self.intent

    def require_acceptance_ready(self, review: str | None = None) -> None:
        """Call before writing a passing terminal receipt; capture can await review."""
        self.work_timeout(1)
        if self.intent["status"] != "captured" or self.intent.get("resultStatus") != "done" or not self.intent.get("processStopped"):
            raise RunnerError("acceptance requires stopped captured done result")
        _validate_mission_scope(self.order, self.policy, self.state)
        if mission_snapshot(self.state, [self.meta["taskId"]]) != self.intent["snapshot"]:
            raise RunnerError("product changed after capture; acceptance/review must be refreshed")
        if "workspaceAfter" in self.intent and workspace_snapshot(self.state) != self.intent["workspaceAfter"]:
            raise RunnerError("workspace bytes changed after controller proof")
        task = self.state["tasks"][self.meta["taskId"]]
        if any(_mission_process_identity(p["pid"]) == p for p in self.intent.get("proofProcesses", [])):
            raise RunnerError("proof process remains open")
        if self.meta["action"] == "review":
            self._validated_review()
        if self.meta["action"] == "product" and task["verificationProfile"] != "V0":
            reviewed = self.state["intents"].get(review)
            if not reviewed or reviewed["status"] != "accepted" or reviewed.get("candidateIntentId") != self.meta["intentId"]:
                raise RunnerError("accepted independent review is required")
            _check_mission_refs(reviewed)

    def _validated_review(self) -> dict[str, Any]:
        result = require_object(load_json(Path(self.intent["resultRef"]["path"])), "review result")
        extensions = require_object(result.get("executorExtensions"), "review result extensions")
        verdict = require_object(extensions.get("review"), "review verdict")
        candidate = self.state["intents"].get(self.meta.get("candidateIntentId"))
        if not candidate or candidate["action"] != "product" or candidate["status"] != "captured" or candidate["taskId"] != self.meta["taskId"]:
            raise RunnerError("review candidate intent is unavailable")
        if verdict.get("verdict") != "pass" or not isinstance(verdict.get("findings"), list) or verdict["findings"]:
            raise RunnerError("review fail/blocked/missing verdict does not accept product")
        if (verdict.get("reviewedOrderId") != candidate["orderId"] or
                verdict.get("reviewedResultSha256") != candidate["resultRef"]["sha256"] or
                verdict.get("productSnapshotSha256") != candidate["snapshot"]["sha256"] or
                self.intent["snapshot"] != candidate["snapshot"] or self.order["executor"] == candidate["executor"]):
            raise RunnerError("independent review binding mismatch")
        if _mission_file_ref(Path(candidate["resultRef"]["path"])) != candidate["resultRef"]:
            raise RunnerError("reviewed candidate result bytes changed")
        return verdict


def pending_review_launches(state: dict[str, Any], current_task: str | None = None) -> int:
    """Keep a minimum launch for each still-required independent review."""
    latest = {task_id: max((intent_id for intent_id, intent in state["intents"].items()
                            if intent["taskId"] == task_id and intent["action"] == "product"),
                           key=lambda intent_id: state["intents"][intent_id].get("reservedAt", ""), default=None)
              for task_id in state["tasks"]}
    return sum(
        task_id != current_task and task["status"] != "accepted"
        and task.get("completionAction", "product") == "product" and task["verificationProfile"] != "V0"
        and not any(intent["taskId"] == task_id and intent["action"] == "review" and intent["status"] == "accepted"
                    and intent.get("candidateIntentId") == latest[task_id]
                    for intent in state["intents"].values())
        for task_id, task in state["tasks"].items()
    )


def reserve_mission_dispatch(order: dict[str, Any], policy: PathPolicy, *, resume_only: bool = False) -> MissionReservation:
    meta = mission_context(order, required=True)
    contract = require_object(order.get("loopContract"), "mission loopContract")
    path = _mission_path({"workspace": str(policy.repo_path)}, contract.get("statePath", ""))
    lock = LoopStateLock(loop_lock_path(path)).acquire()
    try:
        state, path = load_mission_state(order, policy)
        task = _validate_mission_scope(order, policy, state)
        old = state["intents"].get(meta["intentId"])
        if old:
            if old["orderSha256"] != _mission_digest(order):
                raise RunnerError("existing intent cannot be rebound to a new order/model/reviewer")
            disposition = "accepted" if old["status"] == "accepted" else ("open" if old["status"] in MISSION_OPEN_INTENTS else "closed")
            if disposition == "accepted":
                _check_mission_refs(old)
                if mission_snapshot(state, [meta["taskId"]]) != old["snapshot"]:
                    raise RunnerError("accepted intent product snapshot is stale; never replay")
            return MissionReservation(order, policy, state, path, lock, disposition)
        if resume_only:
            raise RunnerError("report recovery requires an existing saved product; never dispatch product")
        try:
            mission_work_timeout(state, order["launch"]["timeoutSeconds"])
        except RunnerError as exc:
            if state["status"] not in MISSION_TERMINAL and state["budget"]["deadlineAt"] is not None and (_mission_time(state["budget"]["deadlineAt"]) - datetime.now(timezone.utc)).total_seconds() <= 30:
                state.update(status="failed", failure="mission work cutoff reached; dispatch closed")
                atomic_write_loop_state(path, state)
            raise exc
        report_reserve = max(0, state["budget"].get("reportLaunchReserve", 0) - sum(
            intent["action"] == "report" and intent.get("modelLaunch", True) for intent in state["intents"].values()))
        required = 1 + pending_review_launches(state, meta["taskId"] if meta["action"] == "review" else None) + report_reserve
        if state["budget"]["maxModelLaunches"] - state["budget"]["modelLaunchesUsed"] < required:
            state.update(status="blocked", blocker={"decisionOwner": "customer", "reasonCode": "model_launch_budget",
                         "reason": "mission model-launch budget exhausted or reserved for review/report recovery"})
            atomic_write_loop_state(path, state)
            raise RunnerError("mission model-launch budget exhausted or reserved for review/report recovery")
        if any(i["status"] in {"reserved", "dispatching", "running", "unknown_effect"} for i in state["intents"].values()):
            raise RunnerError("open or unknown effect requires reconciliation; never replay")
        if meta["action"] == "report":
            raise RunnerError("report-only dispatch disabled: no trusted no-write capability verifier")
        if meta["action"] == "advisory" and task.get("completionAction", "product") == "advisory" and task["status"] == "accepted":
            raise RunnerError("accepted advisory task must not restart consultation")
        if meta["action"] == "product":
            if task["status"] == "accepted":
                raise RunnerError("accepted task must not restart development")
            if task["productAttemptsUsed"] >= task["maxProductAttempts"]:
                state.update(status="failed", failure="task product-attempt budget exhausted")
                atomic_write_loop_state(path, state)
                raise RunnerError("task product-attempt budget exhausted")
            if task["productAttemptsUsed"] and (not meta.get("retryReason") or not meta.get("expectedEvidence")):
                raise RunnerError("product retry requires reason and expected new evidence")
            if any(i["taskId"] == meta["taskId"] and i["action"] == "product" and i["status"] == "captured" for i in state["intents"].values()):
                raise RunnerError("captured product requires acceptance/review or explicit criterion-bound correction")
            task["productAttemptsUsed"] += 1
            task["status"] = "running"
        if meta["action"] == "review":
            candidate = state["intents"].get(meta.get("candidateIntentId"))
            if not candidate or candidate["status"] != "captured" or candidate["action"] != "product":
                raise RunnerError("review requires captured candidate intent")
            if candidate["executor"] == order["executor"] or mission_snapshot(state, [meta["taskId"]]) != candidate["snapshot"]:
                raise RunnerError("review requires independent executor and current candidate bytes")
            # A reviewer may read the captured product, but only the exact
            # product files bound by the candidate snapshot plus its own
            # controller custody namespace. Reject a custody-only review order
            # before spending a model launch; otherwise the model can produce a
            # valid review that controller acceptance must reject later.
            for row in candidate["snapshot"].get("files", []):
                if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                    raise RunnerError("review candidate snapshot contains an invalid product path")
                policy.order_path(row["path"], "review candidate product path")
            from order_preflight import review_binding
            binding = review_binding(order, validate_order_routing(order))
            if binding != {"reviewedOrderId": candidate["orderId"], "reviewedResultSha256": candidate["resultRef"]["sha256"],
                           "productSnapshotSha256": candidate["snapshot"]["sha256"]}:
                raise RunnerError("review controller candidate binding mismatch")
        state["budget"]["modelLaunchesUsed"] += 1
        state["status"] = "verifying" if meta["action"] == "review" else "running"
        state["intents"][meta["intentId"]] = {"intentId": meta["intentId"], "taskId": meta["taskId"], "action": meta["action"],
            "orderId": order["orderId"], "orderSha256": _mission_digest(order), "executor": order["executor"],
            "candidateIntentId": meta.get("candidateIntentId"), "status": "reserved", "effect": "not_started",
            "reservedAt": utc_now(), "reportAttemptsUsed": 0, "processStopped": False,
            "beforeSnapshot": mission_snapshot(state, [meta["taskId"]]), "workspaceBaseline": workspace_snapshot(state)}
        validate_mission_state(state, path)
        atomic_write_loop_state(path, state)
        return MissionReservation(order, policy, state, path, lock, "launch")
    except BaseException:
        lock.release()
        raise


def _validate_mission_proof(checks: dict[str, Any], required: list[dict[str, Any]], snapshot: str, criteria: list[str]) -> None:
    if checks.get("productSnapshotSha256") != snapshot or checks.get("criteria") != criteria:
        raise RunnerError("controller proof must bind all criteria to final product bytes")
    observed = checks.get("proof")
    if not isinstance(observed, list) or len(observed) != len(required):
        raise RunnerError("required controller proof coverage missing")
    for check, proof in zip(observed, required):
        if (check.get("command") != proof["command"] or Path(check.get("cwd", "")).resolve() != Path(proof["cwd"]).resolve()
                or check.get("required") is not True or check.get("status") != "pass" or check.get("exitCode") != 0):
            raise RunnerError("required controller proof did not pass")


def _run_final_mission_proof(state: dict[str, Any], proofs: list[dict[str, Any]], reservation: Any) -> list[dict[str, Any]]:
    checks = []
    for proof in proofs:
        timeout = mission_work_timeout(state, None if reservation.order["launch"]["timeoutSeconds"] is None else 3600)
        try:
            from result_gateway import run_child
            observed = run_child(proof["argv"], _mission_path(state, proof["cwd"]), timeout, 10,
                                 reservation=reservation, auxiliary=True)
            if observed["error"] or not observed.get("processStopped"):
                raise RunnerError("final controller proof incomplete")
            completed = subprocess.CompletedProcess(proof["argv"], observed["exitCode"])
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RunnerError(f"final integration proof incomplete: {exc}") from exc
        mission_work_timeout(state, 1)
        if completed.returncode != 0:
            raise RunnerError(f"final integration proof failed: {proof['command']}")
        checks.append({"command": proof["command"], "cwd": proof["cwd"], "required": True, "status": "pass",
                       "exitCode": completed.returncode, "summary": "controller observed final integration proof"})
    return checks


def complete_mission(order: dict[str, Any], policy: PathPolicy, final_proof: dict[str, Any], project_revision: str) -> dict[str, Any]:
    _, path = load_mission_state(order, policy)
    lock = LoopStateLock(loop_lock_path(path)).acquire()
    try:
        state, path = load_mission_state(order, policy)
        mission_work_timeout(state, 1)
        if not project_revision:
            raise RunnerError("final project revision is required")
        for task_id, task in state["tasks"].items():
            if task["status"] != "accepted" or not task.get("acceptance"):
                raise RunnerError("mission has unaccepted tasks/criteria")
            _check_mission_refs(state["intents"][task["acceptance"]["intentId"]])
            if mission_snapshot(state, [task_id])["sha256"] != task["acceptance"]["snapshotSha256"]:
                raise RunnerError("accepted task bytes changed after review; integration reproof/review required")
        if any(i["status"] in {*MISSION_OPEN_INTENTS, "unknown_effect"} for i in state["intents"].values()):
            raise RunnerError("mission has open/unknown effect intents")
        if any(_mission_process_identity(p["pid"]) == p for i in state["intents"].values() for p in i.get("proofProcesses", [])):
            raise RunnerError("mission has open proof processes")
        snapshot = mission_snapshot(state)
        proofs = [proof for task in state["tasks"].values() for proof in task["requiredProof"]]
        _validate_mission_proof(final_proof, proofs, snapshot["sha256"], state["authority"]["criteria"])
        final_reservation = MissionReservation(order, policy, state, path, lock, "open")
        previous_signals = {}
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                previous_signals[sig] = signal.signal(sig, lambda signum, frame: final_reservation.cancel(f"final proof signal {signum}"))
            observed = _run_final_mission_proof(state, proofs, final_reservation)
        finally:
            for sig, handler in previous_signals.items():
                signal.signal(sig, handler)
        if mission_snapshot(state) != snapshot:
            raise RunnerError("final proof changed product bytes; acceptance/review must be refreshed")
        mission_work_timeout(state, 1)
        final_proof = dict(final_proof, proof=observed)
        state.update(status="completed", completion={"projectRevision": project_revision, "snapshot": snapshot,
                                                     "proof": final_proof, "completedAt": utc_now()})
        try:
            atomic_write_loop_state(path, state)
        except OSError:
            state.update(status="failed", completion=None, failure="final state write failed; completion unconfirmed")
            try:
                atomic_write_loop_state(path, state)
            except OSError:
                pass
            raise
        return state
    finally:
        lock.release()


def record_mission_observation(reservation: MissionReservation, observation: dict[str, Any]) -> dict[str, Any]:
    """Persist controller-verified evidence, not arbitrary result hashes as progress."""
    from progress_drift_detector import evaluate_progress
    from blocker_packet_projection import build_blocker_packet
    state = reservation.state
    if state["status"] in MISSION_TERMINAL:
        raise RunnerError("terminal mission cannot record new development")
    row = copy.deepcopy(observation)
    state["observations"].append(row)
    # A strategy switch resets the no-progress window, never cumulative counters.
    start = state.get("strategyObservationStart", 0)
    progress_budgets = None
    if state["budget"]["deadlineAt"] is None:
        # Legacy advisory wall limits cannot close monitored work. Project
        # them out without changing approved authority or finite old missions.
        declared = state["authority"].get("budgets")
        progress_budgets = {key: value for key, value in declared.items()
                            if key not in {"maxWallSeconds", "wallTimeSeconds", "wallSeconds"}} if isinstance(declared, dict) else {}
    advisory = evaluate_progress(state["authority"], state["observations"][start:], budgets=progress_budgets)
    state["progressDecision"] = advisory
    if advisory["decision"] != "allow":
        state.update(status="blocked", blocker={"decisionOwner": "customer" if advisory["requiresOwnerDecision"] else "controller",
                                               "reason": advisory["reasonCodes"]})
        state["blockerPacket"] = build_blocker_packet(reservation.order, None, loop_state=advisory)
    reservation.save()
    return advisory


def switch_mission_strategy(reservation: MissionReservation, strategy_id: str, reason: str) -> None:
    state = reservation.state
    if state["status"] != "blocked" or (state.get("blocker") or {}).get("decisionOwner") != "controller":
        raise RunnerError("strategy switch requires an internal controller blocker")
    if state["strategySwitchesUsed"] or not strategy_id or strategy_id == state["strategyId"] or not reason:
        raise RunnerError("only one explicit strategy switch is allowed")
    candidate = dict(state, status="running")
    mission_work_timeout(candidate, 1)
    if state["budget"]["modelLaunchesUsed"] >= state["budget"]["maxModelLaunches"]:
        raise RunnerError("strategy switch cannot replenish budget")
    if any(i["status"] in {"reserved", "dispatching", "running", "unknown_effect"} for i in state["intents"].values()):
        raise RunnerError("strategy switch cannot replay open/unknown effect")
    state.update(status="running", strategyId=strategy_id, strategySwitchesUsed=1,
                 strategySwitch={"reason": reason, "at": utc_now()}, blocker=None,
                 strategyObservationStart=len(state["observations"]))
    reservation.save()


def prepare_mission_correction(reservation: MissionReservation, criterion: str, evidence_path: Path,
                               reason: str, expected_evidence: str) -> None:
    """A failed criterion can be corrected without inventing customer approval."""
    state = reservation.state
    if state["status"] not in {"running", "verifying", "blocked"} or (state.get("blocker") or {}).get("decisionOwner") == "customer":
        raise RunnerError("correction cannot reactivate terminal/external blocked mission")
    if state.get("progressDecision", {}).get("decision") in {"escalate", "replan", "block"}:
        raise RunnerError("stopped strategy requires the one bounded strategy switch")
    task_id = reservation.meta["taskId"]
    task = state["tasks"][task_id]
    if criterion not in task["acceptanceCriteria"] or not reason or not expected_evidence:
        raise RunnerError("correction must bind an existing criterion and expected evidence")
    if task["status"] == "accepted" or task["productAttemptsUsed"] >= task["maxProductAttempts"]:
        raise RunnerError("accepted task or exhausted product attempts cannot be corrected implicitly")
    if any(i["status"] in {"reserved", "dispatching", "running", "unknown_effect"} for i in state["intents"].values()):
        raise RunnerError("correction cannot replay an open/unknown effect")
    mission_work_timeout(dict(state, status="running"), 1)
    if state["budget"]["modelLaunchesUsed"] >= state["budget"]["maxModelLaunches"]:
        raise RunnerError("correction cannot replenish launch budget")
    evidence = _mission_file_ref(_mission_path(state, str(evidence_path)))
    for intent in state["intents"].values():
        if intent["taskId"] == task_id and intent["action"] == "product" and intent["status"] == "captured":
            intent.update(status="rejected", correctionEvidence=evidence)
    task.update(status="ready", acceptance=None)
    state.update(status="running", blocker=None, correction={"taskId": task_id, "criterion": criterion, "evidence": evidence,
                 "reason": reason, "expectedEvidence": expected_evidence, "at": utc_now()})
    reservation.save()


def cancel_mission(reservation: MissionReservation, reason: str) -> None:
    reservation.cancel(reason)


def resume_mission(reservation: MissionReservation, owner_decision: dict[str, Any]) -> None:
    state = reservation.state
    if state["status"] != "blocked" or (state.get("blocker") or {}).get("decisionOwner") != "customer":
        raise RunnerError("only externally blocked missions may resume by owner decision")
    if owner_decision.get("approvalRef") != state["authority"]["approvalRef"] or owner_decision.get("missionId") != state["missionId"] or not owner_decision.get("decisionRef"):
        raise RunnerError("matching recorded owner decision is required")
    candidate = dict(state, status="running")
    mission_work_timeout(candidate, 1)
    state.update(status="running", ownerDecision=copy.deepcopy(owner_decision), blocker=None)
    reservation.save()


def continue_mission(order: dict[str, Any], policy: PathPolicy, decision_path: Path) -> dict[str, Any]:
    """Apply an explicit owner decision without resetting effects or counters."""
    contract = require_object(order.get("loopContract"), "mission loopContract")
    path = _mission_path({"workspace": str(policy.repo_path)}, contract.get("statePath", ""))
    lock = LoopStateLock(loop_lock_path(path)).acquire()
    try:
        state, path = load_mission_state(order, policy)
        decision_path = policy.control_path(decision_path, "mission continuation decision")
        decision_ref = _mission_file_ref(decision_path)
        if decision_ref["bytes"] > 1024 * 1024:
            raise RunnerError("mission continuation decision exceeds size limit")
        decision = require_object(load_json(decision_path), "mission continuation decision")
        if (decision.get("version") != "CENTURION_MISSION_CONTINUATION_V1"
                or decision.get("missionId") != state["missionId"]
                or decision.get("approvalRef") != state["authority"]["approvalRef"]
                or decision.get("stateSha256") != _mission_file_ref(path)["sha256"]
                or not isinstance(decision.get("reason"), str) or not decision["reason"].strip()):
            raise RunnerError("continuation must bind the current mission, owner authority, state bytes and reason")
        legacy_budget_failure = state["status"] == "failed" and state.get("failure") == "mission model-launch budget exhausted"
        if state["cancelled"] or state.get("stopDeadlineAt") or (state["status"] in MISSION_TERMINAL and not legacy_budget_failure):
            raise RunnerError("continuation cannot reopen a cancelled, completed or failed product")
        for intent in state["intents"].values():
            if intent["status"] == "unknown_effect" or (
                    intent["status"] in {"reserved", "dispatching", "running"} and not intent.get("processStopped")):
                raise RunnerError("continuation requires reconciled, stopped effects")
            processes = ([intent["process"]] if intent.get("process") else []) + intent.get("proofProcesses", [])
            if any(_mission_process_identity(process["pid"]) == process for process in processes):
                raise RunnerError("continuation cannot race a live owned process")
            if intent["action"] == "product" and intent["status"] in {"reportable", "captured", "accepted"}:
                if workspace_snapshot(state) != intent["workspaceAfter"] and intent["status"] != "accepted":
                    raise RunnerError("product changed before continuation")
                for ref in intent.get("protocolRefs", {}).values():
                    if _mission_file_ref(Path(ref["path"])) != ref:
                        raise RunnerError("original protocol evidence changed before continuation")
        updated = copy.deepcopy(state)
        if "maxModelLaunches" in decision:
            maximum = _mission_int(decision["maxModelLaunches"], "continuation.maxModelLaunches", 1)
            if maximum < state["budget"]["maxModelLaunches"]:
                raise RunnerError("continuation cannot reduce or reset the approved launch budget")
            updated["budget"]["maxModelLaunches"] = maximum
        for key in ("reportCapabilityRef", "manualReportReviewRef"):
            if key in decision:
                if "report" not in state["authority"]["allowedActions"]:
                    raise RunnerError("continuation cannot add report authority")
                ref = require_object(decision[key], key)
                ref_path = policy.control_path(ref.get("path"), key) if key == "manualReportReviewRef" else Path(ref["path"])
                if _mission_file_ref(ref_path) != ref:
                    raise RunnerError("continuation report evidence reference changed")
                updated["authority"][key] = ref
        if "manualReportReviewRef" in decision:
            updated["authority"]["manualReportAuthorityRef"] = decision_ref
        updated["authoritySha256"] = _mission_digest(updated["authority"])
        updated.setdefault("continuations", []).append({"decisionRef": decision_ref,
            "previousStateSha256": decision["stateSha256"], "previousBudget": state["budget"], "at": utc_now()})
        updated.update(status="verifying" if any(i["status"] in {"reportable", "captured"} for i in updated["intents"].values()) else "running",
                       blocker=None)
        if legacy_budget_failure:
            updated.pop("failure", None)
        mission_work_timeout(updated, 1)  # Never extends an expired finite deadline.
        validate_mission_state(updated, path)
        atomic_write_loop_state(path, updated)
        return updated
    finally:
        lock.release()


def loop_result_metadata(result: dict[str, Any]) -> dict[str, Any]:
    extensions = require_object(result.get("executorExtensions"), "result.executorExtensions")
    metadata = require_object(extensions.get("aquilaLoop"), "result.executorExtensions.aquilaLoop")
    return metadata


def check_loop_budget(state: dict[str, Any]) -> None:
    iteration = state["iteration"]
    if iteration["current"] > iteration["max"]:
        raise RunnerError("loop iteration budget exhausted")
    started = state["budgets"].get("startedAt")
    if not isinstance(started, str):
        raise RunnerError("loop state budgets.startedAt must be a date-time string")
    try:
        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunnerError("loop state budgets.startedAt is invalid") from exc
    elapsed = (datetime.now(timezone.utc) - started_dt.astimezone(timezone.utc)).total_seconds()
    if elapsed >= state["budgets"]["maxWallSeconds"]:
        raise RunnerError("loop wall-time budget exhausted")


def prepare_loop_dispatch(order: dict[str, Any], policy: PathPolicy) -> tuple[dict[str, Any], Path]:
    if mission_context(order) is not None:
        raise RunnerError("policy 3.0 requires reserve_mission_dispatch; legacy Loop dispatch is disabled")
    contract = loop_contract(order)
    if contract is None:
        raise RunnerError("loopContract missing")
    state, state_path = load_loop_state(order, policy)
    if contract["phase"] == "execute":
        if state["workItem"]["status"] != "ready":
            raise RunnerError("execute phase requires loop state ready")
        check_loop_budget(state)
    else:
        if state["workItem"]["status"] != "awaiting_verification":
            raise RunnerError("verify phase requires loop state awaiting_verification")
        candidate = contract["candidate"]
        stored = state["candidate"]
        for key in ["orderId", "executor"]:
            if stored.get(key) != candidate[key]:
                raise RunnerError(f"loop/state candidate {key} mismatch")
        if not paths_equal(Path(stored.get("resultPath", "")), policy.resolve_under_repo(candidate["resultPath"])):
            raise RunnerError("loop/state candidate resultPath mismatch")
        if order["executor"] == stored.get("executor"):
            raise RunnerError("same-executor self-verification is not allowed")
        validate_loop_review_binding(order, policy, stored)
    return state, state_path


def validate_loop_review_binding(order: dict[str, Any], policy: PathPolicy, candidate: dict[str, Any]) -> None:
    """Keep review subordinate to the controller's accepted candidate and route."""
    routing = validate_order_routing(order)
    binding = candidate.get("reviewContract")
    digest = candidate.get("resultSha256")
    if digest is not None:
        candidate_path = Path(candidate["resultPath"]).expanduser()
        if not candidate_path.is_absolute():
            candidate_path = policy.repo_path / candidate_path
        try:
            require_no_symlink_components(candidate_path)
        except ArtifactNamespaceError as exc:
            raise RunnerError(f"loop candidate result path is unsafe: {exc}") from exc
        if result_digest(candidate_path) != digest:
            raise RunnerError("loop candidate result changed since controller acceptance")
    if binding is None:
        if routing is not None:
            raise RunnerError("loop candidate lacks controller reviewContract; restore it from accepted execution evidence")
        return  # Pre-cutover states retain their original contract.
    if not isinstance(binding, dict) or routing is None or digest is None:
        raise RunnerError("bound loop review requires routing metadata and candidate result digest")
    profile = binding.get("verificationProfile")
    if profile not in {"V1", "V2", "V3"} or binding.get("reviewer") != REVIEWER_BY_PROFILE[profile]:
        raise RunnerError("loop candidate reviewContract has an invalid reviewer/profile")
    if routing["executionProfile"] != "terminal_review":
        raise RunnerError("loop candidate requires a terminal review")
    for key in ("objectiveId", "taskClass"):
        if routing[key] != binding.get(key):
            raise RunnerError(f"loop reviewer {key} must match the accepted candidate")
    if PROFILE_RANK[routing["verificationProfile"]] < PROFILE_RANK[profile]:
        raise RunnerError("loop reviewer cannot lower the candidate verification profile")
    if routing["model"] != REVIEWER_BY_PROFILE[routing["verificationProfile"]]:
        raise RunnerError("loop reviewer model must match the controller-selected review route")


def update_loop_state_after_result(order: dict[str, Any], policy: PathPolicy, result: dict[str, Any], result_path: Path, events_path: Path) -> None:
    contract = loop_contract(order)
    if contract is None:
        return
    state, state_path = load_loop_state(order, policy)
    if contract["phase"] == "verify":
        # Recheck the reviewed bytes after the child and controller proofs ran.
        state, state_path = prepare_loop_dispatch(order, policy)
    metadata = loop_result_metadata(result)
    expected = {
        "loopId": contract["loopId"],
        "phase": contract["phase"],
        "workItemId": contract["workItem"]["workItemId"],
        "iteration": contract["iteration"]["current"],
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise RunnerError(f"executorExtensions.aquilaLoop.{key} does not match order")
    now = utc_now()
    current_status = state["workItem"]["status"]
    if contract["phase"] == "execute":
        if result["status"] != "done":
            state["workItem"]["status"] = "blocked"
            state["failures"].append({"at": now, "phase": "execute", "orderId": order["orderId"], "status": result["status"], "summary": result["summary"]})
            state["transitions"].append({"at": now, "from": current_status, "to": "blocked", "controller": "Aquila", "reason": "implementation result not done"})
        else:
            state["candidate"] = {"orderId": order["orderId"], "executor": order["executor"], "resultPath": str(result_path), "recordedAt": now}
            state["candidate"]["resultSha256"] = result_digest(result_path)
            routing = validate_order_routing(order)
            if routing is not None:
                state["candidate"]["reviewContract"] = {
                    key: routing[key] for key in ("objectiveId", "taskClass", "verificationProfile", "reviewer")
                }
            if routing is not None and routing["verificationProfile"] == "V0":
                state["verification"] = {
                    "status": "pass",
                    "verifierOrderId": order["orderId"],
                    "verifierExecutor": "Aquila",
                    "verdict": "pass",
                    "recordedAt": now,
                }
                state["workItem"]["status"] = "completed"
                state["transitions"].append({"at": now, "from": current_status, "to": "completed", "controller": "Aquila", "reason": "V0 deterministic artifact and proof gate passed; no reviewer launched"})
            else:
                state["verification"] = {"status": "pending"}
                state["workItem"]["status"] = "awaiting_verification"
                state["transitions"].append({"at": now, "from": current_status, "to": "awaiting_verification", "controller": "Aquila", "reason": "implementation accepted pending selected terminal verification"})
    else:
        verdict = metadata.get("verdict")
        if verdict not in {"pass", "fail", "blocked"}:
            raise RunnerError("verifier metadata verdict must be pass, fail, or blocked")
        if result["status"] != "done":
            raise RunnerError("verifier result must be done")
        state["verification"] = {"status": verdict, "verifierOrderId": order["orderId"], "verifierExecutor": order["executor"], "verdict": verdict, "recordedAt": now}
        target = "completed" if verdict == "pass" else "blocked"
        state["workItem"]["status"] = target
        state["transitions"].append({"at": now, "from": current_status, "to": target, "controller": "Aquila", "reason": f"independent verifier verdict {verdict}"})
        if verdict != "pass":
            state["failures"].append({"at": now, "phase": "verify", "orderId": order["orderId"], "status": verdict, "summary": result["summary"]})
    validate_loop_state(state, contract, state_path)
    atomic_write_loop_state(state_path, state)
    append_committed_loop_event(events_path, "aquila_loop_state_updated", orderId=order["orderId"], phase=contract["phase"], statePath=str(state_path), status=state["workItem"]["status"])


def block_loop_state_after_dispatch_failure(
    order: dict[str, Any],
    policy: PathPolicy,
    events_path: Path,
    error: RunnerError,
) -> None:
    contract = loop_contract(order)
    if contract is None:
        return
    state, state_path = load_loop_state(order, policy)
    current_status = state["workItem"]["status"]
    if current_status != "blocked":
        if current_status not in {"ready", "awaiting_verification"}:
            raise RunnerError(
                f"cannot block loop state after dispatch failure from status {current_status}"
            ) from error
        now = utc_now()
        state["workItem"]["status"] = "blocked"
        state["failures"].append(
            {
                "at": now,
                "phase": contract["phase"],
                "orderId": order["orderId"],
                "status": "failed",
                "summary": str(error),
            }
        )
        state["transitions"].append(
            {
                "at": now,
                "from": current_status,
                "to": "blocked",
                "controller": "Aquila",
                "reason": "post-dispatch gate failure",
            }
        )
        validate_loop_state(state, contract, state_path)
        atomic_write_loop_state(state_path, state)
    append_committed_loop_event(
        events_path,
        "aquila_loop_state_blocked_after_dispatch_failure",
        orderId=order["orderId"],
        phase=contract["phase"],
        statePath=str(state_path),
        status="blocked",
        error=str(error),
    )


def validate_runtime_paths(order: dict[str, Any], policy: PathPolicy, result_arg: Path, events_arg: Path) -> tuple[Path, Path]:
    result_path = policy.control_cli_path(result_arg, "CLI --result")
    events_path = policy.control_cli_path(events_arg, "CLI --events")
    launch_result = policy.control_path(order["launch"]["resultJsonPath"], "launch.resultJsonPath")
    contract_result = policy.control_path(order["outputContract"]["resultPath"], "outputContract.resultPath")
    if not paths_equal(result_path, launch_result) or not paths_equal(result_path, contract_result):
        raise RunnerError("CLI --result, launch.resultJsonPath, and outputContract.resultPath must resolve to the same path")
    return result_path, events_path


def plan_command(order: dict[str, Any]) -> list[str]:
    command = order["launch"]["command"]
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise RunnerError(f"launch.command cannot be parsed safely: {exc}") from exc
    if not argv:
        raise RunnerError("launch.command must not be empty")

    executor = order["executor"]
    first_token = Path(argv[0]).name
    if first_token not in ALLOWED_EXECUTORS:
        raise RunnerError(
            "launch.command first token must be an allowed executor: "
            + ", ".join(sorted(ALLOWED_EXECUTORS))
        )
    if first_token != executor:
        raise RunnerError(f"executor is {executor} but launch.command starts with {first_token}")
    return argv


def direct_response_paths(order: dict[str, Any], policy: PathPolicy, result_path: Path, events_path: Path) -> tuple[Path, Path] | None:
    """Opt-in ingress for direct surfaces; legacy canonical JSON stays strict."""
    declared = order["launch"].get("candidateJsonPath")
    if declared is None:
        return None
    raw_candidate = Path(declared).expanduser()
    if not raw_candidate.is_absolute():
        raw_candidate = policy.repo_path / raw_candidate
    if any(component.is_symlink() for component in (raw_candidate, *raw_candidate.parents)):
        raise RunnerError("direct response candidate path contains a symlink")
    candidate = policy.control_path(declared, "launch.candidateJsonPath")
    evidence = policy.control_namespace / "response-evidence"
    outputs = [result_path, events_path, candidate, evidence]
    outputs.extend(policy.control_path(order["launch"][key], key) for key in ("stdoutPath", "stderrPath") if key in order["launch"])
    if len(set(outputs)) != len(outputs) or any(evidence in path.parents for path in outputs):
        raise RunnerError("direct response candidate/evidence must be distinct from other outputs")
    for path in outputs:
        if any(component.is_symlink() for component in (path, *path.parents)):
            raise RunnerError("direct response output contains a symlink")
    for path in (candidate, result_path, evidence):
        if path.exists():
            raise RunnerError(f"direct response output already exists before launch: {path}")
    return candidate, evidence


def finalize_direct_response(order_path: Path, paths: tuple[Path, Path] | None, result_path: Path) -> None:
    if paths is None:
        return
    from agent_result_builder import BuilderError, build_result
    try:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        build_result(order_path, paths[0], result_path, paths[1])
    except (BuilderError, OSError) as exc:
        raise RunnerError(f"direct response finalization failed: {exc}") from exc


def run_command(order: dict[str, Any], argv: list[str], policy: PathPolicy) -> subprocess.CompletedProcess[str]:
    raise RunnerError("direct runner dispatch is disabled; legacy orders are read-only; use policy 3.0 result_gateway.py")
    timeout = order["launch"]["timeoutSeconds"]
    try:
        return subprocess.run(
            argv,
            cwd=policy.repo_path,
            timeout=timeout,
            check=False,
            text=True,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandTimeoutError(timeout, normalize_stream(exc.stdout), normalize_stream(exc.stderr)) from exc
    except OSError as exc:
        raise CommandStartError(f"executor command failed to start: {exc}") from exc


def write_captured_streams(order: dict[str, Any], completed: subprocess.CompletedProcess[str], policy: PathPolicy) -> None:
    launch = order["launch"]
    for key, content in [("stdoutPath", completed.stdout), ("stderrPath", completed.stderr)]:
        stream_path = launch.get(key)
        if stream_path is None:
            continue
        if not isinstance(stream_path, str) or not stream_path.strip():
            raise RunnerError(f"launch.{key} must be a non-empty string when present")
        path = policy.control_path(stream_path, f"launch.{key}")
        captured = normalize_stream(content)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(captured, encoding="utf-8")
        except OSError as exc:
            os_error = exc.strerror or type(exc).__name__
            if exc.errno is not None:
                os_error = f"[Errno {exc.errno}] {os_error}"
            raise RunnerError(f"stream capture failed for launch.{key} at {path}: {os_error}") from exc


def check_expected_artifacts(
    order: dict[str, Any],
    policy: PathPolicy,
    result_artifact_paths: list[Path],
    primary_result_path: Path,
) -> list[dict[str, Any]]:
    checks = []
    for index, artifact in enumerate(order["expectedArtifacts"]):
        path = policy.order_path(artifact["path"], f"expectedArtifacts[{index}].path")
        reported_by_result = any(paths_equal(path, result_path) for result_path in result_artifact_paths)
        result_artifact_match_required = not paths_equal(path, primary_result_path)
        checks.append(
            {
                "path": str(path),
                "type": artifact["type"],
                "required": artifact["required"],
                "exists": path.exists(),
                "reportedByResult": reported_by_result,
                "resultArtifactMatchRequired": result_artifact_match_required,
            }
        )
    return checks


def run_proof_commands(order: dict[str, Any], policy: PathPolicy, reservation: Any = None) -> list[dict[str, Any]]:
    if mission_context(order) is not None and reservation is None:
        raise RunnerError("3.0 proof dispatch is closed without the locked Gateway mission reservation")
    launch_timeout = order["launch"]["timeoutSeconds"]
    checks = []
    for index, proof in enumerate(order["proofCommands"]):
        if mission_context(order) is not None:
            state, _ = load_mission_state(order, policy)
            launch_timeout = mission_work_timeout(state, order["launch"]["timeoutSeconds"])
        command = proof["command"]
        cwd_path = _mission_path({"workspace":str(policy.repo_path)}, proof["cwd"]) if mission_context(order) is not None else policy.order_path(proof["cwd"], f"proofCommands[{index}].cwd")
        required = proof["required"]
        proof_argv = proof.get("argv")
        if loop_contract(order) is not None and proof_argv is None:
            raise RunnerError(f"proofCommands[{index}].argv is required for Loop V1 proof commands")
        check: dict[str, Any] = {
            "command": command,
            "cwd": str(cwd_path),
            "required": required,
            "status": "not_run",
            "exitCode": None,
            "summary": "not run",
        }
        if not cwd_path.is_dir():
            check["status"] = "fail"
            check["summary"] = f"cwd does not exist: {cwd_path}"
        else:
            try:
                if reservation is not None:
                    from result_gateway import run_child
                    observed = run_child(proof_argv, cwd_path, reservation.work_timeout(launch_timeout), 10,
                                         reservation=reservation, auxiliary=True)
                    if observed["error"] or not observed.get("processStopped"):
                        raise RunnerError("controller proof incomplete")
                    completed = subprocess.CompletedProcess(proof_argv, observed["exitCode"], observed["stdout"].decode(errors="replace"), observed["stderr"].decode(errors="replace"))
                elif proof_argv is None:
                    # Deprecated compatibility path for legacy non-loop orders only.
                    completed = subprocess.run(
                        command,
                        cwd=cwd_path,
                        timeout=launch_timeout,
                        check=False,
                        shell=True,
                        text=True,
                        capture_output=True,
                    )
                else:
                    completed = subprocess.run(
                        proof_argv,
                        cwd=cwd_path,
                        timeout=launch_timeout,
                        check=False,
                        shell=False,
                        text=True,
                        capture_output=True,
                    )
                check["exitCode"] = completed.returncode
                check["status"] = "pass" if completed.returncode == 0 else "fail"
                stdout_bytes = len(completed.stdout.encode("utf-8"))
                stderr_bytes = len(completed.stderr.encode("utf-8"))
                check["summary"] = f"exitCode={completed.returncode}; stdoutBytes={stdout_bytes}; stderrBytes={stderr_bytes}"
            except subprocess.TimeoutExpired:
                check["status"] = "fail"
                check["summary"] = f"timed out after {launch_timeout}s"
            except OSError as exc:
                check["status"] = "fail"
                check["summary"] = f"failed to start: {exc}"
        checks.append(check)
    return checks


def verify_required_artifact_checks(checks: list[dict[str, Any]]) -> None:
    missing_required = [check["path"] for check in checks if check["required"] and not check["exists"]]
    if missing_required:
        raise RunnerError("required expectedArtifacts missing: " + ", ".join(missing_required))
    unreported_required = [
        check["path"]
        for check in checks
        if check["required"]
        and check.get("resultArtifactMatchRequired", True)
        and not check["reportedByResult"]
    ]
    if unreported_required:
        raise RunnerError("required expectedArtifacts not reported by result artifacts: " + ", ".join(unreported_required))


def verify_required_proof_checks(checks: list[dict[str, Any]]) -> None:
    failed_required = [
        f"proofCommands[{index}] {check['command']}: {check['summary']}"
        for index, check in enumerate(checks)
        if check["required"] and check["status"] != "pass"
    ]
    if failed_required:
        raise RunnerError("required proofCommands failed: " + "; ".join(failed_required))


def verify_result(result_path: Path, order: dict[str, Any], policy: PathPolicy) -> tuple[dict[str, Any], list[Path]]:
    result = require_object(load_json(result_path), "result")
    try:
        routing_for_handoff = validate_order_routing(order)
    except RoutingError as exc:
        raise RunnerError(f"routing validation failed: {exc}") from exc
    handoff_errors = validate_response_handoff(result, order, routing_for_handoff) + response_state_errors(result)
    if handoff_errors:
        raise RunnerError("; ".join(handoff_errors))
    if result.get("resultVersion") != RESULT_VERSION:
        raise RunnerError(f"resultVersion must be {RESULT_VERSION}")
    if result.get("orderId") != order["orderId"]:
        raise RunnerError("result orderId does not match order")
    if result.get("executor") != order["executor"]:
        raise RunnerError("result executor does not match order")
    if not isinstance(result.get("status"), str) or result["status"] not in RESULT_STATUSES:
        raise RunnerError("result status must be done, blocked, or failed")
    if not isinstance(result.get("summary"), str):
        raise RunnerError("result summary must be a string")
    for key in REQUIRED_RESULT_LISTS:
        require_list(result, key)
    validate_files_changed(result["filesChanged"], policy)
    artifact_paths = validate_artifacts(result["artifacts"], policy, typed="handoff" in order["outputContract"])
    validate_response_envelope(result, policy, order)
    try:
        routing = validate_order_routing(order)
        validate_terminal_review_result(routing, result)
    except RoutingError as exc:
        raise RunnerError(f"result routing validation failed: {exc}") from exc
    if routing is not None and routing["executionProfile"] == "advisory":
        if result["filesChanged"]:
            raise RunnerError("Astra advisory filesChanged must be empty")
        for index, path in enumerate(artifact_paths):
            policy.control_path(path, f"Astra advisory artifacts[{index}]")
    validate_proof(result["proof"])
    if not result["artifacts"]:
        raise RunnerError("result artifacts must include at least one summary")
    if not result["proof"]:
        raise RunnerError("result proof must include at least one summary")
    self_review = require_object(result.get("selfReview"), "selfReview")
    if not isinstance(self_review.get("performed"), bool):
        raise RunnerError("selfReview.performed must be boolean")
    require_list(self_review, "findings")
    require_list(self_review, "fixesApplied")
    if not isinstance(result.get("stdoutSummary"), str):
        raise RunnerError("stdoutSummary must be a string")
    if not isinstance(result.get("stderrSummary"), str):
        raise RunnerError("stderrSummary must be a string")
    validate_done_semantics(result)
    return result, artifact_paths


def run_verification_gate(
    order: dict[str, Any],
    result_path: Path,
    events_path: Path | None,
    policy: PathPolicy,
    passed_event: str,
    evidence: dict[str, Any] | None = None,
    event_sink: Callable[..., None] | None = None,
    reservation: Any = None,
) -> dict[str, Any]:
    emit = event_sink or append_event
    result_sha256 = result_digest(result_path)
    mission = mission_context(order)
    product_before = None
    if mission is not None:
        state, _ = load_mission_state(order, policy)
        mission_work_timeout(state, order["launch"]["timeoutSeconds"])
        product_before = mission_snapshot(state, [mission["taskId"]])
    result, result_artifact_paths = verify_result(result_path, order, policy)
    artifact_checks = check_expected_artifacts(order, policy, result_artifact_paths, result_path)
    if evidence is not None:
        evidence["artifacts"] = artifact_checks
    emit(events_path, "expected_artifacts_checked", orderId=order["orderId"], artifacts=artifact_checks)
    verify_required_artifact_checks(artifact_checks)
    proof_checks = run_proof_commands(order, policy, reservation)
    if evidence is not None:
        evidence["proof"] = proof_checks
    emit(events_path, "proof_commands_checked", orderId=order["orderId"], proof=proof_checks)
    verify_required_proof_checks(proof_checks)
    # Proof commands can change evidence: validate its bytes again before acceptance.
    validate_response_envelope(result, policy, order)
    validate_artifacts(result["artifacts"], policy, typed="handoff" in order["outputContract"])
    try:
        checked_inputs = verify_input_results(order, policy.repo_path)
    except AcceptedInputError as exc:
        raise RunnerError(f"accepted input verification failed after proof: {exc}") from exc
    if evidence is not None:
        evidence["inputResults"] = checked_inputs
    routing = validate_order_routing(order)
    if routing is not None and routing["verificationProfile"] == "V0":
        # Honest risk disclosure is evidence for the owner, not an automatic
        # veto on the owner's selected deterministic verification profile.
        unresolved = [field for field in ("questions", "errors") if result[field]]
        if unresolved:
            raise RunnerError("V0 result has unresolved " + ", ".join(unresolved))
    if result_digest(result_path) != result_sha256:
        raise RunnerError("result bytes changed during controller verification")
    if mission is not None:
        state, _ = load_mission_state(order, policy)
        mission_work_timeout(state, 1)
        product_after = mission_snapshot(state, [mission["taskId"]])
        if product_before != product_after:
            raise RunnerError("product bytes changed during controller proof; reproof required")
        if evidence is not None:
            evidence["productSnapshotSha256"] = product_after["sha256"]
            evidence["criteria"] = list(state["tasks"][mission["taskId"]]["acceptanceCriteria"])
    if evidence is not None:
        evidence["resultSha256"] = result_sha256
    emit(events_path, passed_event, orderId=order["orderId"], resultStatus=result["status"])
    return result


def close_verified_direct_attempt(
    custody: dict[str, Any], result_path: Path, result: dict[str, Any], checks: dict[str, Any]
) -> dict[str, Any]:
    outcome = "passed" if result["status"] == "done" else "rejected"
    try:
        return close_direct_attempt(
            custody, result_path=result_path, outcome=outcome,
            result_status=result["status"], reason=None if outcome == "passed" else result["summary"],
            checks=checks, expected_result_sha256=checks["resultSha256"],
        )
    except (CustodyError, OSError) as exc:
        raise RunnerError(f"direct custody closure failed: {exc}") from exc


def commit_result_and_terminal(
    order: dict[str, Any], policy: PathPolicy, result: dict[str, Any], result_path: Path,
    events_path: Path, custody: dict[str, Any] | None,
) -> None:
    snapshot = LoopStateSnapshot(validate_loop_order(order, policy)) if loop_contract(order) is not None else None
    try:
        update_loop_state_after_result(order, policy, result, result_path, events_path)
        if custody is not None:
            try:
                finalize_direct_attempt(
                    custody, order_path=Path(custody["startPayload"]["orderPath"]), result_path=result_path,
                    status="passed" if result["status"] == "done" else "rejected",
                    reason=None if result["status"] == "done" else result["summary"],
                )
            except (CustodyError, OSError) as exc:
                raise RunnerError(f"direct terminal acceptance failed: {exc}") from exc
    except Exception:
        if snapshot is not None:
            snapshot.rollback()
        raise
    else:
        if snapshot is not None:
            snapshot.discard()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and run AGENT_ORDER_JSON_V1 handoffs.")
    parser.add_argument("--order", type=Path, help="Path to AGENT_ORDER_JSON_V1 order JSON")
    parser.add_argument("--init-mission", type=Path, help="Explicit approved mission preparation spec")
    parser.add_argument("--continue-mission", type=Path, help="Recorded owner decision bound to current state; no dispatch")
    parser.add_argument("--state", type=Path, help="State path for --init-mission")
    parser.add_argument("--complete-mission", type=Path, help="Controller final proof bound to integrated product bytes")
    parser.add_argument("--project-revision", help="Final accepted project revision")
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run", help="Dispatch mode")
    parser.add_argument("--events", type=Path, help="Append-only JSONL event log path")
    parser.add_argument("--result", type=Path, help="Expected AGENT_RESULT_JSON_V1 result path")
    parser.add_argument("--validate-only", action="store_true", help="Only validate the order")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.continue_mission is not None:
        if args.order is None or args.init_mission is not None or args.complete_mission is not None or args.mode != "dry-run" or args.validate_only:
            print("error: --continue-mission requires --order without dispatch or other mission operations", file=sys.stderr)
            return 2
        try:
            order = require_object(load_json(args.order), "order")
            _, policy = validate_order(order)
            state = continue_mission(order, policy, args.continue_mission)
            print(json.dumps({"status": state["status"], "missionId": state["missionId"], "modelLaunchesUsed": state["budget"]["modelLaunchesUsed"]}))
            return 0
        except (RunnerError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    if args.init_mission is not None:
        if args.order is not None or args.state is None or args.mode != "dry-run" or args.validate_only:
            print("error: --init-mission requires --state and cannot be combined with dispatch options", file=sys.stderr)
            return 2
        try:
            spec = require_object(load_json(args.init_mission), "mission preparation spec")
            state = initialize_mission(spec, args.state)
            print(json.dumps({"status": "prepared", "missionId": state["missionId"], "statePath": state["statePath"]}, sort_keys=True))
            return 0
        except (RunnerError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    if args.complete_mission is not None:
        if args.order is None or not args.project_revision or args.mode != "dry-run":
            print("error: --complete-mission requires --order and --project-revision without dispatch", file=sys.stderr)
            return 2
        try:
            order = require_object(load_json(args.order), "order")
            _, policy = validate_order(order)
            state = complete_mission(order, policy, require_object(load_json(args.complete_mission), "final proof"), args.project_revision)
            print(json.dumps({"status": state["status"], "missionId": state["missionId"]}, sort_keys=True))
            return 0
        except (RunnerError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    if args.order is None or args.events is None or args.result is None:
        print("error: --order, --events and --result are required for validation/dispatch", file=sys.stderr)
        return 2
    events_path = args.events
    loop_lock: LoopStateLock | None = None
    direct_custody: dict[str, Any] | None = None
    direct_result_status: str | None = None
    direct_checks: dict[str, Any] = {}
    direct_closed = False
    direct_terminal_written = False
    executor_ran = False
    event_sink_ready = False
    try:
        order = require_object(load_json(args.order), "order")
        notes, policy = validate_order(order)
        mission = mission_context(order)
        if args.mode == "run" and not args.validate_only:
            raise RunnerError("direct runner dispatch is disabled; legacy orders are read-only; use policy 3.0 result_gateway.py")
        result_path, events_path = validate_runtime_paths(order, policy, args.result, args.events)
        try:
            verify_input_results(order, policy.repo_path)
        except AcceptedInputError as exc:
            raise RunnerError(f"accepted input verification failed before launch: {exc}") from exc
        response_paths = direct_response_paths(order, policy, result_path, events_path)
        if args.mode == "run" and not args.validate_only and "lineage" in order:
            raise RunnerError("linked lineage dispatch requires result_gateway.py controller acceptance and receipts")
        if args.mode == "run" and not args.validate_only and order["executor"] == "codex":
            routing = validate_order_routing(order)
            if routing is not None and routing["executionProfile"] == "advisory":
                raise RunnerError("Astra advisory dispatch requires result_gateway.py custody receipts")
        append_event(events_path, "order_loaded", orderId=order.get("orderId"), executor=order.get("executor"), path=str(args.order))
        event_sink_ready = True
        append_event(events_path, "order_validated", orderId=order["orderId"], executor=order["executor"], notes=notes)

        if loop_contract(order) is not None:
            if mission is not None:
                state, _ = load_mission_state(order, policy)
                _validate_mission_scope(order, policy, state)
                mission_work_timeout(state, order["launch"]["timeoutSeconds"])
            elif args.mode == "run" and not args.validate_only:
                state_path = validate_loop_order(order, policy)
                loop_lock = LoopStateLock(loop_lock_path(state_path)).acquire()
                append_event(events_path, "aquila_loop_state_lock_acquired", orderId=order["orderId"], statePath=str(state_path), lockPath=str(loop_lock.path))
            if mission is None:
                prepare_loop_dispatch(order, policy)
            append_event(events_path, "aquila_loop_dispatch_preflight_passed", orderId=order["orderId"], phase=order["loopContract"]["phase"])

        if args.validate_only:
            append_event(events_path, "verification_skipped_or_not_run", orderId=order["orderId"], reason="validate_only")
            print(json.dumps({"status": "valid", "orderId": order["orderId"]}, sort_keys=True))
            return 0

        argv = plan_command(order)
        append_event(events_path, "dispatch_planned", orderId=order["orderId"], executor=order["executor"], mode=args.mode, argv=argv_summary(argv))
        print("planned command:", shlex.join(argv))

        if args.mode == "dry-run":
            append_event(events_path, "verification_skipped_or_not_run", orderId=order["orderId"], reason="dry_run")
            return 0

        append_event(events_path, "dispatch_started", orderId=order["orderId"], executor=order["executor"])
        if order["executor"] in {"codex", "claude"}:
            try:
                direct_custody = start_direct_attempt(
                    namespace=policy.control_namespace,
                    order_path=args.order,
                    order=order,
                    result_path=result_path,
                    argv=argv,
                )
            except CustodyError as exc:
                raise RunnerError(str(exc)) from exc
            append_event(
                events_path, "direct_custody_started", orderId=order["orderId"],
                startReceiptPath=str(direct_custody["start"]),
                startReceiptSha256=direct_custody["startSha256"],
                closurePath=str(direct_custody["closure"]),
                terminalPath=str(direct_custody["terminal"]),
            )
        try:
            prepare_order_namespace(policy)
            completed = run_command(order, argv, policy)
        except CommandTimeoutError as exc:
            executor_ran = True
            append_event(
                events_path,
                "dispatch_timed_out",
                orderId=order["orderId"],
                executor=order["executor"],
                argv=argv_summary(argv),
                timeoutSeconds=exc.timeout,
                stdoutBytes=len(exc.stdout.encode("utf-8")),
                stderrBytes=len(exc.stderr.encode("utf-8")),
            )
            partial = subprocess.CompletedProcess(argv, returncode=-1, stdout=exc.stdout, stderr=exc.stderr)
            write_captured_streams(order, partial, policy)
            try:
                finalize_direct_response(args.order, response_paths, result_path)
                result = run_verification_gate(order, result_path, events_path, policy, "salvage_verification_passed", direct_checks)
                direct_result_status = result["status"]
                if direct_custody is not None:
                    closure = close_verified_direct_attempt(direct_custody, result_path, result, direct_checks)
                    direct_closed = True
                    if closure["controllerVerification"] != ("passed" if result["status"] == "done" else "rejected"):
                        raise RunnerError("direct result changed after proof and before custody closure")
                commit_result_and_terminal(order, policy, result, result_path, events_path, direct_custody)
                direct_terminal_written = direct_custody is not None
            except RunnerError as salvage_exc:
                append_event(
                    events_path,
                    "salvage_verification_failed",
                    orderId=order["orderId"],
                    executor=order["executor"],
                    error=str(salvage_exc),
                )
                raise
            print(json.dumps({"status": "accepted", "resultStatus": result["status"], "orderId": order["orderId"]}, sort_keys=True))
            return 0 if result["status"] == "done" else 2
        executor_ran = True
        append_event(
            events_path,
            "dispatch_finished",
            orderId=order["orderId"],
            executor=order["executor"],
            argv=argv_summary(argv),
            exitCode=completed.returncode,
            stdoutBytes=len(completed.stdout.encode("utf-8")),
            stderrBytes=len(completed.stderr.encode("utf-8")),
        )
        write_captured_streams(order, completed, policy)
        finalize_direct_response(args.order, response_paths, result_path)
        result = run_verification_gate(order, result_path, events_path, policy, "verification_passed", direct_checks)
        direct_result_status = result["status"]
        if direct_custody is not None:
            closure = close_verified_direct_attempt(direct_custody, result_path, result, direct_checks)
            direct_closed = True
            if closure["controllerVerification"] != ("passed" if result["status"] == "done" else "rejected"):
                raise RunnerError("direct result changed after proof and before custody closure")
        commit_result_and_terminal(order, policy, result, result_path, events_path, direct_custody)
        direct_terminal_written = direct_custody is not None
        print(json.dumps({"status": "accepted", "resultStatus": result["status"], "orderId": order["orderId"]}, sort_keys=True))
        return 0 if result["status"] == "done" else 2
    except (RunnerError, OSError) as caught:
        # Filesystem failures must enter the same custody closure path as
        # validation failures; otherwise a start receipt can be orphaned.
        exc = caught if isinstance(caught, RunnerError) else RunnerError(str(caught))
        if direct_custody is not None and not direct_closed:
            try:
                close_direct_attempt(
                    direct_custody, result_path=result_path, outcome="rejected",
                    result_status=direct_result_status, reason=str(exc), checks=direct_checks,
                    expected_result_sha256=direct_checks.get("resultSha256"),
                )
                direct_closed = True
            except (CustodyError, OSError) as custody_exc:
                print(f"direct custody closure failed: {custody_exc}", file=sys.stderr)
        if direct_custody is not None and direct_closed and not direct_terminal_written:
            try:
                finalize_direct_attempt(
                    direct_custody, order_path=args.order, result_path=result_path,
                    status="rejected", reason=str(exc),
                )
                direct_terminal_written = True
            except (CustodyError, OSError) as custody_exc:
                print(f"direct terminal acceptance failed: {custody_exc}", file=sys.stderr)
        order_id = None
        executor = None
        try:
            if "order" in locals() and isinstance(order, dict):
                order_id = order.get("orderId")
                executor = order.get("executor")
                if executor_ran and loop_lock is not None and "policy" in locals():
                    block_loop_state_after_dispatch_failure(order, policy, events_path, exc)
        finally:
            if event_sink_ready:
                append_committed_loop_event(
                    events_path,
                    "verification_failed",
                    orderId=order_id,
                    executor=executor,
                    error=str(exc),
                )
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        if loop_lock is not None:
            loop_lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
