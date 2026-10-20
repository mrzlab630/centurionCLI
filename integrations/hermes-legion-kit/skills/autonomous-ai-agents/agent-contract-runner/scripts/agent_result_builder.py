#!/usr/bin/env python3
"""Validate and create-only finalize AGENT_RESULT_JSON_V1 payloads."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from schema_validation import Draft202012Validator

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
    MAX_CANDIDATE_BYTES,
    MAX_ORDER_BYTES,
    read_bounded_file,
)
from order_preflight import PreflightError, controller_context, review_binding
from strict_json import StrictJSONError, strict_json_load_bytes, strict_json_load_path
from agent_artifact_namespace import ArtifactNamespaceError, artifact_namespace, validate_order_id
from review_ladder import RoutingError, validate_order_routing, validate_terminal_review_result


RESULT_VERSION = "AGENT_RESULT_JSON_V1"
PACKAGED_SCHEMA = Path(__file__).resolve().parent.parent / "references" / "agent-result.schema.json"


class BuilderError(ValueError):
    """Raised when result construction cannot be finalized safely."""


class ProtocolFailure(BuilderError):
    """The raw response is retained, but no executor result was created."""

    def __init__(self, receipt: Path):
        self.receipt = receipt
        super().__init__(f"protocol failure; no canonical result; receipt: {receipt}")


def native_result_schema(order: dict[str, Any], routing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project required author fields into the API's strict schema subset.

    Conditional success semantics remain enforced by the canonical validator;
    the native generation schema is not the result acceptance authority.
    """
    schema, _ = _load_schema(PACKAGED_SCHEMA)
    projection = copy.deepcopy(schema)
    projection["properties"] = {key: projection["properties"][key] for key in projection["required"]}
    for key in ("orderId", "executor"):
        projection["properties"][key] = {"const": order[key]}
    handoff = order.get("outputContract", {}).get("handoff")
    if handoff is not None:
        projection["properties"]["handoff"] = {
            "type": "object", "properties": {key: {"const": value} for key, value in handoff.items()},
            "required": list(handoff),
        }
        projection["required"].append("handoff")
        artifact = copy.deepcopy(projection["properties"]["artifacts"]["items"])
        present, absent = copy.deepcopy(artifact), copy.deepcopy(artifact)
        present["required"] += ["sha256", "mediaType"]
        present["properties"]["exists"] = {"const": True}
        absent["properties"]["exists"] = {"const": False}
        projection["properties"]["artifacts"]["items"] = {"anyOf": [present, absent]}
    if routing is None and "createdAt" in order:
        routing = validate_order_routing(order)
    if controller_context(order) is not None and isinstance(routing, dict) and routing.get("executionProfile") == "terminal_review":
        projection["required"].append("executorExtensions")
        extension = copy.deepcopy(schema["properties"]["executorExtensions"])
        projection["properties"]["executorExtensions"] = extension
        extension["required"] = ["review"]
        binding = review_binding(order, routing)
        review = extension["properties"]["review"]
        for key, value in binding.items():
            review["properties"][key] = {"const": value}
        review["properties"]["findings"]["description"] = (
            "Only unresolved criterion violations belong in findings; put positive evidence in proof or summary."
        )
        variants = []
        for verdict in ("pass", "fail", "blocked"):
            variant = copy.deepcopy(review)
            variant["properties"]["verdict"] = {"const": verdict}
            if verdict == "pass":
                variant["properties"]["findings"]["maxItems"] = 0
            elif verdict == "fail":
                variant["properties"]["findings"]["minItems"] = 1
            variants.append(variant)
        extension["properties"]["review"] = {"anyOf": variants}
    return _native_schema_subset(projection)


def _native_schema_subset(node: dict[str, Any]) -> dict[str, Any]:
    """Close required-only objects; omit unsupported canonical composition."""
    supported = {"type", "enum", "pattern", "format", "minimum", "maximum", "exclusiveMinimum",
                 "exclusiveMaximum", "multipleOf", "minItems", "maxItems", "description", "title"}
    result = {key: copy.deepcopy(value) for key, value in node.items() if key in supported}
    values = [node["const"]] if "const" in node else node.get("enum")
    if values is not None:
        result["enum"] = values
        if "type" not in result:
            types = {type(value) for value in values}
            if types == {str}:
                result["type"] = "string"
            elif types == {bool}:
                result["type"] = "boolean"
            else:
                raise BuilderError("native schema literal requires an explicit supported scalar type")
    if "anyOf" in node:
        result["anyOf"] = [_native_schema_subset(branch) for branch in node["anyOf"]]
    if node.get("type") == "object":
        required = node.get("required", [])
        result["properties"] = {key: _native_schema_subset(node["properties"][key]) for key in required}
        result["required"] = list(required)
        result["additionalProperties"] = False
    if node.get("type") == "array":
        result["items"] = _native_schema_subset(node["items"])
    return result


def validate_review_binding(candidate: dict[str, Any], order: dict[str, Any], routing: dict[str, Any] | None) -> list[str]:
    try:
        binding = review_binding(order, routing)
    except (PreflightError, ArtifactNamespaceError) as exc:
        return [f"RESPONSE_IDENTITY_ERROR: {exc}"]
    if binding is None:
        return []
    extension = candidate.get("executorExtensions")
    review = extension.get("review") if isinstance(extension, dict) else None
    if not isinstance(review, dict):
        return ["RESPONSE_SCHEMA_ERROR: 3.0 reviewer requires executorExtensions.review"]
    errors = []
    for key, expected in binding.items():
        if review.get(key) != expected:
            errors.append(f"RESPONSE_IDENTITY_ERROR: review.{key} must match original order/attempt binding")
    if review.get("verdict") == "pass" and review.get("findings"):
        errors.append("RESPONSE_SCHEMA_ERROR: pass review cannot contain unresolved findings")
    if review.get("verdict") == "fail" and not review.get("findings"):
        errors.append("RESPONSE_SCHEMA_ERROR: fail review requires criterion/evidence findings")
    return errors


def record_protocol_failure(order: dict[str, Any], order_bytes: bytes, evidence_dir: Path,
                            candidate_bytes: bytes, errors: list[str], *, complete: bool = True,
                            binding: dict[str, Any] | None = None) -> Path:
    raw = preserve_original(candidate_bytes, evidence_dir)
    receipt = {
        "version": "AGENT_PROTOCOL_FAILURE_V1", "orderId": order["orderId"], "executor": order["executor"],
        "orderSha256": hashlib.sha256(order_bytes).hexdigest(), "canonicalFinalized": False,
        "candidate": {"path": str(raw), "sha256": hashlib.sha256(candidate_bytes).hexdigest(),
                      "bytes": len(candidate_bytes), "complete": complete},
        "errors": sorted(set(errors)), "launchBinding": binding,
        "reportRecovery": {"enabled": False, "reason": "no proven no-write report capability", "productReplayAllowed": False},
    }
    path = evidence_dir / "protocol-failure.json"
    create_only_finalize(path, receipt)
    return path


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
    errors.extend(validate_review_binding(candidate, order, routing))
    proof_items = candidate.get("proof")
    if isinstance(proof_items, list):
        for index, item in enumerate(proof_items):
            if not isinstance(item, dict):
                continue
            exit_code = item.get("exitCode")
            if item.get("status") == "pass" and (type(exit_code) is not int or exit_code != 0):
                errors.append(f"proof[{index}].status=pass requires exitCode=0")
    if candidate.get("status") == "done":
        proof = candidate.get("proof")
        if not isinstance(proof, list) or not proof:
            errors.append("done result requires at least one proof entry")
        elif any(not isinstance(item, dict) or item.get("status") != "pass" or type(item.get("exitCode")) is not int or item.get("exitCode") != 0 for item in proof):
            errors.append("done result requires every proof[].status=pass with exitCode=0")
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
    if controller_context(order) is not None:
        from response_envelope import validate_handoff_order
        if order.get("orderVersion") != "AGENT_ORDER_JSON_V1" or not isinstance(output_contract, dict) or "handoff" not in output_contract or validate_handoff_order(order):
            raise BuilderError("3.0 requires strict V1 order and exact handoff before adaptation")
        if output_contract.get("resultVersion") != RESULT_VERSION or output_contract.get("proseAllowedAfterJson") is True:
            raise BuilderError("3.0 requires AGENT_RESULT_JSON_V1 without prose transport")
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
            written = os.write(fd, encoded[offset:])
            if written < 1:
                raise OSError("create-only write made no progress")
            offset += written
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
    *, protocol_binding: dict[str, Any] | None = None, expected_order_sha256: str | None = None,
    expected_candidate_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        order_bytes, order_complete = read_bounded_file(order_path, MAX_ORDER_BYTES)
        if not order_complete:
            raise BuilderError("order exceeds byte limit or changed while reading")
        order = strict_json_load_bytes(order_bytes, "order")
    except (OSError, StrictJSONError, ResponseEnvelopeError) as exc:
        raise BuilderError(f"could not load order: {exc}") from exc
    if not isinstance(order, dict):
        raise BuilderError("order must be a JSON object")
    if expected_order_sha256 is not None and hashlib.sha256(order_bytes).hexdigest() != expected_order_sha256:
        raise BuilderError("order changed after Gateway launch; no canonical result")
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
    if controller_context(order) is not None and resolve_schema_path(schema_path).resolve() != PACKAGED_SCHEMA.resolve():
        raise BuilderError("3.0 requires packaged canonical schema")
    if any(component.is_symlink() for component in (candidate_path, *candidate_path.parents)):
        raise BuilderError("candidate path must not contain symlinks")
    if candidate_path.exists() and not candidate_path.is_file():
        raise BuilderError("candidate must be a regular file")
    try:
        candidate_bytes, candidate_complete = read_bounded_file(candidate_path, MAX_CANDIDATE_BYTES)
    except FileNotFoundError:
        candidate_bytes, candidate_complete = b"", False
    except (OSError, ResponseEnvelopeError) as exc:
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
    if expected_candidate_sha256 is not None and hashlib.sha256(candidate_bytes).hexdigest() != expected_candidate_sha256:
        errors.append("RESPONSE_IDENTITY_ERROR: candidate changed after Gateway capture")
    if not candidate_complete:
        errors.append("RESPONSE_LIMIT_ERROR: candidate is missing, partial, or changed while being read")
    if errors and not any("RESPONSE_" in error for error in errors):
        identity_error = any(error.startswith(("orderId:", "executor:")) for error in errors)
        errors.insert(0, "RESPONSE_IDENTITY_ERROR" if identity_error else "RESPONSE_SCHEMA_ERROR")
    if errors:
        if controller_context(order) is not None:
            receipt = record_protocol_failure(order, order_bytes, evidence_dir, candidate_bytes, errors,
                                              complete=candidate_complete, binding=protocol_binding)
            raise ProtocolFailure(receipt)
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
    except (BuilderError, OSError, PreflightError, ResponseEnvelopeError) as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1
    print(json.dumps({"status": "finalized", "resultStatus": payload["status"], "path": str(args.result)}, sort_keys=True))
    return 0 if payload["status"] == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
