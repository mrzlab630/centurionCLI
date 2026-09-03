#!/usr/bin/env python3
"""Read-only, fail-closed projection of AGENT_ORDER/RESULT execution state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from strict_json import StrictJSONError, strict_json_load_path

STATE_VERSION = "AQUILA_EXECUTION_STATE_V1"
MAX_STATE_BYTES = 16 * 1024
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_REFS = 32
MAX_STRING = 512
MAX_SUMMARY_BYTES = 512
SUMMARY_OMISSION_REASON = "result-summary-over-bound"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SECRET_KEY_RE = re.compile(r"(?:secret|token|password|api[_-]?key|authorization|bearer|cookie|credential)", re.I)
PHASES = {"execute", "verify"}
STATUSES = {"planned", "running", "awaiting_verification", "completed", "blocked", "failed"}
TERMINAL_STATUSES = {"completed", "blocked", "failed"}
PROVENANCE_MODES = {"read-only-derived", "read-only-derived-legacy-terminal"}
PHASE_STATUSES = {
    "execute": {"planned", "running", "awaiting_verification"},
    "verify": {"awaiting_verification", "completed", "blocked", "failed"},
}
TRANSITIONS = {
    "planned": {"planned", "running", "blocked", "failed"},
    "running": {"running", "awaiting_verification", "completed", "blocked", "failed"},
    "awaiting_verification": {"awaiting_verification", "completed", "blocked", "failed"},
    "completed": {"completed"},
    "blocked": {"blocked"},
    "failed": {"failed"},
}
PHASE_TRANSITIONS = {
    ("execute", "execute"): True,
    ("execute", "verify"): True,
    ("verify", "verify"): True,
}


class ExecutionStateError(ValueError):
    """Raised for malformed, ambiguous, stale, or out-of-scope state."""


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExecutionStateError(f"{context} must be an object")
    return value


def _string(value: Any, context: str, *, max_length: int = MAX_STRING) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ExecutionStateError(f"{context} must be a non-empty string of at most {max_length} bytes")
    return value


def _strict_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ExecutionStateError(f"{context} contains unknown keys: {', '.join(unknown)}")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_json(path: Path, context: str) -> tuple[Any, bytes]:
    content = path.read_bytes()
    if len(content) > MAX_INPUT_BYTES:
        raise ExecutionStateError(f"{context} exceeds {MAX_INPUT_BYTES} bytes")
    try:
        return strict_json_load_path(path, context), content
    except (StrictJSONError, OSError) as exc:
        raise ExecutionStateError(str(exc)) from exc


def _source(kind: str, path: Path, content: bytes) -> dict[str, Any]:
    return {"kind": kind, "path": str(path.resolve()), "sha256": _sha256_bytes(content), "bytes": len(content)}


def _scope_from_order(order: dict[str, Any]) -> dict[str, str]:
    loop = order.get("loopContract")
    work = loop.get("workItem") if isinstance(loop, dict) else None
    work = work if isinstance(work, dict) else {}
    workspace = order.get("workspace") if isinstance(order.get("workspace"), dict) else {}
    project = work.get("project") or order.get("project") or workspace.get("projectName")
    objective = work.get("objective") or order.get("objective") or order.get("objectiveId")
    work_item = work.get("workItemId") or order.get("workItemId") or order.get("orderId")
    order_id = order.get("orderId")
    return {
        "project": _string(project, "scope.project"),
        "objective": _string(objective, "scope.objective"),
        "workItemId": _string(work_item, "scope.workItemId"),
        "orderId": _string(order_id, "scope.orderId"),
    }


def _status_from_inputs(
    order: dict[str, Any], result: dict[str, Any] | None, *, legacy_terminal_compat: bool = False
) -> tuple[str, str, str | None, str | None]:
    loop = order.get("loopContract")
    phase = loop.get("phase", "execute") if isinstance(loop, dict) else "execute"
    if legacy_terminal_compat:
        phase = "verify"
    if phase not in PHASES:
        raise ExecutionStateError("execution.phase must be execute or verify")
    executor = result.get("executor") if result else order.get("executor")
    if executor is not None:
        executor = _string(executor, "execution.executor", max_length=128)
    summary = result.get("summary") if result else None
    if summary is not None:
        summary = _string(summary, "execution.summary", max_length=MAX_INPUT_BYTES)
    loop_status = None
    if isinstance(loop, dict) and isinstance(loop.get("workItem"), dict) and loop["workItem"].get("status"):
        raw = loop["workItem"]["status"]
        mapping = {"ready": "planned", "awaiting_verification": "awaiting_verification", "completed": "completed", "blocked": "blocked"}
        if raw not in mapping:
            raise ExecutionStateError(f"unsupported loop workItem.status: {raw!r}")
        loop_status = mapping[raw]
        if loop_status not in PHASE_STATUSES[phase]:
            raise ExecutionStateError(f"incoherent phase/status pair: {phase}+{loop_status}")
    if result is None:
        status = loop_status or "planned"
        if status not in PHASE_STATUSES[phase]:
            raise ExecutionStateError(f"incoherent phase/status pair: {phase}+{status}")
        return phase, status, executor, summary
    status = result.get("status")
    if status == "done":
        result_status = "completed"
    elif status in {"blocked", "failed"}:
        result_status = status
    else:
        raise ExecutionStateError("result.status must be done, blocked, or failed")
    if result_status not in PHASE_STATUSES[phase]:
        raise ExecutionStateError(f"incoherent phase/status pair: {phase}+{result_status}")
    if loop_status is not None and loop_status != result_status:
        raise ExecutionStateError("loop and result status disagree")
    return phase, result_status, executor, summary


def _legacy_terminal_compatibility(
    order: dict[str, Any], result: dict[str, Any] | None, parent_path: Path | None, requested: bool
) -> bool:
    if not requested:
        return False
    if result is None:
        raise ExecutionStateError("legacy terminal compatibility requires a canonical result")
    if parent_path is not None:
        raise ExecutionStateError("legacy terminal compatibility cannot use a parent state")
    loop = order.get("loopContract")
    if isinstance(loop, dict) and "phase" in loop and loop.get("phase") != "verify":
        raise ExecutionStateError("legacy terminal compatibility rejects a contradictory explicit lifecycle phase")
    if isinstance(loop, dict) and isinstance(loop.get("workItem"), dict) and "status" in loop["workItem"]:
        raise ExecutionStateError("legacy terminal compatibility requires implicit lifecycle metadata")
    if result.get("status") not in {"done", "blocked", "failed"}:
        raise ExecutionStateError("legacy terminal compatibility requires a terminal result status")
    return True


def _utf8_bytes(value: str, context: str) -> int:
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ExecutionStateError(f"{context} must contain valid UTF-8 text") from exc


def _bounded_summary(summary: str | None) -> tuple[str | None, dict[str, Any] | None]:
    if summary is None:
        return None, None
    source_bytes = _utf8_bytes(summary, "execution.summary")
    if source_bytes > MAX_SUMMARY_BYTES:
        return None, {"reason": SUMMARY_OMISSION_REASON, "sourceBytes": source_bytes}
    return summary, None


def _validate_scope(scope: dict[str, Any], expected: dict[str, str], context: str) -> None:
    _strict_keys(scope, set(expected), context)
    for key, value in expected.items():
        if scope.get(key) != value:
            raise ExecutionStateError(f"{context}.{key} does not match order scope")


def _evidence_refs(value: Any, scope: dict[str, str]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_EVIDENCE_REFS:
        raise ExecutionStateError(f"evidence references must be a list of at most {MAX_EVIDENCE_REFS} items")
    refs: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        obj = _object(item, f"evidence[{index}]")
        _strict_keys(obj, {"kind", "path", "sha256", "bytes", "scope"}, f"evidence[{index}]")
        if any(SECRET_KEY_RE.search(str(key)) for key in obj):
            raise ExecutionStateError(f"evidence[{index}] contains secret-like key")
        kind = _string(obj.get("kind"), f"evidence[{index}].kind", max_length=64)
        path = _string(obj.get("path"), f"evidence[{index}].path", max_length=1024)
        digest = _string(obj.get("sha256"), f"evidence[{index}].sha256", max_length=64)
        if not SHA256_RE.fullmatch(digest):
            raise ExecutionStateError(f"evidence[{index}].sha256 must be lowercase SHA-256")
        size = obj.get("bytes", 0)
        if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_INPUT_BYTES:
            raise ExecutionStateError(f"evidence[{index}].bytes is invalid")
        ref_scope = _object(obj.get("scope"), f"evidence[{index}].scope")
        _validate_scope(ref_scope, scope, f"evidence[{index}].scope")
        refs.append({"kind": kind, "path": path, "sha256": digest, "bytes": size})
    return refs


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def validate_state(
    state: Any,
    *,
    parent: Any = None,
    parent_bytes: bytes | None = None,
    _allow_unbound_revision: bool = False,
) -> dict[str, Any]:
    obj = _object(state, "state")
    _strict_keys(obj, {"stateVersion", "scope", "execution", "revision", "provenance"}, "state")
    if obj.get("stateVersion") != STATE_VERSION:
        raise ExecutionStateError(f"stateVersion must be {STATE_VERSION}")
    scope = _object(obj.get("scope"), "state.scope")
    _strict_keys(scope, {"project", "objective", "workItemId", "orderId"}, "state.scope")
    for key in scope:
        _string(scope[key], f"state.scope.{key}")
    execution = _object(obj.get("execution"), "state.execution")
    _strict_keys(execution, {"phase", "status", "executor", "iteration", "summary", "summaryOmitted"}, "state.execution")
    if execution.get("phase") not in PHASES or execution.get("status") not in STATUSES:
        raise ExecutionStateError("state.execution phase/status is invalid")
    if execution["status"] not in PHASE_STATUSES[execution["phase"]]:
        raise ExecutionStateError(f"incoherent phase/status pair: {execution['phase']}+{execution['status']}")
    if "executor" in execution and execution["executor"] is not None:
        _string(execution["executor"], "state.execution.executor", max_length=128)
    if "summary" in execution and execution["summary"] is not None:
        summary = _string(execution["summary"], "state.execution.summary", max_length=MAX_INPUT_BYTES)
        if _utf8_bytes(summary, "state.execution.summary") > MAX_SUMMARY_BYTES:
            raise ExecutionStateError("state.execution.summary exceeds 512 UTF-8 bytes")
    if "summary" in execution and "summaryOmitted" in execution:
        raise ExecutionStateError("state.execution cannot contain summary and summaryOmitted")
    if "summaryOmitted" in execution:
        omitted = _object(execution["summaryOmitted"], "state.execution.summaryOmitted")
        _strict_keys(omitted, {"reason", "sourceBytes"}, "state.execution.summaryOmitted")
        if omitted.get("reason") != SUMMARY_OMISSION_REASON:
            raise ExecutionStateError(f"state.execution.summaryOmitted.reason must be {SUMMARY_OMISSION_REASON}")
        source_bytes = omitted.get("sourceBytes")
        if (
            not isinstance(source_bytes, int)
            or isinstance(source_bytes, bool)
            or source_bytes <= MAX_SUMMARY_BYTES
            or source_bytes > MAX_INPUT_BYTES
        ):
            raise ExecutionStateError("state.execution.summaryOmitted.sourceBytes is invalid")
    if "iteration" in execution and execution["iteration"] is not None:
        iteration = execution["iteration"]
        if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 0 or iteration > 1000000:
            raise ExecutionStateError("state.execution.iteration is invalid")
    revision = _object(obj.get("revision"), "state.revision")
    _strict_keys(revision, {"sequence", "orderSha256", "resultSha256", "parentSha256"}, "state.revision")
    sequence = revision.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise ExecutionStateError("state.revision.sequence is invalid")
    order_digest = revision.get("orderSha256")
    if not isinstance(order_digest, str) or not SHA256_RE.fullmatch(order_digest):
        raise ExecutionStateError("state.revision.orderSha256 must be a required lowercase SHA-256")
    for key in ("resultSha256", "parentSha256"):
        value = revision.get(key)
        if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
            raise ExecutionStateError(f"state.revision.{key} must be lowercase SHA-256 or null")
    parent_hash = revision.get("parentSha256")
    if sequence == 0 and parent_hash is not None:
        raise ExecutionStateError("state.revision.sequence 0 cannot carry a parent hash")
    if sequence > 0 and parent_hash is None:
        raise ExecutionStateError("state.revision.nonzero sequence requires a parent hash")
    if sequence > 0 and parent is None and not _allow_unbound_revision:
        raise ExecutionStateError("state.revision.nonzero sequence requires an explicit parent state")
    if "summaryOmitted" in execution and revision.get("resultSha256") is None:
        raise ExecutionStateError("state.execution.summaryOmitted requires a result source hash")
    provenance = _object(obj.get("provenance"), "state.provenance")
    _strict_keys(provenance, {"mode", "sources", "evidence"}, "state.provenance")
    mode = provenance.get("mode")
    if mode not in PROVENANCE_MODES:
        raise ExecutionStateError("state.provenance.mode is invalid")
    if mode == "read-only-derived-legacy-terminal":
        if execution["phase"] != "verify" or execution["status"] not in TERMINAL_STATUSES:
            raise ExecutionStateError("legacy terminal provenance requires a verify terminal snapshot")
        if revision.get("sequence") != 0 or revision.get("parentSha256") is not None:
            raise ExecutionStateError("legacy terminal provenance cannot carry a parent transition")
        if revision.get("resultSha256") is None:
            raise ExecutionStateError("legacy terminal provenance requires a result source")
    sources = provenance.get("sources")
    if not isinstance(sources, list) or not (1 <= len(sources) <= 34):
        raise ExecutionStateError("state.provenance.sources must contain 1 to 34 items")
    for index, source in enumerate(sources):
        source_obj = _object(source, f"state.provenance.sources[{index}]")
        _strict_keys(source_obj, {"kind", "path", "sha256", "bytes"}, f"state.provenance.sources[{index}]")
        _string(source_obj.get("kind"), f"state.provenance.sources[{index}].kind", max_length=64)
        _string(source_obj.get("path"), f"state.provenance.sources[{index}].path", max_length=1024)
        if not SHA256_RE.fullmatch(str(source_obj.get("sha256", ""))):
            raise ExecutionStateError(f"state.provenance.sources[{index}].sha256 is invalid")
        if not isinstance(source_obj.get("bytes"), int) or isinstance(source_obj["bytes"], bool) or source_obj["bytes"] < 0 or source_obj["bytes"] > MAX_INPUT_BYTES:
            raise ExecutionStateError(f"state.provenance.sources[{index}].bytes is invalid")
    evidence = provenance.get("evidence", [])
    if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE_REFS:
        raise ExecutionStateError("state.provenance.evidence exceeds limit")
    for index, ref in enumerate(evidence):
        ref_obj = _object(ref, f"state.provenance.evidence[{index}]")
        _strict_keys(ref_obj, {"kind", "path", "sha256", "bytes"}, f"state.provenance.evidence[{index}]")
        _string(ref_obj.get("kind"), f"state.provenance.evidence[{index}].kind", max_length=64)
        _string(ref_obj.get("path"), f"state.provenance.evidence[{index}].path", max_length=1024)
        if not SHA256_RE.fullmatch(str(ref_obj.get("sha256", ""))):
            raise ExecutionStateError(f"state.provenance.evidence[{index}].sha256 is invalid")
        if not isinstance(ref_obj.get("bytes"), int) or isinstance(ref_obj["bytes"], bool) or ref_obj["bytes"] < 0 or ref_obj["bytes"] > MAX_INPUT_BYTES:
            raise ExecutionStateError(f"state.provenance.evidence[{index}].bytes is invalid")
    if parent is not None:
        if mode == "read-only-derived-legacy-terminal":
            raise ExecutionStateError("legacy terminal provenance cannot use a parent state")
        parent_obj = validate_state(parent, _allow_unbound_revision=True)
        if parent_obj["scope"] != scope:
            raise ExecutionStateError("parent state scope does not match")
        if sequence != parent_obj["revision"]["sequence"] + 1:
            raise ExecutionStateError("state revision is stale")
        if parent_bytes is None:
            parent_bytes = _canonical_bytes(parent_obj)
        if revision.get("parentSha256") != _sha256_bytes(parent_bytes):
            raise ExecutionStateError("state parent hash is stale or mismatched")
        if not PHASE_TRANSITIONS.get((parent_obj["execution"]["phase"], execution["phase"]), False):
            raise ExecutionStateError("invalid phase transition")
        if execution["phase"] == "verify" and parent_obj["execution"]["phase"] == "execute" and parent_obj["execution"]["status"] != "awaiting_verification":
            raise ExecutionStateError("execute to verify requires awaiting_verification")
        if execution["status"] not in TRANSITIONS[parent_obj["execution"]["status"]]:
            raise ExecutionStateError("invalid phase/status transition")
    encoded = _canonical_bytes(obj)
    if len(encoded) + 1 > MAX_STATE_BYTES:
        raise ExecutionStateError(f"state exceeds {MAX_STATE_BYTES} bytes")
    return obj


def project(
    order_path: Path,
    result_path: Path | None = None,
    evidence_path: Path | None = None,
    parent_path: Path | None = None,
    *,
    legacy_terminal_compat: bool = False,
) -> dict[str, Any]:
    order, order_bytes = _read_json(order_path, "order")
    order_obj = _object(order, "order")
    if order_obj.get("orderVersion") != "AGENT_ORDER_JSON_V1":
        raise ExecutionStateError("orderVersion must be AGENT_ORDER_JSON_V1")
    scope = _scope_from_order(order_obj)
    result = None
    result_bytes = None
    if result_path is not None:
        result, result_bytes = _read_json(result_path, "result")
        result = _object(result, "result")
        if result.get("resultVersion") != "AGENT_RESULT_JSON_V1":
            raise ExecutionStateError("resultVersion must be AGENT_RESULT_JSON_V1")
        if result.get("orderId") != scope["orderId"]:
            raise ExecutionStateError("result.orderId does not match order scope")
    evidence_value = None
    evidence_bytes = None
    if evidence_path is not None:
        evidence_value, evidence_bytes = _read_json(evidence_path, "evidence")
    compatibility_mode = _legacy_terminal_compatibility(order_obj, result, parent_path, legacy_terminal_compat)
    phase, status, executor, summary = _status_from_inputs(order_obj, result, legacy_terminal_compat=compatibility_mode)
    summary, summary_omitted = _bounded_summary(summary)
    loop = order_obj.get("loopContract")
    iteration = None
    if isinstance(loop, dict) and isinstance(loop.get("iteration"), dict):
        iteration = loop["iteration"].get("current")
        if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 0:
            raise ExecutionStateError("loopContract.iteration.current is invalid")
    parent = None
    parent_bytes = None
    sequence = 0
    parent_hash = None
    if parent_path is not None:
        parent, parent_bytes = _read_json(parent_path, "parent state")
        parent = validate_state(parent, parent_bytes=parent_bytes)
        if parent["scope"] != scope:
            raise ExecutionStateError("parent state scope does not match order scope")
        sequence = parent["revision"]["sequence"] + 1
        parent_hash = _sha256_bytes(parent_bytes)
    sources = [_source("order", order_path, order_bytes)]
    result_hash = None
    if result_path is not None and result_bytes is not None:
        sources.append(_source("result", result_path, result_bytes))
        result_hash = _sha256_bytes(result_bytes)
    evidence = _evidence_refs(evidence_value, scope)
    if evidence_path is not None and evidence_bytes is not None:
        sources.append(_source("evidence-index", evidence_path, evidence_bytes))
    state = {
        "stateVersion": STATE_VERSION,
        "scope": scope,
        "execution": {"phase": phase, "status": status, "executor": executor, "iteration": iteration, "summary": summary},
        "revision": {"sequence": sequence, "orderSha256": _sha256_bytes(order_bytes), "resultSha256": result_hash, "parentSha256": parent_hash},
        "provenance": {
            "mode": "read-only-derived-legacy-terminal" if compatibility_mode else "read-only-derived",
            "sources": sources,
            "evidence": evidence,
        },
    }
    if summary_omitted is not None:
        state["execution"]["summaryOmitted"] = summary_omitted
    state["execution"] = {key: value for key, value in state["execution"].items() if value is not None}
    validate_state(state, parent=parent, parent_bytes=parent_bytes)
    return state


def _reject_output_input_collision(output_path: Path, input_paths: list[Path | None]) -> None:
    output_resolved = output_path.resolve()
    for input_path in input_paths:
        if input_path is None:
            continue
        input_resolved = input_path.resolve()
        if output_resolved == input_resolved:
            raise ExecutionStateError("output path collides with an input path")
        try:
            if output_path.exists() and input_path.exists() and os.path.samefile(output_path, input_path):
                raise ExecutionStateError("output path collides with an input path")
        except OSError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project or validate AQUILA_EXECUTION_STATE_V1 (opt-in, read-only).")
    sub = parser.add_subparsers(dest="command", required=True)
    project_parser = sub.add_parser("project", help="derive bounded state from order and optional references")
    project_parser.add_argument("--order", required=True, type=Path)
    project_parser.add_argument("--result", type=Path)
    project_parser.add_argument("--evidence", type=Path, help="strict JSON evidence-reference array")
    project_parser.add_argument("--parent", type=Path, help="prior state for concurrency/transition checks")
    project_parser.add_argument(
        "--legacy-terminal-compat",
        action="store_true",
        help="project one implicit legacy terminal result as a read-only verify snapshot",
    )
    project_parser.add_argument("--output", required=True, type=Path)
    validate_parser = sub.add_parser("validate", help="validate an existing state artifact")
    validate_parser.add_argument("--state", required=True, type=Path)
    validate_parser.add_argument("--parent", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "project":
            _reject_output_input_collision(args.output, [args.order, args.result, args.evidence, args.parent])
            state = project(
                args.order,
                args.result,
                args.evidence,
                args.parent,
                legacy_terminal_compat=args.legacy_terminal_compat,
            )
            encoded = _canonical_bytes(state) + b"\n"
            if len(encoded) > MAX_STATE_BYTES:
                raise ExecutionStateError(f"state exceeds {MAX_STATE_BYTES} bytes")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(encoded)
            print(json.dumps({"ok": True, "stateVersion": STATE_VERSION, "bytes": len(encoded)}, sort_keys=True))
        else:
            state, state_bytes = _read_json(args.state, "state")
            parent = None
            parent_bytes = None
            if args.parent:
                parent, parent_bytes = _read_json(args.parent, "parent state")
            validate_state(state, parent=parent, parent_bytes=parent_bytes)
            print(json.dumps({"ok": True, "stateVersion": STATE_VERSION}, sort_keys=True))
        return 0
    except (ExecutionStateError, OSError, StrictJSONError) as exc:
        print(f"execution-state rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
