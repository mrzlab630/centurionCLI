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

from strict_json import StrictJSONError, strict_json_load_bytes, strict_json_load_path


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
    return sorted(set(errors))


def preserve_original(candidate_bytes: bytes, evidence_dir: Path) -> Path:
    digest = hashlib.sha256(candidate_bytes).hexdigest()
    evidence_path = evidence_dir / f"{digest}.candidate-result.bin"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if hashlib.sha256(evidence_path.read_bytes()).hexdigest() != digest:
            raise BuilderError(f"evidence hash collision at {evidence_path}")
        return evidence_path
    try:
        offset = 0
        while offset < len(candidate_bytes):
            offset += os.write(fd, candidate_bytes[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    return evidence_path


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
    return {
        "resultVersion": RESULT_VERSION,
        "orderId": order["orderId"],
        "executor": order["executor"],
        "status": "failed",
        "summary": "Candidate result rejected by deterministic validation.",
        "filesChanged": [{"path": str(evidence_path), "action": "added"}],
        "artifacts": [
            {
                "path": str(evidence_path),
                "exists": True,
                "type": "malformed-result-evidence",
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
    output_contract = order.get("outputContract")
    if not isinstance(output_contract, dict) or output_contract.get("resultPath") != str(result_path):
        raise BuilderError("result path must exactly match order.outputContract.resultPath")

    _, validator = _load_schema(resolve_schema_path(schema_path))
    try:
        candidate_bytes = candidate_path.read_bytes()
    except FileNotFoundError:
        candidate_bytes = b""
    except OSError as exc:
        raise BuilderError(f"could not read candidate: {exc}") from exc
    parse_errors: list[str] = []
    try:
        candidate = strict_json_load_bytes(candidate_bytes, "candidate result")
    except StrictJSONError as exc:
        candidate = None
        parse_errors.append(f"candidate JSON parse failed: {exc}")
    errors = parse_errors + validate_candidate(candidate, order, validator)
    if errors:
        evidence_path = preserve_original(candidate_bytes, evidence_dir)
        payload = failed_result(order, evidence_path, sorted(set(errors)))
        schema_errors = _schema_errors(validator, payload)
        if schema_errors:
            raise BuilderError("internal failed-result schema error: " + "; ".join(schema_errors))
    else:
        payload = candidate
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
