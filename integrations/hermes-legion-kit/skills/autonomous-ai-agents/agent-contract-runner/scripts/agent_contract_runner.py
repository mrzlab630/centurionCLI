#!/usr/bin/env python3
"""Small AGENT_ORDER_JSON_V1 runner for local Aquila/Hermes delegation."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attempt_ledger import LedgerError, load_attempt_history
from review_ladder import RoutingError, validate_order_routing
from strict_json import StrictJSONError, strict_json_load_path


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


class PathPolicy:
    """Resolve order paths and enforce exact / trailing-** path rules."""

    def __init__(self, repo_path: Path, allowed_paths: list[Any], forbidden_paths: list[Any]) -> None:
        self.repo_path = repo_path.expanduser().resolve()
        if not self.repo_path.is_dir():
            raise RunnerError(f"workspace.repoPath must be an existing directory: {self.repo_path}")
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_event(events_path: Path, event: str, **payload: Any) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": utc_now(), "event": event, **payload}
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


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


def validate_artifacts(items: list[Any], policy: PathPolicy) -> list[Path]:
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
    return artifact_paths


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
        if not isinstance(proof_obj.get("exitCode"), int) and proof_obj.get("exitCode") is not None:
            raise RunnerError(f"proof[{index}].exitCode must be integer or null")
        require_string_value(proof_obj, "summary", f"proof[{index}].summary")


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

    for key in ["orderId", "createdAt", "roleForTask", "objective"]:
        require_nonempty_string(order, key)
    require_order_lists(order)

    workspace = require_object(order["workspace"], "workspace")
    for key in ["repoPath", "branchOrWorktree", "projectName"]:
        require_nonempty_string(workspace, key, f"workspace.{key}")
    policy = PathPolicy(Path(workspace["repoPath"]), order["allowedPaths"], order["forbiddenPaths"])

    launch = require_object(order["launch"], "launch")
    for key in ["surface", "command", "resultJsonPath"]:
        require_nonempty_string(launch, key, f"launch.{key}")
    if not isinstance(launch.get("timeoutSeconds"), int) or launch["timeoutSeconds"] < 1:
        raise RunnerError("launch.timeoutSeconds must be a positive integer")
    policy.order_path(launch["resultJsonPath"], "launch.resultJsonPath")
    for key in ["stdoutPath", "stderrPath"]:
        if key in launch:
            if not isinstance(launch.get(key), str) or not launch[key].strip():
                raise RunnerError(f"launch.{key} must be a non-empty string when present")
            policy.order_path(launch[key], f"launch.{key}")

    output_contract = require_object(order["outputContract"], "outputContract")
    if output_contract.get("resultVersion") != RESULT_VERSION:
        raise RunnerError(f"outputContract.resultVersion must be {RESULT_VERSION}")
    require_nonempty_string(output_contract, "resultPath", "outputContract.resultPath")
    policy.order_path(output_contract["resultPath"], "outputContract.resultPath")
    if not isinstance(output_contract.get("stdoutAllowed"), bool):
        raise RunnerError("outputContract.stdoutAllowed must be boolean")
    if "proseAllowedAfterJson" not in output_contract:
        raise RunnerError("outputContract must include proseAllowedAfterJson")
    if not isinstance(output_contract["proseAllowedAfterJson"], bool):
        raise RunnerError("outputContract.proseAllowedAfterJson must be boolean")

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
        cwd = policy.order_path(proof_obj["cwd"], f"proofCommands[{index}].cwd")
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
        notes.append(
            "aquila_routing_validated:"
            f"{routing['verificationProfile']}:{routing['reviewer']}:{routing['executionProfile']}"
        )
    if "loopContract" in order:
        if routing is not None:
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
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


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
    return state, state_path


def update_loop_state_after_result(order: dict[str, Any], policy: PathPolicy, result: dict[str, Any], result_path: Path, events_path: Path) -> None:
    contract = loop_contract(order)
    if contract is None:
        return
    state, state_path = load_loop_state(order, policy)
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
            routing = validate_order_routing(order)
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
    append_event(events_path, "aquila_loop_state_updated", orderId=order["orderId"], phase=contract["phase"], statePath=str(state_path), status=state["workItem"]["status"])


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
    append_event(
        events_path,
        "aquila_loop_state_blocked_after_dispatch_failure",
        orderId=order["orderId"],
        phase=contract["phase"],
        statePath=str(state_path),
        status="blocked",
        error=str(error),
    )


def validate_runtime_paths(order: dict[str, Any], policy: PathPolicy, result_arg: Path, events_arg: Path) -> tuple[Path, Path]:
    result_path = policy.cli_path(result_arg, "CLI --result")
    events_path = policy.cli_path(events_arg, "CLI --events")
    launch_result = policy.order_path(order["launch"]["resultJsonPath"], "launch.resultJsonPath")
    contract_result = policy.order_path(order["outputContract"]["resultPath"], "outputContract.resultPath")
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


def run_command(order: dict[str, Any], argv: list[str], policy: PathPolicy) -> subprocess.CompletedProcess[str]:
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
        path = policy.order_path(stream_path, f"launch.{key}")
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


def run_proof_commands(order: dict[str, Any], policy: PathPolicy) -> list[dict[str, Any]]:
    launch_timeout = order["launch"]["timeoutSeconds"]
    checks = []
    for index, proof in enumerate(order["proofCommands"]):
        command = proof["command"]
        cwd_path = policy.order_path(proof["cwd"], f"proofCommands[{index}].cwd")
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
                if proof_argv is None:
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
    if result.get("resultVersion") != RESULT_VERSION:
        raise RunnerError(f"resultVersion must be {RESULT_VERSION}")
    if result.get("orderId") != order["orderId"]:
        raise RunnerError("result orderId does not match order")
    if result.get("executor") != order["executor"]:
        raise RunnerError("result executor does not match order")
    if result.get("status") not in RESULT_STATUSES:
        raise RunnerError("result status must be done, blocked, or failed")
    if not isinstance(result.get("summary"), str):
        raise RunnerError("result summary must be a string")
    for key in REQUIRED_RESULT_LISTS:
        require_list(result, key)
    validate_files_changed(result["filesChanged"], policy)
    artifact_paths = validate_artifacts(result["artifacts"], policy)
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
    return result, artifact_paths


def run_verification_gate(
    order: dict[str, Any],
    result_path: Path,
    events_path: Path,
    policy: PathPolicy,
    passed_event: str,
) -> dict[str, Any]:
    result, result_artifact_paths = verify_result(result_path, order, policy)
    artifact_checks = check_expected_artifacts(order, policy, result_artifact_paths, result_path)
    append_event(events_path, "expected_artifacts_checked", orderId=order["orderId"], artifacts=artifact_checks)
    verify_required_artifact_checks(artifact_checks)
    proof_checks = run_proof_commands(order, policy)
    append_event(events_path, "proof_commands_checked", orderId=order["orderId"], proof=proof_checks)
    verify_required_proof_checks(proof_checks)
    append_event(events_path, passed_event, orderId=order["orderId"], resultStatus=result["status"])
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and run AGENT_ORDER_JSON_V1 handoffs.")
    parser.add_argument("--order", required=True, type=Path, help="Path to AGENT_ORDER_JSON_V1 order JSON")
    parser.add_argument("--mode", choices=["dry-run", "run"], default="dry-run", help="Dispatch mode")
    parser.add_argument("--events", required=True, type=Path, help="Append-only JSONL event log path")
    parser.add_argument("--result", required=True, type=Path, help="Expected AGENT_RESULT_JSON_V1 result path")
    parser.add_argument("--validate-only", action="store_true", help="Only validate the order")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    events_path = args.events
    loop_lock: LoopStateLock | None = None
    executor_ran = False
    try:
        order = require_object(load_json(args.order), "order")
        notes, policy = validate_order(order)
        result_path, events_path = validate_runtime_paths(order, policy, args.result, args.events)
        append_event(events_path, "order_loaded", orderId=order.get("orderId"), executor=order.get("executor"), path=str(args.order))
        append_event(events_path, "order_validated", orderId=order["orderId"], executor=order["executor"], notes=notes)

        if loop_contract(order) is not None:
            if args.mode == "run" and not args.validate_only:
                state_path = validate_loop_order(order, policy)
                loop_lock = LoopStateLock(loop_lock_path(state_path)).acquire()
                append_event(events_path, "aquila_loop_state_lock_acquired", orderId=order["orderId"], statePath=str(state_path), lockPath=str(loop_lock.path))
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
        try:
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
                result = run_verification_gate(order, result_path, events_path, policy, "salvage_verification_passed")
                update_loop_state_after_result(order, policy, result, result_path, events_path)
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
        result = run_verification_gate(order, result_path, events_path, policy, "verification_passed")
        update_loop_state_after_result(order, policy, result, result_path, events_path)
        print(json.dumps({"status": "accepted", "resultStatus": result["status"], "orderId": order["orderId"]}, sort_keys=True))
        return 0 if result["status"] == "done" else 2
    except RunnerError as exc:
        order_id = None
        executor = None
        try:
            if "order" in locals() and isinstance(order, dict):
                order_id = order.get("orderId")
                executor = order.get("executor")
                if executor_ran and loop_lock is not None and "policy" in locals():
                    block_loop_state_after_dispatch_failure(order, policy, events_path, exc)
        finally:
            append_event(events_path, "verification_failed", orderId=order_id, executor=executor, error=str(exc))
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        if loop_lock is not None:
            loop_lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
