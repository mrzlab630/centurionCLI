#!/usr/bin/env python3
"""Controller-owned, create-only snapshots for linked order artifacts.

The controller supplies explicit product files. A manifest never trusts hashes
reported by an executor, and verification requires a digest held by the caller.
Directories are deliberately rejected: an order must name the exact files it
will hand to the next order.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence

from agent_artifact_namespace import ArtifactNamespaceError, artifact_namespace, validate_order_id
from strict_json import StrictJSONError, strict_json_load_bytes


MANIFEST_VERSION = "ARTIFACT_LINEAGE_V1"
MANIFEST_NAME = "lineage-manifest.json"
ANCHOR_VERSION = "ARTIFACT_LINEAGE_ANCHOR_V1"
ANCHOR_NAME = "lineage-anchor.json"
TERMINAL_ACCEPTANCE_VERSION = "AQUILA_CONTROLLER_ACCEPTANCE_V1"
TERMINAL_ACCEPTANCE_NAME = "controller-acceptance.json"
PROOF_NAME = "controller-proof.json"
_CONTROL_ROOT = ".centurion/agents_results"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_NAME = re.compile(r"^[a-z][A-Za-z0-9_-]*$")
_MAX_MANIFEST_BYTES = 1024 * 1024
_MAX_CONTROL_BYTES = 16 * 1024 * 1024
_MAX_CHAIN_DEPTH = 64
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


class LineageError(ValueError):
    """Raised when a lineage artifact or its live inputs cannot be trusted."""


def _repo_path(repo_path: str | Path) -> Path:
    try:
        repo = Path(repo_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LineageError(f"cannot resolve repository path: {exc}") from exc
    if not repo.is_dir():
        raise LineageError(f"repository is not a directory: {repo}")
    return repo


def _relative(repo: Path, value: str | Path, label: str) -> str:
    if not isinstance(value, (str, Path)) or not str(value):
        raise LineageError(f"{label} must be a non-empty path")
    path = Path(value).expanduser()
    if ".." in path.parts or not path.parts:
        raise LineageError(f"{label} contains an unsafe path component")
    try:
        relative = path.relative_to(repo) if path.is_absolute() else path
    except ValueError as exc:
        raise LineageError(f"{label} must be inside repository {repo}") from exc
    parts = relative.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise LineageError(f"{label} must name a file below the repository")
    return relative.as_posix()


def _stored_relative(repo: Path, value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise LineageError(f"{label} must be a canonical relative path")
    normalized = _relative(repo, value, label)
    if normalized != value:
        raise LineageError(f"{label} must be a canonical relative path")
    return normalized


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise LineageError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _open_parent(repo_fd: int, relative: str) -> tuple[int, str]:
    parts = relative.split("/")
    fd = os.dup(repo_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd, parts[-1]
    except OSError as exc:
        os.close(fd)
        raise LineageError(f"unsafe or missing parent for {relative}: {exc}") from exc


def _file_record(repo_fd: int, relative: str, *, content_limit: int | None = None) -> tuple[dict[str, Any], bytes | None]:
    parent_fd, leaf = _open_parent(repo_fd, relative)
    try:
        try:
            fd = os.open(leaf, _FILE_FLAGS, dir_fd=parent_fd)
        except OSError as exc:
            raise LineageError(f"cannot open regular file {relative}: {exc}") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise LineageError(f"artifact is not a regular file: {relative}")
            if content_limit is not None and before.st_size > content_limit:
                raise LineageError(f"file exceeds size limit: {relative}")
            digest = hashlib.sha256()
            content = bytearray() if content_limit is not None else None
            observed_size = 0
            while chunk := os.read(fd, 1024 * 1024):
                observed_size += len(chunk)
                if content_limit is not None and observed_size > content_limit:
                    raise LineageError(f"file exceeds size limit: {relative}")
                digest.update(chunk)
                if content is not None:
                    content.extend(chunk)
            after = os.fstat(fd)
            identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mode, item.st_mtime_ns, item.st_ctime_ns)
            if identity(before) != identity(after) or observed_size != after.st_size:
                raise LineageError(f"file changed while hashing: {relative}")
            return {
                "path": relative,
                "type": "file",
                "mode": stat.S_IMODE(after.st_mode),
                "size": observed_size,
                "sha256": digest.hexdigest(),
            }, bytes(content) if content is not None else None
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def _deleted_record(repo_fd: int, relative: str) -> dict[str, str]:
    try:
        parent_fd, leaf = _open_parent(repo_fd, relative)
    except LineageError as exc:
        # A missing ancestor is a deletion; a symlink or non-directory is not.
        if isinstance(exc.__cause__, FileNotFoundError):
            return {"path": relative, "type": "deleted"}
        raise
    try:
        try:
            os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return {"path": relative, "type": "deleted"}
        except OSError as exc:
            raise LineageError(f"cannot inspect deleted path {relative}: {exc}") from exc
        raise LineageError(f"declared deletion still exists: {relative}")
    finally:
        os.close(parent_fd)


def _read_record(repo_fd: int, relative: str, *, content_limit: int | None = None) -> tuple[dict[str, Any], bytes | None]:
    return _file_record(repo_fd, relative, content_limit=content_limit)


def _exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise LineageError(f"{label} has missing or unexpected fields")
    return value


def _check_file_record(repo: Path, repo_fd: int, record: Any, label: str) -> None:
    item = _exact_keys(record, {"path", "type", "mode", "size", "sha256"}, label)
    relative = _stored_relative(repo, item["path"], f"{label}.path")
    if item["type"] != "file":
        raise LineageError(f"{label}.type must be file")
    if isinstance(item["mode"], bool) or not isinstance(item["mode"], int) or not 0 <= item["mode"] <= 0o7777:
        raise LineageError(f"{label}.mode is invalid")
    if isinstance(item["size"], bool) or not isinstance(item["size"], int) or item["size"] < 0:
        raise LineageError(f"{label}.size is invalid")
    _digest(item["sha256"], f"{label}.sha256")
    actual, _ = _read_record(repo_fd, relative)
    if actual != item:
        raise LineageError(f"{label} changed since manifest creation: {relative}")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _manifest_relative(repo: Path, order_id: str, manifest_path: str | Path) -> str:
    try:
        expected = artifact_namespace(repo, order_id) / MANIFEST_NAME
    except ArtifactNamespaceError as exc:
        raise LineageError(str(exc)) from exc
    relative = _relative(repo, manifest_path, "manifest_path")
    if repo / relative != expected:
        raise LineageError(f"manifest_path must be {expected}")
    return relative


def _control_json(repo_fd: int, record: dict[str, Any], label: str) -> dict[str, Any]:
    current, content = _read_record(repo_fd, record["path"], content_limit=_MAX_CONTROL_BYTES)
    if current != record:
        raise LineageError(f"{label} changed while checking its content")
    try:
        value = strict_json_load_bytes(content or b"", label)
    except StrictJSONError as exc:
        raise LineageError(str(exc)) from exc
    if not isinstance(value, dict):
        raise LineageError(f"{label} must be a JSON object")
    return value


def _verify_binding_documents(repo_fd: int, bindings: dict[str, Any], order_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    order = _control_json(repo_fd, bindings["order"], "order")
    result = _control_json(repo_fd, bindings["result"], "result")
    if order.get("orderVersion") != "AGENT_ORDER_JSON_V1" or order.get("orderId") != order_id:
        raise LineageError("order version or identity does not match manifest")
    if order.get("executor") not in {"codex", "claude", "agy", "hermes"}:
        raise LineageError("order executor is missing or unsupported")
    if (
        result.get("resultVersion") != "AGENT_RESULT_JSON_V1"
        or result.get("orderId") != order_id
        or result.get("executor") != order["executor"]
        or result.get("status") != "done"
    ):
        raise LineageError("result version, identity or done status does not match order")
    return order, result


def _verify_gateway_receipts(repo: Path, repo_fd: int, bindings: dict[str, Any], order_id: str, executor: str) -> None:
    receipts = bindings["receipts"]
    if not receipts:
        return
    if set(receipts) != {"start", "closure", "acceptance"}:
        raise LineageError("gateway lineage requires start, closure and controller proof receipts")
    if executor not in {"codex", "claude"}:
        raise LineageError("gateway receipts require a codex or claude executor")
    if receipts["acceptance"]["path"] != f"{_CONTROL_ROOT}/{order_id}/{PROOF_NAME}":
        raise LineageError("Gateway proof receipt must use its deterministic control path")
    start = _control_json(repo_fd, receipts["start"], "start receipt")
    closure = _control_json(repo_fd, receipts["closure"], "closure receipt")
    acceptance = _control_json(repo_fd, receipts["acceptance"], "controller acceptance receipt")
    order_path = str(repo / bindings["order"]["path"])
    result_path = str(repo / bindings["result"]["path"])
    start_path = str(repo / receipts["start"]["path"])
    closure_path = str(repo / receipts["closure"]["path"])
    run_id = start.get("runId")
    if (
        start.get("startReceiptVersion") != "RESULT_GATEWAY_START_V1"
        or start.get("state") != "started"
        or closure.get("closureVersion") != "RESULT_GATEWAY_CLOSURE_V2"
        or closure.get("state") != "closed"
        or closure.get("launcherClosed") is not True
        or closure.get("canonicalFinalized") is not True
        or closure.get("canonicalStatus") != "done"
        or closure.get("childStarted") is not True
        or closure.get("timedOut") is not False
        or closure.get("exitCode") != 0
        or closure.get("controllerErrors") != []
        or acceptance.get("version") != "AQUILA_CONTROLLER_VERIFICATION_V1"
        or acceptance.get("scope") != "post_execution_proof"
        or acceptance.get("status") != "passed"
        or acceptance.get("reason") is not None
        or not isinstance(acceptance.get("observedChecks"), dict)
        or not isinstance(run_id, str)
        or not run_id
        or closure.get("runId") != run_id
        or acceptance.get("runId") != run_id
        or start.get("orderId") != order_id
        or closure.get("orderId") != order_id
        or acceptance.get("orderId") != order_id
        or start.get("executor") != executor
        or closure.get("executor") != executor
        or start.get("orderPath") != order_path
        or closure.get("orderPath") != order_path
        or start.get("resultPath") != result_path
        or closure.get("canonicalResultPath") != result_path
        or start.get("startReceiptPath") != start_path
        or closure.get("startReceiptPath") != start_path
        or start.get("closurePath") != closure_path
        or start.get("orderSha256") != bindings["order"]["sha256"]
        or closure.get("orderSha256") != bindings["order"]["sha256"]
        or acceptance.get("orderSha256") != bindings["order"]["sha256"]
        or closure.get("canonicalResultSha256") != bindings["result"]["sha256"]
        or acceptance.get("canonicalResultSha256") != bindings["result"]["sha256"]
        or closure.get("startReceiptSha256") != bindings["receipts"]["start"]["sha256"]
        or acceptance.get("startReceiptSha256") != bindings["receipts"]["start"]["sha256"]
        or acceptance.get("closureSha256") != bindings["receipts"]["closure"]["sha256"]
    ):
        raise LineageError("gateway receipts do not bind an accepted order and result")


def _verify_manifest(
    manifest_path: str | Path,
    repo: Path,
    expected_sha256: str,
    expected_order_id: str | None,
    seen: set[str],
    verify_live_artifacts: bool,
) -> dict[str, Any]:
    if len(seen) >= _MAX_CHAIN_DEPTH:
        raise LineageError("lineage chain exceeds maximum depth")
    with_fd = os.open(repo, _DIR_FLAGS)
    try:
        relative = _relative(repo, manifest_path, "manifest_path")
        if relative in seen:
            raise LineageError("lineage chain contains a cycle")
        seen.add(relative)
        record, content = _read_record(with_fd, relative, content_limit=_MAX_MANIFEST_BYTES)
        if record["sha256"] != _digest(expected_sha256, "expected_sha256"):
            raise LineageError(f"manifest digest mismatch: {relative}")
        try:
            payload = strict_json_load_bytes(content or b"", "lineage manifest")
        except StrictJSONError as exc:
            raise LineageError(str(exc)) from exc
        manifest = _exact_keys(payload, {"manifestVersion", "orderId", "repoPath", "bindings", "previous", "artifacts"}, "manifest")
        if manifest["manifestVersion"] != MANIFEST_VERSION or manifest["repoPath"] != str(repo):
            raise LineageError("manifest version or repository path mismatch")
        try:
            order_id = validate_order_id(manifest["orderId"])
        except ArtifactNamespaceError as exc:
            raise LineageError(str(exc)) from exc
        if expected_order_id is not None and order_id != expected_order_id:
            raise LineageError("manifest orderId mismatch")
        _manifest_relative(repo, order_id, relative)
        bindings = _exact_keys(manifest["bindings"], {"order", "result", "receipts"}, "bindings")
        _check_file_record(repo, with_fd, bindings["order"], "bindings.order")
        _check_file_record(repo, with_fd, bindings["result"], "bindings.result")
        if not bindings["result"]["path"].startswith(f"{_CONTROL_ROOT}/{order_id}/"):
            raise LineageError("result path must be in order control namespace")
        if not isinstance(bindings["receipts"], dict):
            raise LineageError("bindings.receipts must be an object")
        paths = {relative}
        for label in ("order", "result"):
            path = bindings[label]["path"]
            if path in paths:
                raise LineageError("manifest and binding paths must be distinct")
            paths.add(path)
        for name, item in bindings["receipts"].items():
            if not isinstance(name, str) or _RECEIPT_NAME.fullmatch(name) is None:
                raise LineageError("receipt names must be safe labels")
            _check_file_record(repo, with_fd, item, f"bindings.receipts.{name}")
            if not item["path"].startswith(f"{_CONTROL_ROOT}/{order_id}/"):
                raise LineageError("receipt path must be in order control namespace")
            if item["path"] in paths:
                raise LineageError("receipt and binding paths must be distinct")
            paths.add(item["path"])
        order_document, _ = _verify_binding_documents(with_fd, bindings, order_id)
        _verify_gateway_receipts(repo, with_fd, bindings, order_id, order_document["executor"])
        artifacts = manifest["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise LineageError("manifest requires explicit product artifacts")
        artifact_paths: list[str] = []
        for index, item in enumerate(artifacts):
            label = f"artifacts[{index}]"
            if not isinstance(item, dict) or item.get("type") not in {"file", "deleted"}:
                raise LineageError(f"{label}.type must be file or deleted")
            if item["type"] == "file":
                if verify_live_artifacts:
                    _check_file_record(repo, with_fd, item, label)
                else:
                    _exact_keys(item, {"path", "type", "mode", "size", "sha256"}, label)
                    _stored_relative(repo, item["path"], f"{label}.path")
                    _digest(item["sha256"], f"{label}.sha256")
                    if isinstance(item["mode"], bool) or not isinstance(item["mode"], int) or not 0 <= item["mode"] <= 0o7777:
                        raise LineageError(f"{label}.mode is invalid")
                    if isinstance(item["size"], bool) or not isinstance(item["size"], int) or item["size"] < 0:
                        raise LineageError(f"{label}.size is invalid")
            else:
                _exact_keys(item, {"path", "type"}, label)
                deleted_path = _stored_relative(repo, item["path"], f"{label}.path")
                if verify_live_artifacts:
                    _deleted_record(with_fd, deleted_path)
            path = item["path"]
            if path == _CONTROL_ROOT or path.startswith(_CONTROL_ROOT + "/"):
                raise LineageError(f"product artifact is in controller namespace: {path}")
            if path in paths:
                raise LineageError(f"product artifact collides with control input: {path}")
            artifact_paths.append(path)
        if artifact_paths != sorted(set(artifact_paths)):
            raise LineageError("product artifact paths must be unique and sorted")
        previous = manifest["previous"]
        if previous is not None:
            prev = _exact_keys(previous, {"path", "orderId", "sha256"}, "previous")
            prev_path = _stored_relative(repo, prev["path"], "previous.path")
            if prev_path in paths or prev_path in artifact_paths:
                raise LineageError("previous manifest path collides with current inputs")
            try:
                previous_order_id = validate_order_id(prev["orderId"])
            except ArtifactNamespaceError as exc:
                raise LineageError(str(exc)) from exc
            if previous_order_id == order_id:
                raise LineageError("previous manifest must belong to another order")
            _manifest_relative(repo, previous_order_id, prev_path)
            _verify_manifest(repo / prev_path, repo, _digest(prev["sha256"], "previous.sha256"), previous_order_id, seen, False)
        return manifest
    finally:
        os.close(with_fd)


def verify_manifest(
    manifest_path: str | Path,
    repo_path: str | Path,
    *,
    expected_sha256: str,
    expected_order_id: str | None = None,
    verify_live_artifacts: bool = True,
) -> dict[str, Any]:
    """Verify head live products and every frozen predecessor control snapshot.

    Invoke before a successor dispatch and again before final closure. The
    expected digest must come from controller custody, not the manifest itself.
    """
    return _verify_manifest(manifest_path, _repo_path(repo_path), expected_sha256, expected_order_id, set(), verify_live_artifacts)


def _create_only(repo_fd: int, relative: str, content: bytes) -> None:
    parent_fd, leaf = _open_parent(repo_fd, relative)
    temporary = f".{leaf}.{secrets.token_hex(12)}.tmp"
    try:
        try:
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent_fd)
        except OSError as exc:
            raise LineageError(f"cannot stage manifest {relative}: {exc}") from exc
        try:
            remaining = memoryview(content)
            while remaining:
                count = os.write(fd, remaining)
                if count <= 0:
                    raise LineageError("manifest write made no progress")
                remaining = remaining[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(temporary, leaf, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
        except FileExistsError as exc:
            raise LineageError(f"manifest already exists: {relative}") from exc
        os.fsync(parent_fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def create_manifest(
    *,
    repo_path: str | Path,
    order_id: str,
    order_path: str | Path,
    result_path: str | Path,
    receipt_paths: Mapping[str, str | Path],
    artifact_paths: Sequence[str | Path],
    manifest_path: str | Path,
    deleted_paths: Sequence[str | Path] = (),
    previous_manifest_path: str | Path | None = None,
    expected_previous_manifest_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Create one immutable manifest from controller-read file bytes.

    The caller must first accept the executor result and independent proof.
    Only exact regular product files and explicit deletion markers are allowed.
    """
    repo = _repo_path(repo_path)
    try:
        validate_order_id(order_id)
    except ArtifactNamespaceError as exc:
        raise LineageError(str(exc)) from exc
    relative = _manifest_relative(repo, order_id, manifest_path)
    if (
        not isinstance(receipt_paths, Mapping)
        or not isinstance(artifact_paths, Sequence)
        or isinstance(artifact_paths, (str, bytes))
        or not isinstance(deleted_paths, Sequence)
        or isinstance(deleted_paths, (str, bytes))
    ):
        raise LineageError("receipt_paths, artifact_paths and deleted_paths have invalid types")
    if (previous_manifest_path is None) != (expected_previous_manifest_sha256 is None):
        raise LineageError("previous manifest requires both path and trusted digest")
    previous = None
    if previous_manifest_path is not None:
        previous_payload = verify_manifest(
            previous_manifest_path, repo,
            expected_sha256=_digest(expected_previous_manifest_sha256, "expected_previous_manifest_sha256"),
            verify_live_artifacts=False,
        )
        if previous_payload["orderId"] == order_id:
            raise LineageError("previous manifest must belong to another order")
        previous = {
            "path": _relative(repo, previous_manifest_path, "previous_manifest_path"),
            "orderId": previous_payload["orderId"],
            "sha256": expected_previous_manifest_sha256,
        }
    repo_fd = os.open(repo, _DIR_FLAGS)
    try:
        order_relative = _relative(repo, order_path, "order_path")
        result_relative = _relative(repo, result_path, "result_path")
        paths = {relative, order_relative, result_relative}
        if len(paths) != 3:
            raise LineageError("manifest, order and result paths must be distinct")
        if not result_relative.startswith(f"{_CONTROL_ROOT}/{order_id}/"):
            raise LineageError("result path must be in order control namespace")
        order_record, _ = _read_record(repo_fd, order_relative)
        result_record, _ = _read_record(repo_fd, result_relative)
        receipts: dict[str, dict[str, Any]] = {}
        for name, path in receipt_paths.items():
            if not isinstance(name, str) or _RECEIPT_NAME.fullmatch(name) is None:
                raise LineageError("receipt names must be safe labels")
            receipt_relative = _relative(repo, path, f"receipt_paths.{name}")
            if not receipt_relative.startswith(f"{_CONTROL_ROOT}/{order_id}/"):
                raise LineageError("receipt path must be in order control namespace")
            if receipt_relative in paths:
                raise LineageError("receipt path collides with manifest, order or result")
            paths.add(receipt_relative)
            receipts[name], _ = _read_record(repo_fd, receipt_relative)
        artifact_records = []
        for label, values, deleted in (("artifact_paths", artifact_paths, False), ("deleted_paths", deleted_paths, True)):
            for index, path in enumerate(values):
                product_relative = _relative(repo, path, f"{label}[{index}]")
                if product_relative == _CONTROL_ROOT or product_relative.startswith(_CONTROL_ROOT + "/"):
                    raise LineageError("product artifact must be outside controller namespace")
                if product_relative in paths:
                    raise LineageError(f"duplicate or colliding artifact path: {product_relative}")
                paths.add(product_relative)
                record = _deleted_record(repo_fd, product_relative) if deleted else _read_record(repo_fd, product_relative)[0]
                artifact_records.append(record)
        if not artifact_records:
            raise LineageError("manifest requires explicit product artifacts")
        payload = {
            "manifestVersion": MANIFEST_VERSION,
            "orderId": order_id,
            "repoPath": str(repo),
            "bindings": {"order": order_record, "result": result_record, "receipts": receipts},
            "previous": previous,
            "artifacts": sorted(artifact_records, key=lambda item: item["path"]),
        }
        order_document, _ = _verify_binding_documents(repo_fd, payload["bindings"], order_id)
        _verify_gateway_receipts(repo, repo_fd, payload["bindings"], order_id, order_document["executor"])
        content = _canonical_bytes(payload)
        if len(content) > _MAX_MANIFEST_BYTES:
            raise LineageError("manifest exceeds size limit")
        _create_only(repo_fd, relative, content)
        digest = hashlib.sha256(content).hexdigest()
    finally:
        os.close(repo_fd)
    verify_manifest(repo / relative, repo, expected_sha256=digest, expected_order_id=order_id)
    return payload, digest


def _anchor_relative(repo: Path, order_id: str, anchor_path: str | Path) -> str:
    try:
        expected = artifact_namespace(repo, order_id) / ANCHOR_NAME
    except ArtifactNamespaceError as exc:
        raise LineageError(str(exc)) from exc
    relative = _relative(repo, anchor_path, "anchor_path")
    if repo / relative != expected:
        raise LineageError(f"anchor_path must be {expected}")
    return relative


def _verify_anchor(
    anchor_path: str | Path,
    repo: Path,
    expected_sha256: str,
    verify_live_artifacts: bool,
    seen: set[str],
    require_terminal: bool,
) -> dict[str, Any]:
    if len(seen) >= _MAX_CHAIN_DEPTH:
        raise LineageError("anchor chain exceeds maximum depth")
    repo_fd = os.open(repo, _DIR_FLAGS)
    try:
        relative = _relative(repo, anchor_path, "anchor_path")
        if relative in seen:
            raise LineageError("anchor chain contains a cycle")
        seen.add(relative)
        record, content = _read_record(repo_fd, relative, content_limit=_MAX_MANIFEST_BYTES)
        if record["sha256"] != _digest(expected_sha256, "expected anchor digest"):
            raise LineageError(f"anchor digest mismatch: {relative}")
        try:
            parsed = strict_json_load_bytes(content or b"", "lineage anchor")
        except StrictJSONError as exc:
            raise LineageError(str(exc)) from exc
        anchor = _exact_keys(
            parsed,
            {"anchorVersion", "orderId", "manifestPath", "manifestSha256", "proofReceiptSha256", "previousAnchorSha256"},
            "lineage anchor",
        )
        if anchor["anchorVersion"] != ANCHOR_VERSION:
            raise LineageError("anchor version mismatch")
        try:
            order_id = validate_order_id(anchor["orderId"])
        except ArtifactNamespaceError as exc:
            raise LineageError(str(exc)) from exc
        _anchor_relative(repo, order_id, relative)
        manifest_relative = _stored_relative(repo, anchor["manifestPath"], "anchor.manifestPath")
        _manifest_relative(repo, order_id, manifest_relative)
        manifest = verify_manifest(
            repo / manifest_relative, repo,
            expected_sha256=_digest(anchor["manifestSha256"], "anchor.manifestSha256"),
            expected_order_id=order_id,
            verify_live_artifacts=verify_live_artifacts,
        )
        bindings = manifest["bindings"]
        proof_record = bindings["receipts"].get("acceptance")
        if proof_record is None or anchor["proofReceiptSha256"] != proof_record["sha256"]:
            raise LineageError("anchor does not bind controller proof receipt")
        if require_terminal:
            terminal_relative = f"{_CONTROL_ROOT}/{order_id}/{TERMINAL_ACCEPTANCE_NAME}"
            terminal_record, _ = _read_record(repo_fd, terminal_relative, content_limit=_MAX_CONTROL_BYTES)
            terminal = _exact_keys(
                _control_json(repo_fd, terminal_record, "terminal controller acceptance"),
                {
                    "version", "orderId", "runId", "orderSha256", "startReceiptSha256",
                    "closureSha256", "canonicalResultSha256", "proofReceiptSha256",
                    "lineageAnchorSha256", "status", "reason", "completedAt",
                },
                "terminal controller acceptance",
            )
            proof = _control_json(repo_fd, proof_record, "controller proof receipt")
            start_record = bindings["receipts"]["start"]
            closure_record = bindings["receipts"]["closure"]
            if (
                terminal.get("version") != TERMINAL_ACCEPTANCE_VERSION
                or terminal.get("status") != "passed"
                or terminal.get("reason") is not None
                or terminal.get("orderId") != order_id
                or terminal.get("runId") != proof.get("runId")
                or terminal.get("orderSha256") != bindings["order"]["sha256"]
                or terminal.get("startReceiptSha256") != start_record["sha256"]
                or terminal.get("closureSha256") != closure_record["sha256"]
                or terminal.get("canonicalResultSha256") != bindings["result"]["sha256"]
                or terminal.get("proofReceiptSha256") != proof_record["sha256"]
                or terminal.get("lineageAnchorSha256") != expected_sha256
                or not isinstance(terminal.get("completedAt"), str)
                or not terminal["completedAt"]
            ):
                raise LineageError("terminal controller acceptance does not bind passed lineage custody")
        previous = manifest["previous"]
        if previous is None:
            if anchor["previousAnchorSha256"] is not None:
                raise LineageError("first anchor cannot name a predecessor")
        else:
            previous_digest = _digest(anchor["previousAnchorSha256"], "anchor.previousAnchorSha256")
            previous_path = artifact_namespace(repo, previous["orderId"]) / ANCHOR_NAME
            predecessor = _verify_anchor(previous_path, repo, previous_digest, False, seen, True)
            if predecessor["manifestSha256"] != previous["sha256"]:
                raise LineageError("predecessor anchor does not bind previous manifest")
        return anchor
    finally:
        os.close(repo_fd)


def verify_anchor(
    anchor_path: str | Path,
    repo_path: str | Path,
    *,
    expected_sha256: str,
    verify_live_artifacts: bool = True,
) -> dict[str, Any]:
    """Check a controller-held anchor digest and its frozen chain.

    The head's live products are checked by default. After an accepted
    successor changes a path, pass False to inspect frozen predecessor custody.
    """
    return _verify_anchor(anchor_path, _repo_path(repo_path), expected_sha256, verify_live_artifacts, set(), True)


def _lineage_config(order: dict[str, Any], repo: Path) -> dict[str, Any] | None:
    if not isinstance(order, dict):
        raise LineageError("order must be a JSON object")
    if "lineage" not in order:
        return None
    try:
        order_id = validate_order_id(order["orderId"])
    except (KeyError, ArtifactNamespaceError) as exc:
        raise LineageError("lineage orderId is invalid") from exc
    lineage = _exact_keys(
        order["lineage"],
        {"artifactPaths", "deletedPaths", "previousAnchorPath", "previousAnchorSha256"},
        "order.lineage",
    )
    normalized: dict[str, Any] = {"orderId": order_id}
    all_paths: list[str] = []
    for key in ("artifactPaths", "deletedPaths"):
        values = lineage[key]
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise LineageError(f"order.lineage.{key} must be a path list")
        normalized[key] = [_relative(repo, value, f"order.lineage.{key}") for value in values]
        all_paths.extend(normalized[key])
    if not all_paths or len(all_paths) != len(set(all_paths)):
        raise LineageError("lineage product paths must be non-empty and unique")
    for item in all_paths:
        if item == _CONTROL_ROOT or item.startswith(_CONTROL_ROOT + "/"):
            raise LineageError("lineage product paths must be outside controller namespace")
    previous_path = lineage["previousAnchorPath"]
    previous_digest = lineage["previousAnchorSha256"]
    if (previous_path is None) != (previous_digest is None):
        raise LineageError("previous anchor path and digest must both be present or null")
    normalized["previousAnchorPath"] = _relative(repo, previous_path, "previousAnchorPath") if previous_path is not None else None
    normalized["previousAnchorSha256"] = _digest(previous_digest, "previousAnchorSha256") if previous_digest is not None else None
    if previous_path is not None and normalized["previousAnchorPath"] == _anchor_relative(repo, order_id, artifact_namespace(repo, order_id) / ANCHOR_NAME):
        raise LineageError("order cannot use its own anchor as predecessor")
    return normalized


def preflight_lineage(order: dict[str, Any], repo_path: str | Path) -> dict[str, Any] | None:
    """Verify the predecessor's live files before launching the successor."""
    repo = _repo_path(repo_path)
    config = _lineage_config(order, repo)
    if config is None:
        return None
    previous_path = config["previousAnchorPath"]
    if previous_path is not None:
        predecessor = verify_anchor(
            repo / previous_path, repo,
            expected_sha256=config["previousAnchorSha256"],
            verify_live_artifacts=True,
        )
        if predecessor["orderId"] == config["orderId"]:
            raise LineageError("order cannot use its own anchor as predecessor")
    return config


def finalize_lineage(
    order: dict[str, Any],
    repo_path: str | Path,
    order_path: str | Path,
    result_path: str | Path,
    receipt_paths: Mapping[str, str | Path],
) -> dict[str, str] | None:
    """Create a manifest and anchor after proof, before terminal acceptance.

    This checks frozen predecessor custody. The caller must have called
    ``preflight_lineage`` before dispatch while predecessor products were live.
    """
    repo = _repo_path(repo_path)
    config = _lineage_config(order, repo)
    if config is None:
        return None
    if not isinstance(receipt_paths, Mapping) or set(receipt_paths) != {"start", "closure", "acceptance"}:
        raise LineageError("lineage finalization requires Gateway start, closure and acceptance receipts")
    order_id = config["orderId"]
    namespace = artifact_namespace(repo, order_id)
    anchor_path = namespace / ANCHOR_NAME
    manifest_path = namespace / MANIFEST_NAME
    if os.path.lexists(anchor_path) or os.path.lexists(manifest_path):
        raise LineageError("lineage manifest or anchor already exists")
    repo_fd = os.open(repo, _DIR_FLAGS)
    try:
        order_relative = _relative(repo, order_path, "order_path")
        order_record, _ = _read_record(repo_fd, order_relative, content_limit=_MAX_CONTROL_BYTES)
        if _control_json(repo_fd, order_record, "order") != order:
            raise LineageError("finalized order differs from order file accepted by Gateway")
    finally:
        os.close(repo_fd)
    previous_anchor_path = config["previousAnchorPath"]
    previous_manifest_path = None
    previous_manifest_digest = None
    if previous_anchor_path is not None:
        previous = verify_anchor(
            repo / previous_anchor_path, repo,
            expected_sha256=config["previousAnchorSha256"],
            verify_live_artifacts=False,
        )
        previous_manifest_path = repo / previous["manifestPath"]
        previous_manifest_digest = previous["manifestSha256"]
    manifest, manifest_digest = create_manifest(
        repo_path=repo,
        order_id=order_id,
        order_path=order_path,
        result_path=result_path,
        receipt_paths=receipt_paths,
        artifact_paths=config["artifactPaths"],
        deleted_paths=config["deletedPaths"],
        manifest_path=manifest_path,
        previous_manifest_path=previous_manifest_path,
        expected_previous_manifest_sha256=previous_manifest_digest,
    )
    proof = manifest["bindings"]["receipts"]["acceptance"]
    anchor = {
        "anchorVersion": ANCHOR_VERSION,
        "orderId": order_id,
        "manifestPath": _relative(repo, manifest_path, "manifest_path"),
        "manifestSha256": manifest_digest,
        "proofReceiptSha256": proof["sha256"],
        "previousAnchorSha256": config["previousAnchorSha256"],
    }
    content = _canonical_bytes(anchor)
    repo_fd = os.open(repo, _DIR_FLAGS)
    try:
        _create_only(repo_fd, _anchor_relative(repo, order_id, anchor_path), content)
    finally:
        os.close(repo_fd)
    anchor_digest = hashlib.sha256(content).hexdigest()
    _verify_anchor(anchor_path, repo, anchor_digest, True, set(), False)
    return {
        "anchorPath": str(anchor_path),
        "anchorSha256": anchor_digest,
        "manifestPath": str(manifest_path),
        "manifestSha256": manifest_digest,
    }
