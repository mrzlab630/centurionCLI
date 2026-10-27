#!/usr/bin/env python3
"""Fail-closed verification for controller-owned predecessor handoffs.

``inputResults`` is an order-owned list of already accepted controller results.
Executor claims are never trusted for the handoff: the verifier recomputes all
receipt and selected artifact digests from the predecessor control namespace.
Product-file lineage remains the separate ``artifact_lineage`` contract.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any, Mapping

from agent_artifact_namespace import ArtifactNamespaceError, artifact_namespace, validate_order_id
from strict_json import StrictJSONError, strict_json_load_bytes
from response_envelope import valid_media_type


MAX_INPUT_DEPTH = 64
MAX_CONTROL_BYTES = 16 * 1024 * 1024
ORDER_VERSION = "AGENT_ORDER_JSON_V1"
RESULT_VERSION = "AGENT_RESULT_JSON_V1"
START_VERSION = "RESULT_GATEWAY_START_V1"
CLOSURE_VERSION = "RESULT_GATEWAY_CLOSURE_V2"
PROOF_VERSION = "AQUILA_CONTROLLER_VERIFICATION_V1"
ACCEPTANCE_VERSION = "AQUILA_CONTROLLER_ACCEPTANCE_V1"
PROOF_NAME = "controller-proof.json"
ACCEPTANCE_NAME = "controller-acceptance.json"
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class AcceptedInputError(ValueError):
    """Raised when a predecessor handoff is missing, changed, or untrusted."""


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise AcceptedInputError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _repo_root(repo_path: str | Path) -> Path:
    try:
        repo = Path(repo_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AcceptedInputError(f"cannot resolve repository: {exc}") from exc
    if not repo.is_dir():
        raise AcceptedInputError(f"repository is not a directory: {repo}")
    return repo


def _lexical_path(repo: Path, value: Any, label: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise AcceptedInputError(f"{label} must be a non-empty path")
    if "\x00" in str(value):
        raise AcceptedInputError(f"{label} contains a NUL byte")
    try:
        raw = Path(value).expanduser()
    except (ValueError, RuntimeError) as exc:
        raise AcceptedInputError(f"{label} is invalid: {exc}") from exc
    if ".." in raw.parts:
        raise AcceptedInputError(f"{label} contains an unsafe path component")
    candidate = raw if raw.is_absolute() else repo / raw
    candidate = Path(os.path.normpath(str(candidate)))
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise AcceptedInputError(f"{label} must be inside repository {repo}") from exc
    if candidate == repo:
        raise AcceptedInputError(f"{label} must name a file below repository")
    return candidate


def _relative(repo: Path, path: Path, label: str) -> str:
    try:
        relative = path.relative_to(repo)
    except ValueError as exc:
        raise AcceptedInputError(f"{label} must be inside repository") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise AcceptedInputError(f"{label} is not canonical")
    return relative.as_posix()


def _assert_no_symlink(repo: Path, path: Path, label: str) -> None:
    current = repo
    for part in _relative(repo, path, label).split("/"):
        current /= part
        try:
            item = os.lstat(current)
        except OSError as exc:
            raise AcceptedInputError(f"{label} cannot be inspected: {exc}") from exc
        if stat.S_ISLNK(item.st_mode):
            raise AcceptedInputError(f"{label} must not contain symlinks: {path}")


def _control_path(repo: Path, order_id: str, value: Any, label: str) -> Path:
    try:
        safe_id = validate_order_id(order_id)
    except ArtifactNamespaceError as exc:
        raise AcceptedInputError(str(exc)) from exc
    path = _lexical_path(repo, value, label)
    namespace = artifact_namespace(repo, safe_id)
    try:
        path.relative_to(namespace)
    except ValueError as exc:
        raise AcceptedInputError(f"{label} must be under predecessor control namespace {namespace}") from exc
    _assert_no_symlink(repo, path, label)
    return path


def _open_relative(repo_fd: int, relative: str, label: str) -> int:
    parts = relative.split("/")
    parent_fd = os.dup(repo_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, _DIR_FLAGS, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        leaf_fd = os.open(parts[-1], _READ_FLAGS, dir_fd=parent_fd)
        return leaf_fd
    except OSError as exc:
        raise AcceptedInputError(f"cannot open {label}: {exc}") from exc
    finally:
        try:
            os.close(parent_fd)
        except OSError:
            pass


def _read_bytes(repo: Path, path: Path, label: str) -> tuple[bytes, str]:
    relative = _relative(repo, path, label)
    repo_fd = -1
    fd = -1
    try:
        repo_fd = os.open(repo, _DIR_FLAGS)
        fd = _open_relative(repo_fd, relative, label)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise AcceptedInputError(f"{label} must be a regular file")
        if before.st_size > MAX_CONTROL_BYTES:
            raise AcceptedInputError(f"{label} exceeds control size limit")
        content = bytearray()
        while chunk := os.read(fd, 1024 * 1024):
            content.extend(chunk)
            if len(content) > MAX_CONTROL_BYTES:
                raise AcceptedInputError(f"{label} exceeds control size limit")
        after = os.fstat(fd)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mode, item.st_mtime_ns, item.st_ctime_ns)
        if identity(before) != identity(after) or len(content) != after.st_size:
            raise AcceptedInputError(f"{label} changed while being read")
        raw = bytes(content)
        return raw, hashlib.sha256(raw).hexdigest()
    except OSError as exc:
        raise AcceptedInputError(f"cannot read {label}: {exc}") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if repo_fd >= 0:
            os.close(repo_fd)


def _json(repo: Path, path: Path, label: str) -> tuple[dict[str, Any], str]:
    raw, digest = _read_bytes(repo, path, label)
    try:
        value = strict_json_load_bytes(raw, label)
    except StrictJSONError as exc:
        raise AcceptedInputError(str(exc)) from exc
    if not isinstance(value, dict):
        raise AcceptedInputError(f"{label} must be a JSON object")
    return value, digest


def _path_equal(repo: Path, value: Any, expected: Path, label: str) -> None:
    actual = _lexical_path(repo, value, label)
    if actual != expected:
        raise AcceptedInputError(f"{label} does not match frozen receipt path")
    _assert_no_symlink(repo, actual, label)


def _input_shape(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AcceptedInputError(f"inputResults[{index}] must be an object")
    keys = {"orderId", "resultPath", "resultSha256", "acceptancePath", "acceptanceSha256", "closurePath", "artifacts"}
    if set(item) != keys:
        raise AcceptedInputError(f"inputResults[{index}] has unexpected or missing fields")
    if not isinstance(item["orderId"], str):
        raise AcceptedInputError(f"inputResults[{index}].orderId must be a string")
    _digest(item["resultSha256"], f"inputResults[{index}].resultSha256")
    _digest(item["acceptanceSha256"], f"inputResults[{index}].acceptanceSha256")
    if not isinstance(item["artifacts"], list):
        raise AcceptedInputError(f"inputResults[{index}].artifacts must be an array")
    seen_paths: set[str] = set()
    for artifact_index, artifact in enumerate(item["artifacts"]):
        if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256", "mediaType"}:
            raise AcceptedInputError(f"inputResults[{index}].artifacts[{artifact_index}] has invalid fields")
        if not isinstance(artifact["path"], str) or not artifact["path"].strip():
            raise AcceptedInputError(f"inputResults[{index}].artifacts[{artifact_index}].path must be a string")
        if artifact["path"] in seen_paths:
            raise AcceptedInputError(f"inputResults[{index}] contains duplicate artifact paths")
        seen_paths.add(artifact["path"])
        _digest(artifact["sha256"], f"inputResults[{index}].artifacts[{artifact_index}].sha256")
        if not valid_media_type(artifact["mediaType"]):
            raise AcceptedInputError(f"inputResults[{index}].artifacts[{artifact_index}].mediaType must be a media type")
    return item


def _verify_one(repo: Path, current_order_id: str, item: dict[str, Any], index: int, seen_orders: set[str], depth: int) -> dict[str, Any]:
    if depth >= MAX_INPUT_DEPTH:
        raise AcceptedInputError("accepted input chain exceeds maximum depth")
    try:
        predecessor_id = validate_order_id(item["orderId"])
    except ArtifactNamespaceError as exc:
        raise AcceptedInputError(f"inputResults[{index}].orderId is unsafe: {exc}") from exc
    if predecessor_id == current_order_id:
        raise AcceptedInputError("accepted input cannot reference current order")
    if predecessor_id in seen_orders:
        raise AcceptedInputError(f"accepted input chain contains duplicate or cycle: {predecessor_id}")
    if len(seen_orders) > MAX_INPUT_DEPTH:
        raise AcceptedInputError("accepted input graph exceeds maximum count")

    namespace = artifact_namespace(repo, predecessor_id)
    result_path = _control_path(repo, predecessor_id, item["resultPath"], f"inputResults[{index}].resultPath")
    acceptance_path = _control_path(repo, predecessor_id, item["acceptancePath"], f"inputResults[{index}].acceptancePath")
    if acceptance_path != namespace / ACCEPTANCE_NAME:
        raise AcceptedInputError(f"inputResults[{index}].acceptancePath must be {namespace / ACCEPTANCE_NAME}")
    acceptance, acceptance_digest = _json(repo, acceptance_path, "controller acceptance")
    if acceptance_digest != item["acceptanceSha256"]:
        raise AcceptedInputError(f"inputResults[{index}] controller acceptance digest mismatch")
    if acceptance.get("version") != ACCEPTANCE_VERSION or acceptance.get("status") != "passed" or acceptance.get("reason") is not None:
        raise AcceptedInputError(f"inputResults[{index}] controller acceptance is not passed")
    if acceptance.get("orderId") != predecessor_id:
        raise AcceptedInputError(f"inputResults[{index}] controller acceptance identity mismatch")

    proof_path = namespace / PROOF_NAME
    proof, proof_digest = _json(repo, proof_path, "controller proof")
    if proof.get("version") != PROOF_VERSION or proof.get("status") != "passed" or proof.get("reason") is not None:
        raise AcceptedInputError(f"inputResults[{index}] controller proof is not passed")
    if proof.get("orderId") != predecessor_id or acceptance.get("proofReceiptSha256") != proof_digest:
        raise AcceptedInputError(f"inputResults[{index}] controller proof identity or digest mismatch")
    start_expected = _digest(acceptance.get("startReceiptSha256"), f"inputResults[{index}].acceptance.startReceiptSha256")
    closure_expected = _digest(acceptance.get("closureSha256"), f"inputResults[{index}].acceptance.closureSha256")
    closure_path = _control_path(repo, predecessor_id, item["closurePath"], f"inputResults[{index}].closurePath")
    closure, closure_digest = _json(repo, closure_path, "closure receipt")
    if closure_digest != closure_expected:
        raise AcceptedInputError(f"inputResults[{index}] closure receipt digest mismatch")
    start_path = _control_path(repo, predecessor_id, closure.get("startReceiptPath"), "closure.startReceiptPath")
    start, start_digest = _json(repo, start_path, "start receipt")
    if start_digest != start_expected or closure.get("startReceiptSha256") != start_digest:
        raise AcceptedInputError(f"inputResults[{index}] start receipt digest mismatch")

    order_path = _control_path(repo, predecessor_id, start.get("orderPath"), "start.orderPath")
    _path_equal(repo, closure.get("orderPath"), order_path, "closure.orderPath")
    _path_equal(repo, start.get("resultPath"), result_path, "start.resultPath")
    _path_equal(repo, closure.get("canonicalResultPath"), result_path, "closure.canonicalResultPath")
    _path_equal(repo, start.get("startReceiptPath"), start_path, "start.startReceiptPath")
    _path_equal(repo, start.get("closurePath"), closure_path, "start.closurePath")

    order, order_digest = _json(repo, order_path, "predecessor order")
    if order_digest != start.get("orderSha256") or order_digest != closure.get("orderSha256") or order_digest != acceptance.get("orderSha256") or order_digest != proof.get("orderSha256"):
        raise AcceptedInputError(f"inputResults[{index}] predecessor order digest mismatch")
    if order.get("orderVersion") != ORDER_VERSION or order.get("orderId") != predecessor_id:
        raise AcceptedInputError(f"inputResults[{index}] predecessor order identity mismatch")
    executor = order.get("executor")
    if not isinstance(executor, str) or executor not in {"codex", "claude"}:
        raise AcceptedInputError(f"inputResults[{index}] predecessor executor is not a Gateway executor")
    if "workspace" in order:
        workspace = order["workspace"]
        if not isinstance(workspace, dict) or workspace.get("repoPath") != str(repo):
            raise AcceptedInputError(f"inputResults[{index}] predecessor workspace mismatch")
    if "outputContract" in order:
        output = order["outputContract"]
        if not isinstance(output, dict) or output.get("resultVersion") != RESULT_VERSION:
            raise AcceptedInputError(f"inputResults[{index}] predecessor output contract mismatch")
        _path_equal(repo, output.get("resultPath"), result_path, "predecessor outputContract.resultPath")

    result, result_digest = _json(repo, result_path, "predecessor result")
    if "reporting" in acceptance:
        closure = _verify_reporting(repo, predecessor_id, acceptance, closure, result_digest, order_digest)
    if result_digest != item["resultSha256"]:
        raise AcceptedInputError(f"inputResults[{index}] canonical result digest mismatch")
    if result.get("resultVersion") != RESULT_VERSION or result.get("orderId") != predecessor_id or result.get("status") != "done" or result.get("executor") != executor:
        raise AcceptedInputError(f"inputResults[{index}] canonical result is not an accepted done result")
    if result_digest != closure.get("canonicalResultSha256") or result_digest != acceptance.get("canonicalResultSha256") or result_digest != proof.get("canonicalResultSha256"):
        raise AcceptedInputError(f"inputResults[{index}] receipts do not bind canonical result")
    if (
        closure.get("closureVersion") != CLOSURE_VERSION or closure.get("state") != "closed"
        or closure.get("launcherClosed") is not True or closure.get("canonicalFinalized") is not True
        or closure.get("canonicalStatus") != "done" or closure.get("childStarted") is not True
        or closure.get("timedOut") is not False or type(closure.get("exitCode")) is not int or closure.get("exitCode") != 0
        or closure.get("drainTimedOut", False) is not False
        or closure.get("controllerErrors") != []
    ):
        raise AcceptedInputError(f"inputResults[{index}] closure is not a successful Gateway closure")
    if (
        start.get("startReceiptVersion") != START_VERSION or start.get("state") != "started"
        or start.get("orderId") != predecessor_id or closure.get("orderId") != predecessor_id
        or start.get("executor") != executor or closure.get("executor") != executor
        or not isinstance(start.get("runId"), str) or not start.get("runId")
        or start.get("runId") != closure.get("runId") or acceptance.get("runId") != start.get("runId")
        or proof.get("runId") != start.get("runId")
    ):
        raise AcceptedInputError(f"inputResults[{index}] receipt identities do not match")
    if proof.get("startReceiptSha256") != start_digest or proof.get("closureSha256") != closure_digest:
        raise AcceptedInputError(f"inputResults[{index}] controller proof does not bind Gateway receipts")
    if proof.get("scope") != "post_execution_proof" or not isinstance(proof.get("observedChecks"), dict):
        raise AcceptedInputError(f"inputResults[{index}] controller proof lacks observed post-execution checks")
    # V3 cannot inherit a pinned-but-malformed author response or a review of
    # different attempt bytes. Imports stay local to avoid the runner boundary.
    from order_preflight import controller_context
    try:
        context = controller_context(order)
        if context is not None:
            from agent_result_builder import PACKAGED_SCHEMA, _load_schema, validate_candidate
            _, validator = _load_schema(PACKAGED_SCHEMA)
            candidate_errors = validate_candidate(result, order, validator)
            if candidate_errors:
                raise AcceptedInputError("predecessor response validation failed: " + "; ".join(candidate_errors))
            from response_envelope import parse_response_bytes
            envelope = result.get("responseEnvelope")
            if not isinstance(envelope, dict):
                raise AcceptedInputError("predecessor lacks controller response envelope")
            raw_path = _control_path(repo, predecessor_id, envelope.get("rawEvidencePath"), "response raw evidence")
            normalized_path = _control_path(repo, predecessor_id, envelope.get("normalizedCandidatePath"), "normalized candidate")
            raw, raw_hash = _read_bytes(repo, raw_path, "response raw evidence")
            normalized, normalized_hash = _read_bytes(repo, normalized_path, "normalized candidate")
            parsed = parse_response_bytes(raw, allowed_transports=order["outputContract"].get("acceptedTransports"))
            author = {key: value for key, value in result.items() if key != "responseEnvelope"}
            if (envelope.get("version") != "AGENT_RESPONSE_ENVELOPE_V1" or envelope.get("transport") != parsed.transport
                or envelope.get("rawSha256") != raw_hash or envelope.get("normalizedSha256") != normalized_hash
                or envelope.get("rawBytes") != len(raw) or envelope.get("normalizedBytes") != len(normalized)
                or parsed.normalized_bytes != normalized or parsed.value != author):
                raise AcceptedInputError("predecessor raw/candidate/result envelope binding mismatch")
            review = result.get("executorExtensions", {}).get("review")
            if review is not None and review.get("verdict") != "pass":
                raise AcceptedInputError("predecessor review verdict is not pass")
            if "protocolFailure" in closure or closure.get("canonicalFinalized") is not True:
                raise AcceptedInputError("report recovery is disabled without a proven no-write capability")
            for label in ("stdout", "stderr", "candidate"):
                capture = closure.get(label)
                if not isinstance(capture, dict) or capture.get("complete") is not True:
                    raise AcceptedInputError(f"predecessor {label} capture is incomplete")
                capture_path = _control_path(repo, predecessor_id, capture.get("path"), f"closure.{label}.path")
                content, capture_hash = _read_bytes(repo, capture_path, f"predecessor {label} capture")
                if capture_hash != capture.get("sha256") or len(content) != capture.get("bytes"):
                    raise AcceptedInputError(f"predecessor {label} capture digest/size mismatch")
            if closure["candidate"]["sha256"] != raw_hash or closure["candidate"]["bytes"] != len(raw):
                raise AcceptedInputError("predecessor captured candidate is not the original author envelope")
            extraction = closure["candidate"].get("extraction")
            if extraction is not None and extraction.get("rawSha256") != closure["stdout"].get("sha256"):
                raise AcceptedInputError("predecessor extraction is not bound to raw stdout")
            from review_ladder import validate_order_routing
            import json
            routing = validate_order_routing(order)
            route_hash = hashlib.sha256(json.dumps(routing, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
            if start.get("routing") != routing or closure.get("routing") != routing or start.get("routingSha256") != route_hash or closure.get("routingSha256") != route_hash:
                raise AcceptedInputError("predecessor routing binding mismatch")
    except AcceptedInputError:
        raise
    except (ValueError, OSError, KeyError) as exc:
        raise AcceptedInputError(f"predecessor 3.0 contract validation failed: {exc}") from exc
    if len({result_path, acceptance_path, proof_path, closure_path, start_path, order_path}) != 6:
        raise AcceptedInputError(f"inputResults[{index}] control paths must be distinct")

    expected_artifacts: list[dict[str, Any]] = []
    reported_artifacts = result.get("artifacts")
    if not isinstance(reported_artifacts, list):
        raise AcceptedInputError(f"inputResults[{index}] predecessor result artifacts must be an array")
    artifact_paths: set[Path] = set()
    for artifact_index, expected in enumerate(item["artifacts"]):
        artifact_path = _control_path(repo, predecessor_id, expected["path"], f"inputResults[{index}].artifacts[{artifact_index}].path")
        if artifact_path in artifact_paths:
            raise AcceptedInputError(f"inputResults[{index}] contains duplicate artifact paths")
        artifact_paths.add(artifact_path)
        actual_hash = _read_bytes(repo, artifact_path, f"predecessor artifact {artifact_path}")[1]
        if actual_hash != expected["sha256"]:
            raise AcceptedInputError(f"inputResults[{index}] artifact digest mismatch: {artifact_path}")
        matches = []
        for reported in reported_artifacts:
            if not isinstance(reported, dict) or not isinstance(reported.get("path"), str):
                continue
            try:
                reported_path = _lexical_path(repo, reported["path"], "reported artifact path")
            except AcceptedInputError:
                # Unselected product artifacts do not become control inputs.
                continue
            if reported_path == artifact_path:
                matches.append(reported)
        if len(matches) != 1 or matches[0].get("exists") is not True:
            raise AcceptedInputError(f"inputResults[{index}] artifact is not reported as existing: {artifact_path}")
        if context is not None and (matches[0].get("sha256") != expected["sha256"] or matches[0].get("mediaType") != expected["mediaType"]):
            raise AcceptedInputError(f"inputResults[{index}] selected artifact metadata is not bound to original result")
        expected_artifacts.append({"path": str(artifact_path), "sha256": actual_hash, "mediaType": expected["mediaType"]})

    seen_orders.add(predecessor_id)
    nested = _verify_order_inputs(repo, order, seen_orders, depth + 1)
    return {
        "orderId": predecessor_id,
        "orderSha256": order_digest,
        "resultPath": str(result_path),
        "resultSha256": result_digest,
        "acceptancePath": str(acceptance_path),
        "acceptanceSha256": acceptance_digest,
        "closurePath": str(closure_path),
        "artifacts": expected_artifacts,
        "nested": nested,
    }


def verify_manual_report_review(repo: Path, order_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Verify controller-pinned human reporting evidence, never a V2/V3 waiver."""
    def load_ref(ref: Any, label: str) -> dict[str, Any]:
        if not isinstance(ref, dict):
            raise AcceptedInputError(label + " reference missing")
        path = _control_path(repo, order_id, ref.get("path"), label)
        raw, digest = _read_bytes(repo, path, label)
        if digest != ref.get("sha256") or len(raw) != ref.get("bytes"):
            raise AcceptedInputError(label + " reference changed")
        value = strict_json_load_bytes(raw, label)
        if not isinstance(value, dict):
            raise AcceptedInputError(label + " must be an object")
        return value

    review = load_ref(report.get("manualReviewRef"), "manual product review")
    decision = load_ref(report.get("manualReportAuthorityRef"), "manual reporting authority")
    order = load_ref(report["originalRefs"]["order"], "manual review original order")
    from order_preflight import controller_context
    context = controller_context(order)
    if (not context or decision.get("version") != "CENTURION_MISSION_CONTINUATION_V1"
            or decision.get("missionId") != context["missionId"]
            or decision.get("approvalRef") != context["approvalRef"]
            or not isinstance(decision.get("reason"), str) or not decision["reason"].strip()
            or decision.get("manualReportReviewRef") != report["manualReviewRef"]):
        raise AcceptedInputError("manual report lacks matching recorded owner authority")
    _digest(decision.get("stateSha256"), "manual reporting authority state digest")
    expected = {"version": "CENTURION_MANUAL_PRODUCT_REVIEW_V1", "missionId": context["missionId"],
        "orderId": order_id, "orderSha256": report["originalRefs"]["order"]["sha256"],
        "productSnapshotSha256": report["snapshot"]["sha256"],
        "rawSha256": report["originalRefs"]["candidate"]["sha256"],
        "candidateRef": report["manualCandidateRef"], "criteria": order["acceptanceCriteria"], "verdict": "pass"}
    if (any(review.get(key) != value for key, value in expected.items())
            or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()):
        raise AcceptedInputError("manual review must bind exact product, report, criteria and reviewer")
    load_ref(report["manualCandidateRef"], "manual report candidate")
    if any(report["manualCandidateRef"][key] != report["candidateRef"][key] for key in ("sha256", "bytes")):
        raise AcceptedInputError("manual report candidate differs from the reviewed bytes")
    return review


def _verify_reporting(repo: Path, order_id: str, acceptance: dict[str, Any], original: dict[str, Any],
                      result_digest: str, order_digest: str) -> dict[str, Any]:
    """Verify both immutable chains, then project the collected report closure.

    Original malformed closure/raw is never rewritten to masquerade as success.
    """
    ref = acceptance["reporting"]
    path = _control_path(repo, order_id, ref.get("path"), "report recovery closure")
    report, digest = _json(repo, path, "report recovery closure")
    if digest != ref.get("sha256") or report.get("version") != "CENTURION_REPORT_RECOVERY_V1" or report.get("status") != "passed" or report.get("orderId") != order_id or report.get("canonicalResultSha256") != result_digest:
        raise AcceptedInputError("report recovery closure/result binding failed")
    refs = report.get("originalRefs", {})
    for name, saved in refs.items():
        saved_path = _control_path(repo, order_id, saved.get("path"), "original recovery " + name)
        raw, digest = _read_bytes(repo, saved_path, "original recovery " + name)
        if digest != saved.get("sha256") or len(raw) != saved.get("bytes"):
            raise AcceptedInputError("original report recovery custody changed")
    if (set(refs) != {"order", "start", "closure", "protocol", "candidate"} or refs["order"]["sha256"] != order_digest
            or refs["closure"]["sha256"] != acceptance["closureSha256"] or refs["start"]["sha256"] != acceptance["startReceiptSha256"]):
        raise AcceptedInputError("report recovery lacks original order/launch/raw binding")
    protocol, _ = _json(repo, Path(refs["protocol"]["path"]), "original protocol failure")
    if (protocol.get("candidate", {}).get("sha256") != refs["candidate"]["sha256"] or
            protocol.get("candidate", {}).get("complete") is not True or protocol.get("orderSha256") != order_digest):
        raise AcceptedInputError("report recovery original raw is incomplete or changed")
    if original.get("canonicalFinalized") is not False or original.get("childStarted") is not True or original.get("exitCode") != 0 or original.get("timedOut") or original.get("drainTimedOut"):
        raise AcceptedInputError("report recovery cannot cover an unknown product effect")
    report_start, _ = _json(repo, Path(report["startRef"]["path"]), "report start")
    for key in ("originalRefs", "capabilityRef", "snapshot", "idempotencyKey", "mode", "manualReviewRef", "manualReportAuthorityRef", "manualCandidateRef"):
        if report_start.get(key) != report.get(key):
            raise AcceptedInputError("report start/closure binding mismatch")
    key = report.get("idempotencyKey")
    if not isinstance(key, list) or len(key) != 4 or type(key[-1]) is not int or key[-1] < 1:
        raise AcceptedInputError("report idempotency ordinal must be positive")
    if path.parent.name != f"report-{key[-1]}":
        raise AcceptedInputError("report namespace differs from its idempotency ordinal")
    captures = {}
    for label, name in (("candidate", "candidateRef"), ("stdout", "stdoutRef"), ("stderr", "stderrRef"), ("start", "startRef")):
        saved = report[name]
        saved_path = _control_path(repo, order_id, saved.get("path"), "report " + label)
        raw, digest = _read_bytes(repo, saved_path, "report " + label)
        if digest != saved.get("sha256") or len(raw) != saved.get("bytes"):
            raise AcceptedInputError("report capture binding changed")
        captures[label] = dict(saved, complete=True)
    if report.get("mode") == "manual_review":
        if report.get("capabilityRef") is not None:
            raise AcceptedInputError("manual reporting must not claim a model capability")
        verify_manual_report_review(repo, order_id, report)
    elif report.get("mode", "model") == "model":
        _verify_report_capability(report["capabilityRef"])
    else:
        raise AcceptedInputError("unsupported reporting mode")
    for row in report["snapshot"]["files"]:
        product = _lexical_path(repo, row["path"], "recovery product snapshot")
        if row["sha256"] is None:
            if product.exists():
                raise AcceptedInputError("recovery deleted product reappeared")
        else:
            raw, digest = _read_bytes(repo, product, "recovery product")
            if digest != row["sha256"] or len(raw) != row["bytes"]:
                raise AcceptedInputError("recovery product snapshot changed")
    projected = dict(original, canonicalResultSha256=result_digest, canonicalStatus="done", canonicalFinalized=True,
                     controllerErrors=[], candidate=captures["candidate"], stdout=captures["stdout"], stderr=captures["stderr"])
    projected.pop("protocolFailure", None)
    return projected


def _verify_report_capability(cap_ref: dict[str, Any]) -> None:
    # Capability receipts belong to the controller and may be shared across
    # workspaces. Only this exact ref, already bound by report start/closure,
    # may be external. Keep the descriptor-relative, no-symlink bounded reader;
    # product and other control paths remain confined to their repository.
    if (not isinstance(cap_ref, dict) or set(cap_ref) != {"path", "sha256", "bytes"}
            or not isinstance(cap_ref["path"], str) or not Path(cap_ref["path"]).is_absolute()
            or type(cap_ref["bytes"]) is not int or not 0 < cap_ref["bytes"] <= 1024 * 1024):
        raise AcceptedInputError("report capability reference invalid")
    _digest(cap_ref["sha256"], "report capability digest")
    cap_root = Path("/")
    cap_path = _lexical_path(cap_root, cap_ref["path"], "report capability")
    cap_raw, cap_hash = _read_bytes(cap_root, cap_path, "report capability")
    if cap_hash != cap_ref["sha256"] or len(cap_raw) != cap_ref["bytes"]:
        raise AcceptedInputError("report capability binding invalid")
    try:
        cap = strict_json_load_bytes(cap_raw, "report capability")
    except StrictJSONError as exc:
        raise AcceptedInputError(str(exc)) from exc
    if (not isinstance(cap, dict) or cap.get("version") != "CENTURION_NO_TOOLS_REPORT_V1"
            or cap.get("probe") != {"status": "passed", "toolsDenied": True, "mcpDisabled": True,
                                    "hooksDisabled": True, "isolatedConfig": True, "productUnchanged": True}):
        raise AcceptedInputError("report capability binding invalid")


def _verify_order_inputs(repo: Path, order: Mapping[str, Any], seen_orders: set[str], depth: int) -> list[dict[str, Any]]:
    if depth > MAX_INPUT_DEPTH:
        raise AcceptedInputError("accepted input chain exceeds maximum depth")
    values = order.get("inputResults", [])
    if not isinstance(values, list):
        raise AcceptedInputError("inputResults must be an array when present")
    try:
        current_id = validate_order_id(order.get("orderId"))
    except ArtifactNamespaceError as exc:
        raise AcceptedInputError(f"orderId is unsafe: {exc}") from exc
    verified: list[dict[str, Any]] = []
    local_ids: set[str] = set()
    for index, raw in enumerate(values):
        item = _input_shape(raw, index)
        if item["orderId"] in local_ids:
            raise AcceptedInputError(f"inputResults contains duplicate orderId: {item['orderId']}")
        local_ids.add(item["orderId"])
        verified.append(_verify_one(repo, current_id, item, index, seen_orders, depth))
    return verified


def verify_input_results(order: Mapping[str, Any], repo_path: str | Path) -> list[dict[str, Any]]:
    """Verify predecessor results before launch and again before acceptance.

    Orders without ``inputResults`` return an empty list. The function performs
    no writes; callers must fail closed on ``AcceptedInputError``.
    """
    if not isinstance(order, Mapping):
        raise AcceptedInputError("order must be an object")
    if "inputResults" not in order:
        return []
    return _verify_order_inputs(_repo_root(repo_path), order, {order.get("orderId")} if isinstance(order.get("orderId"), str) else set(), 0)


__all__ = ["AcceptedInputError", "MAX_INPUT_DEPTH", "verify_input_results"]
