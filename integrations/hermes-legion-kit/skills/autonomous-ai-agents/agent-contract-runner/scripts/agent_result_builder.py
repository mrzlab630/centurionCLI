#!/usr/bin/env python3
"""Validate and create-only finalize AGENT_RESULT_JSON_V1 payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from response_envelope import (
    JSON_FENCE,
    RAW_JSON,
    ResponseEnvelopeError,
    ParsedResponse,
    parse_response_bytes,
    response_envelope,
    response_state_errors,
    validate_response_handoff,
    valid_media_type,
)
from strict_json import StrictJSONError, strict_json_load_bytes, strict_json_load_path
from agent_artifact_namespace import ArtifactNamespaceError, artifact_namespace, validate_order_id
from review_ladder import RoutingError, validate_order_routing, validate_terminal_review_result


RESULT_VERSION = "AGENT_RESULT_JSON_V1"
PACKAGED_SCHEMA = Path(__file__).resolve().parent.parent / "references" / "agent-result.schema.json"


class BuilderError(ValueError):
    """Raised when result construction cannot be finalized safely."""


def resolve_schema_path(explicit: Path | None = None) -> Path:
    """Resolve the result schema without binding the skill to an operator HOME."""
    if explicit is not None:
        return explicit
    environment_override = os.environ.get("AQUILA_AGENT_RESULT_SCHEMA", "").strip()
    if environment_override:
        return Path(environment_override).expanduser()
    if PACKAGED_SCHEMA.is_file():
        return PACKAGED_SCHEMA
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        return Path(hermes_home).expanduser() / "contracts" / "agent-result.schema.json"
    return Path.home() / ".hermes" / "contracts" / "agent-result.schema.json"


def _schema_errors(validator: Draft202012Validator, payload: Any) -> list[str]:
    errors: list[str] = []
    for error in sorted(validator.iter_errors(payload), key=lambda item: (list(item.absolute_path), item.message)):
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{path}: {error.message}")
    return errors


def _load_schema(path: Path) -> tuple[dict[str, Any], Draft202012Validator]:
    try:
        schema = strict_json_load_path(path, "result schema")
    except (OSError, StrictJSONError) as exc:
        raise BuilderError(f"could not load result schema: {exc}") from exc
    if not isinstance(schema, dict):
        raise BuilderError("result schema must be a JSON object")
    Draft202012Validator.check_schema(schema)
    return schema, Draft202012Validator(schema)


def validate_candidate(candidate: Any, order: dict[str, Any], validator: Draft202012Validator) -> list[str]:
    errors = _schema_errors(validator, candidate)
    if not isinstance(candidate, dict):
        return errors or ["<root>: candidate must be a JSON object"]
    if candidate.get("resultVersion") != RESULT_VERSION:
        errors.append(f"resultVersion: must be {RESULT_VERSION}")
    if candidate.get("orderId") != order.get("orderId"):
        errors.append("orderId: must match the declared order")
    if candidate.get("executor") != order.get("executor"):
        errors.append("executor: must match the declared order")
    try:
        routing_for_handoff = validate_order_routing(order) if "createdAt" in order else None
    except RoutingError as exc:
        routing_for_handoff = None
        errors.append(f"routing validation failed: {exc}")
    errors.extend(validate_response_handoff(candidate, order, routing_for_handoff))
    errors.extend(response_state_errors(candidate))
    for artifact in candidate.get("artifacts", []) if isinstance(candidate.get("artifacts"), list) else []:
        if not isinstance(artifact, dict):
            continue
        typed = order.get("outputContract", {}).get("handoff") is not None and artifact.get("exists") is True
        if typed or "sha256" in artifact or "mediaType" in artifact:
            digest, media_type = artifact.get("sha256"), artifact.get("mediaType")
            if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                errors.append("artifacts.sha256 must be a lowercase SHA-256 digest")
            if not valid_media_type(media_type):
                errors.append("artifacts.mediaType must be a media type")
    routing = None
    if "createdAt" in order:
        try:
            routing = validate_order_routing(order)
            validate_terminal_review_result(routing, candidate)
        except RoutingError as exc:
            errors.append(f"routing validation failed: {exc}")
    if routing is not None and routing["executionProfile"] == "advisory":
        if candidate.get("filesChanged") != []:
            errors.append("Astra advisory filesChanged must be empty")
        workspace = order.get("workspace")
        repo_value = workspace.get("repoPath") if isinstance(workspace, dict) else None
        if isinstance(repo_value, str):
            namespace = artifact_namespace(Path(repo_value), order["orderId"])
            for index, artifact in enumerate(candidate.get("artifacts", [])):
                if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                    continue
                path = Path(artifact["path"]).expanduser()
                if not path.is_absolute():
                    path = Path(repo_value) / path
                resolved = path.resolve(strict=False)
                if namespace not in resolved.parents:
                    errors.append(f"Astra advisory artifacts[{index}] must stay in the control namespace")
    if candidate.get("status") == "done":
        proof = candidate.get("proof")
        if not isinstance(proof, list) or not proof:
            errors.append("done result requires at least one proof entry")
        elif any(not isinstance(item, dict) or item.get("status") != "pass" for item in proof):
            errors.append("done result requires every proof[].status to be pass")
        self_review = candidate.get("selfReview")
        if not isinstance(self_review, dict) or self_review.get("performed") is not True:
            errors.append("done result requires selfReview.performed=true")
        for field in ("scopeDeviations", "forbiddenPatternHits"):
            if candidate.get(field): errors.append(f"done result must not include {field}")
    if errors and not any("RESPONSE_" in error for error in errors):
        identity_error = any(error.startswith(("orderId:", "executor:")) for error in errors)
        errors.insert(0, "RESPONSE_IDENTITY_ERROR" if identity_error else "RESPONSE_SCHEMA_ERROR")
    return sorted(set(errors))


def preserve_original(candidate_bytes: bytes, evidence_dir: Path) -> Path:
    digest = hashlib.sha256(candidate_bytes).hexdigest()
    evidence_path = evidence_dir / f"{digest}.candidate-result.bin"
    return preserve_bytes(candidate_bytes, evidence_path)


def preserve_bytes(content: bytes, path: Path) -> Path:
    """Create one immutable evidence file and verify an existing same-name file."""
    path = path.expanduser().absolute()
    evidence_path = path
    digest = hashlib.sha256(content).hexdigest()
    for component in (path, *path.parents):
        if component.is_symlink():
            raise BuilderError(f"evidence path contains a symlink: {component}")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if hashlib.sha256(evidence_path.read_bytes()).hexdigest() != digest:
            raise BuilderError(f"evidence hash collision at {evidence_path}")
        return evidence_path
    try:
        offset = 0
        while offset < len(content):
            written = os.write(fd, content[offset:])
            if written < 1:
                raise OSError("evidence write made no progress")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    return evidence_path


def preserve_normalized(parsed: ParsedResponse, evidence_dir: Path) -> Path:
    digest = parsed.normalized_sha256
    return preserve_bytes(parsed.normalized_bytes, evidence_dir / f"{digest}.normalized-candidate.json")


def _allowed_response_transports(order: dict[str, Any]) -> tuple[str, ...]:
    output_contract = order.get("outputContract")
    if not isinstance(output_contract, dict):
        return (RAW_JSON, JSON_FENCE)
    declared = output_contract.get("acceptedTransports")
    if declared is None:
        return (RAW_JSON, JSON_FENCE)
    if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
        raise BuilderError("outputContract.acceptedTransports must be an array of strings")
    return tuple(declared)


def create_only_finalize(result_path: Path, payload: dict[str, Any]) -> None:
    if not result_path.parent.is_dir():
        raise BuilderError(f"result parent does not exist: {result_path.parent}")
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{result_path.name}.", suffix=".tmp", dir=result_path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        offset = 0
        while offset < len(encoded):
            offset += os.write(fd, encoded[offset:])
        os.fsync(fd)
        os.close(fd)
        fd = -1
        try:
            os.link(temporary_path, result_path)
        except FileExistsError as exc:
            raise BuilderError(f"result path collision: {result_path}") from exc
        directory_fd = os.open(result_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        temporary_path.unlink(missing_ok=True)


def failed_result(order: dict[str, Any], evidence_path: Path, errors: list[str]) -> dict[str, Any]:
    payload = {
        "resultVersion": RESULT_VERSION,
        "orderId": order["orderId"],
        "executor": order["executor"],
        "status": "failed",
        "summary": "Candidate result rejected by deterministic validation.",
        "filesChanged": [],
        "artifacts": [
            {
                "path": str(evidence_path),
                "exists": True,
                "type": "malformed-result-evidence",
                "mediaType": "application/octet-stream",
                "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                "note": f"Original candidate bytes preserved as sha256:{evidence_path.name.split('.', 1)[0]}",
            }
        ],
        "proof": [
            {
                "command": "agent_result_builder deterministic candidate validation",
                "cwd": str(evidence_path.parent),
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
        "stdoutSummary": "",
        "stderrSummary": "Candidate result was not accepted.",
    }
    if order.get("outputContract", {}).get("handoff") is not None:
        payload["handoff"] = order["outputContract"]["handoff"]
    return payload


def _canonical_result_path(order: dict[str, Any], declared_path: str, result_path: Path) -> Path:
    workspace = order.get("workspace")
    repo_value = workspace.get("repoPath") if isinstance(workspace, dict) else None
    if not isinstance(repo_value, str) or not repo_value.strip():
        return result_path

    repo_path = Path(repo_value).expanduser().resolve(strict=False)
    declared = Path(declared_path).expanduser()
    if not declared.is_absolute():
        declared = repo_path / declared
        declared = declared.resolve(strict=False)
        if repo_path not in declared.parents:
            raise BuilderError("result path must remain under workspace.repoPath")
    return declared.resolve(strict=False)


def build_result(
    order_path: Path,
    candidate_path: Path,
    result_path: Path,
    evidence_dir: Path,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    try:
        order = strict_json_load_path(order_path, "order")
    except (OSError, StrictJSONError) as exc:
        raise BuilderError(f"could not load order: {exc}") from exc
    if not isinstance(order, dict):
        raise BuilderError("order must be a JSON object")
    for key in ("orderId", "executor"):
        if not isinstance(order.get(key), str) or not order[key].strip():
            raise BuilderError(f"order.{key} must be a non-empty string")
    try:
        validate_order_id(order["orderId"])
    except ArtifactNamespaceError as exc:
        raise BuilderError(str(exc)) from exc
    output_contract = order.get("outputContract")
    declared_result_path = output_contract.get("resultPath") if isinstance(output_contract, dict) else None
    if not isinstance(declared_result_path, str):
        raise BuilderError("result path must exactly match order.outputContract.resultPath")
    if _canonical_result_path(order, declared_result_path, result_path) != result_path.expanduser().resolve(strict=False):
        raise BuilderError("result path must exactly match order.outputContract.resultPath")
    if result_path.exists() or result_path.is_symlink():
        raise BuilderError(f"result path collision: {result_path}")
    if candidate_path.resolve(strict=False) == result_path.resolve(strict=False):
        raise BuilderError("candidate and canonical result must be distinct")

    _, validator = _load_schema(resolve_schema_path(schema_path))
    if any(component.is_symlink() for component in (candidate_path, *candidate_path.parents)):
        raise BuilderError("candidate path must not contain symlinks")
    if candidate_path.exists() and not candidate_path.is_file():
        raise BuilderError("candidate must be a regular file")
    try:
        candidate_bytes = candidate_path.read_bytes()
    except FileNotFoundError:
        candidate_bytes = b""
    except OSError as exc:
        raise BuilderError(f"could not read candidate: {exc}") from exc
    parse_errors: list[str] = []
    parsed_response: ParsedResponse | None = None
    try:
        parsed_response = parse_response_bytes(
            candidate_bytes,
            "candidate result",
            allowed_transports=_allowed_response_transports(order),
        )
        candidate = parsed_response.value
    except (ResponseEnvelopeError, StrictJSONError) as exc:
        candidate = None
        parse_errors.append(f"candidate response parse failed: {exc}")
    if isinstance(candidate, dict) and "responseEnvelope" in candidate:
        parse_errors.append("RESPONSE_FORMAT_ERROR: candidate responseEnvelope is controller-owned and must not be supplied by executor")
    errors = parse_errors + validate_candidate(candidate, order, validator)
    if errors and not any("RESPONSE_" in error for error in errors):
        identity_error = any(error.startswith(("orderId:", "executor:")) for error in errors)
        errors.insert(0, "RESPONSE_IDENTITY_ERROR" if identity_error else "RESPONSE_SCHEMA_ERROR")
    if errors:
        evidence_path = preserve_original(candidate_bytes, evidence_dir)
        payload = failed_result(order, evidence_path, sorted(set(errors)))
        schema_errors = _schema_errors(validator, payload)
        if schema_errors:
            raise BuilderError("internal failed-result schema error: " + "; ".join(schema_errors))
    else:
        assert parsed_response is not None
        raw_evidence_path = preserve_original(candidate_bytes, evidence_dir)
        normalized_path = preserve_normalized(parsed_response, evidence_dir)
        payload = dict(candidate)
        payload["responseEnvelope"] = response_envelope(
            parsed_response,
            raw_evidence_path=str(raw_evidence_path),
            normalized_path=str(normalized_path),
        )
        schema_errors = _schema_errors(validator, payload)
        if schema_errors:
            raise BuilderError("internal normalized-result schema error: " + "; ".join(schema_errors))
    create_only_finalize(result_path, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--schema", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = build_result(args.order, args.candidate, args.result, args.evidence_dir, args.schema)
    except (BuilderError, OSError) as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1
    print(json.dumps({"status": "finalized", "resultStatus": payload["status"], "path": str(args.result)}, sort_keys=True))
    return 0 if payload["status"] == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
