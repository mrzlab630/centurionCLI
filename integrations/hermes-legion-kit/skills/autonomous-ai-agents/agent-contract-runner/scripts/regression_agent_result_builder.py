#!/usr/bin/env python3
"""Regression checks for create-only AGENT_RESULT_JSON_V1 construction."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

import agent_result_builder as builder
from agent_result_builder import BuilderError, build_result, resolve_schema_path


ROOT = Path("/tmp/agent-result-builder-regression")
SCHEMA = Path(__file__).resolve().parent.parent / "references" / "agent-result.schema.json"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ambiguous_json_bytes(original: bytes, variant: str, duplicate_key: str = "orderId") -> bytes:
    text = original.decode("utf-8").rstrip()
    if variant == "duplicate-key":
        return (json.dumps({duplicate_key: "ambiguous"})[:-1] + "," + text[1:] + "\n").encode("utf-8")
    literal = {
        "nan": "NaN",
        "infinity": "Infinity",
        "negative-infinity": "-Infinity",
        "overflow": "1e999",
    }[variant]
    return (text[:-1] + ',"ambiguous":' + literal + "}\n").encode("utf-8")


def make_case(name: str, status: str = "done") -> tuple[Path, Path, Path, Path, Path, dict[str, Any]]:
    case = ROOT / name
    case.mkdir(parents=True)
    product = case / "product.txt"
    product.write_text("unchanged product bytes\n", encoding="utf-8")
    result = case / "result.json"
    candidate = case / "candidate.json"
    evidence = case / "evidence"
    order = {
        "orderVersion": "AGENT_ORDER_JSON_V1",
        "orderId": f"builder-{name}",
        "executor": "codex",
        "workspace": {"repoPath": str(ROOT)},
        "outputContract": {"resultVersion": "AGENT_RESULT_JSON_V1", "resultPath": str(result)},
    }
    payload = {
        "resultVersion": "AGENT_RESULT_JSON_V1",
        "orderId": order["orderId"],
        "executor": "codex",
        "status": status,
        "summary": f"candidate remains {status}",
        "filesChanged": [{"path": str(product), "action": "none"}],
        "artifacts": [{"path": str(product), "exists": True, "type": "fixture", "note": "product fixture"}],
        "proof": [{"command": "fixture proof", "cwd": str(case), "status": "pass", "exitCode": 0, "summary": "fixture passed"}],
        "selfReview": {"performed": True, "findings": [], "fixesApplied": []},
        "scopeDeviations": [],
        "forbiddenPatternHits": [],
        "remainingRisks": [],
        "questions": [],
        "errors": [],
        "stdoutSummary": "",
        "stderrSummary": "",
    }
    order_path = case / "order.json"
    write_json(order_path, order)
    write_json(candidate, payload)
    return order_path, candidate, result, evidence, product, payload


def finalized(name: str, mutate: Any = None, status: str = "done") -> tuple[dict[str, Any], bytes, Path, Path]:
    order, candidate, result, evidence, product, payload = make_case(name, status=status)
    if mutate is not None:
        mutate(payload)
        write_json(candidate, payload)
    original = candidate.read_bytes()
    product_before = hashlib.sha256(product.read_bytes()).hexdigest()
    built = build_result(order, candidate, result, evidence)
    assert hashlib.sha256(product.read_bytes()).hexdigest() == product_before, "builder must not modify product bytes"
    return built, original, result, evidence


def assert_failed_with_evidence(built: dict[str, Any], original: bytes, evidence: Path) -> None:
    assert built["status"] == "failed", "malformed candidate must never become done"
    digest = hashlib.sha256(original).hexdigest()
    evidence_path = evidence / f"{digest}.candidate-result.bin"
    assert evidence_path.read_bytes() == original, "original malformed bytes must be preserved exactly"
    assert built["artifacts"][0]["path"] == str(evidence_path), "failed result must bind the evidence path"


def main() -> int:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    explicit_schema = ROOT / "explicit-schema.json"
    environment_schema = ROOT / "environment-schema.json"
    hermes_home = ROOT / "hermes-home"
    fallback_home = ROOT / "fallback-home"
    with patch.dict(os.environ, {"AQUILA_AGENT_RESULT_SCHEMA": str(environment_schema), "HERMES_HOME": str(hermes_home)}):
        assert resolve_schema_path(explicit_schema) == explicit_schema
        assert resolve_schema_path() == environment_schema
    with patch.dict(os.environ, {"AQUILA_AGENT_RESULT_SCHEMA": "", "HERMES_HOME": str(hermes_home)}):
        assert resolve_schema_path() == SCHEMA
    with patch.object(builder, "PACKAGED_SCHEMA", ROOT / "missing-packaged-schema.json"):
        with patch.dict(os.environ, {"AQUILA_AGENT_RESULT_SCHEMA": "", "HERMES_HOME": str(hermes_home)}):
            assert resolve_schema_path() == hermes_home / "contracts" / "agent-result.schema.json"
        with patch.dict(os.environ, {"AQUILA_AGENT_RESULT_SCHEMA": "", "HERMES_HOME": ""}):
            with patch.object(Path, "home", return_value=fallback_home):
                assert resolve_schema_path() == fallback_home / ".hermes" / "contracts" / "agent-result.schema.json"
    print("PASS schema precedence is explicit, environment, packaged, HERMES_HOME, then HOME")

    valid, _, valid_result, _ = finalized("valid")
    assert valid["status"] == "done"
    validator.validate(json.loads(valid_result.read_text(encoding="utf-8")))
    print("PASS valid candidate finalized once with canonical identity and schema")

    semantic_cases = {
        "failed-proof": lambda payload: payload["proof"][0].__setitem__("status", "fail"),
        "unperformed-self-review": lambda payload: payload["selfReview"].__setitem__("performed", False),
        "scope-deviation": lambda payload: payload["scopeDeviations"].append("outside"),
        "forbidden-hit": lambda payload: payload["forbiddenPatternHits"].append("secret"),
    }
    for name, mutate in semantic_cases.items():
        candidate = json.loads(json.dumps(valid))
        mutate(candidate)
        try:
            validator.validate(candidate)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"done schema semantic gate must reject {name}")
    for status in ("blocked", "failed"):
        candidate = json.loads(json.dumps(valid))
        candidate.update({
            "status": status,
            "proof": [],
            "selfReview": {"performed": False, "findings": [], "fixesApplied": []},
            "scopeDeviations": ["not accepted"],
            "forbiddenPatternHits": ["not accepted"],
        })
        validator.validate(candidate)
    print("PASS schema conditional gate restricts done and leaves blocked/failed unconstrained")

    relative_order, relative_candidate, relative_result, relative_evidence, _, _ = make_case("relative")
    relative_order_payload = json.loads(relative_order.read_text(encoding="utf-8"))
    relative_order_payload["outputContract"]["resultPath"] = str(relative_result.relative_to(ROOT))
    write_json(relative_order, relative_order_payload)
    relative = build_result(relative_order, relative_candidate, relative_result, relative_evidence)
    assert relative["status"] == "done"
    print("PASS relative result path resolves against workspace.repoPath")

    absolute_order, absolute_candidate, absolute_result, absolute_evidence, _, _ = make_case("absolute")
    absolute = build_result(absolute_order, absolute_candidate, absolute_result, absolute_evidence)
    assert absolute["status"] == "done"
    print("PASS absolute result path remains accepted")

    mismatch_order, mismatch_candidate, mismatch_result, mismatch_evidence, _, _ = make_case("mismatch")
    mismatch_payload = json.loads(mismatch_order.read_text(encoding="utf-8"))
    mismatch_payload["outputContract"]["resultPath"] = "mismatch/other-result.json"
    write_json(mismatch_order, mismatch_payload)
    try:
        build_result(mismatch_order, mismatch_candidate, mismatch_result, mismatch_evidence)
    except BuilderError as exc:
        assert "exactly match" in str(exc)
    else:
        raise AssertionError("mismatched result path must be rejected")
    print("PASS mismatched result path is rejected")

    escape_order, escape_candidate, escape_result, escape_evidence, _, _ = make_case("escape")
    escape_payload = json.loads(escape_order.read_text(encoding="utf-8"))
    escape_payload["outputContract"]["resultPath"] = "../escaped-result.json"
    write_json(escape_order, escape_payload)
    try:
        build_result(escape_order, escape_candidate, escape_result, escape_evidence)
    except BuilderError as exc:
        assert "workspace.repoPath" in str(exc)
    else:
        raise AssertionError("escaping relative result path must be rejected")
    print("PASS escaping relative result path is rejected")

    cases = {
        "proof-near-miss": lambda payload: payload["proof"][0].__setitem__("status", "pass_with_finding"),
        "files-changed-string": lambda payload: payload.__setitem__("filesChanged", "product.txt"),
        "self-review-string": lambda payload: payload.__setitem__("selfReview", "performed"),
        "wrong-order-id": lambda payload: payload.__setitem__("orderId", "wrong-order-id"),
        "wrong-executor": lambda payload: payload.__setitem__("executor", "claude"),
    }
    for name, mutate in cases.items():
        built, original, result, evidence = finalized(name, mutate)
        assert_failed_with_evidence(built, original, evidence)
        validator.validate(json.loads(result.read_text(encoding="utf-8")))
        print(f"PASS {name} rejected without status promotion")

    order, candidate, result, evidence, product, _ = make_case("unparseable")
    candidate.write_bytes(b"{not-json\x00")
    product_before = product.read_bytes()
    unparseable = build_result(order, candidate, result, evidence)
    assert product.read_bytes() == product_before
    assert_failed_with_evidence(unparseable, b"{not-json\x00", evidence)
    print("PASS unparseable original bytes preserved by SHA-256 evidence")

    for variant in ("duplicate-key", "nan", "infinity", "negative-infinity", "overflow"):
        order, candidate, result, evidence, _, _ = make_case(f"strict-candidate-{variant}")
        original = ambiguous_json_bytes(candidate.read_bytes(), variant)
        candidate.write_bytes(original)
        built = build_result(order, candidate, result, evidence)
        assert_failed_with_evidence(built, original, evidence)
    print("PASS builder rejects duplicate keys, NaN, Infinity, -Infinity, and 1e999 candidates")

    for variant in ("duplicate-key", "nan", "infinity", "negative-infinity", "overflow"):
        order, candidate, result, evidence, _, _ = make_case(f"strict-order-{variant}")
        order.write_bytes(ambiguous_json_bytes(order.read_bytes(), variant))
        try:
            build_result(order, candidate, result, evidence)
        except BuilderError as exc:
            assert "strict JSON" in str(exc)
        else:
            raise AssertionError(f"builder must reject {variant} order JSON")
        assert not result.exists()
    print("PASS builder rejects ambiguous and overflowed order JSON before finalization")

    strict_schema = ROOT / "strict-schema.json"
    for variant in ("duplicate-key", "nan", "infinity", "negative-infinity", "overflow"):
        strict_schema.write_bytes(ambiguous_json_bytes(SCHEMA.read_bytes(), variant, "$schema"))
        try:
            builder._load_schema(strict_schema)
        except BuilderError as exc:
            assert "strict JSON" in str(exc)
        else:
            raise AssertionError(f"builder must reject {variant} schema JSON")
    print("PASS builder rejects duplicate keys, non-finite constants, and 1e999 schemas")

    for status in ("blocked", "failed"):
        built, _, _, _ = finalized(f"preserve-{status}", status=status)
        assert built["status"] == status, f"valid {status} candidate must not be promoted"
    print("PASS blocked and failed candidate verdicts are preserved")

    order, candidate, result, evidence, product, _ = make_case("collision")
    result.write_text("existing result bytes\n", encoding="utf-8")
    try:
        build_result(order, candidate, result, evidence)
    except BuilderError as exc:
        assert "result path collision" in str(exc)
    else:
        raise AssertionError("create-only finalization must reject a result collision")
    assert result.read_text(encoding="utf-8") == "existing result bytes\n"
    assert product.read_text(encoding="utf-8") == "unchanged product bytes\n"
    print("PASS create-only collision preserves existing result and product bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
