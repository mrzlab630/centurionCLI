#!/usr/bin/env python3
"""Offline regression checks for the opt-in execution-state projection."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from execution_state import (  # noqa: E402
    MAX_SUMMARY_BYTES,
    MAX_STATE_BYTES,
    STATE_VERSION,
    ExecutionStateError,
    _canonical_bytes,
    project,
    validate_state,
)

SCHEMA_PATH = SCRIPT_DIR.parent / "references" / "execution-state.schema.json"
SCHEMA_VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fixture(root: Path) -> tuple[Path, Path, Path, dict]:
    order = {
        "orderVersion": "AGENT_ORDER_JSON_V1",
        "orderId": "state-order-001",
        "executor": "codex",
        "objective": "bounded state projection",
        "workspace": {"projectName": "state-fixture"},
        "loopContract": {
            "phase": "verify",
            "workItem": {"workItemId": "item-001", "project": "state-fixture", "objective": "bounded state projection"},
            "iteration": {"current": 1, "max": 3},
        },
    }
    result = {
        "resultVersion": "AGENT_RESULT_JSON_V1",
        "orderId": "state-order-001",
        "executor": "codex",
        "status": "done",
        "summary": "projection accepted",
    }
    evidence = [{
        "kind": "receipt",
        "path": "/evidence/receipt.json",
        "sha256": "a" * 64,
        "bytes": 12,
        "scope": {
            "project": "state-fixture",
            "objective": "bounded state projection",
            "workItemId": "item-001",
            "orderId": "state-order-001",
        },
    }]
    paths = []
    for name, value in (("order.json", order), ("result.json", result), ("evidence.json", evidence)):
        path = root / name
        path.write_bytes(json.dumps(value, indent=2).encode("utf-8"))
        paths.append(path)
    return paths[0], paths[1], paths[2], order


def rejects(fn, marker: str) -> None:
    try:
        fn()
    except (ExecutionStateError, ValueError) as exc:
        check(marker.lower() in str(exc).lower(), f"rejection did not mention {marker!r}: {exc}")
    else:
        raise AssertionError(f"expected rejection: {marker}")


def schema_validates(state: dict) -> None:
    errors = sorted(SCHEMA_VALIDATOR.iter_errors(state), key=lambda error: list(error.absolute_path))
    check(not errors, f"execution-state schema rejected generated artifact: {errors[0].message if errors else ''}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="execution-state-regression-") as temp:
        root = Path(temp)
        order_path, result_path, evidence_path, order = fixture(root)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        original_order = order_path.read_bytes()
        state = project(order_path, result_path, evidence_path)
        check(state["stateVersion"] == STATE_VERSION, "projection version")
        check(state["execution"]["status"] == "completed", "done result maps to completed")
        check(state["provenance"]["mode"] == "read-only-derived", "provenance mode")
        check(len(_canonical_bytes(state)) < 16 * 1024, "bounded state")
        check(order_path.read_bytes() == original_order, "input bytes preserved")
        validate_state(state)
        schema_validates(state)

        legacy_order = copy.deepcopy(json.loads(order_path.read_text(encoding="utf-8")))
        legacy_order["loopContract"].pop("phase")
        legacy_order_path = root / "legacy-order.json"
        legacy_order_path.write_text(json.dumps(legacy_order), encoding="utf-8")
        legacy_result = json.loads(result_path.read_text(encoding="utf-8"))
        for result_status, expected_status in (("done", "completed"), ("blocked", "blocked"), ("failed", "failed")):
            legacy_result["status"] = result_status
            legacy_result_path = root / f"legacy-{result_status}-result.json"
            legacy_result_path.write_text(json.dumps(legacy_result), encoding="utf-8")
            rejects(
                lambda legacy_result_path=legacy_result_path: project(legacy_order_path, legacy_result_path),
                "incoherent phase/status pair",
            )
            compatibility = project(
                legacy_order_path,
                legacy_result_path,
                legacy_terminal_compat=True,
            )
            check(compatibility["execution"]["phase"] == "verify", "legacy compatibility maps to verify")
            check(compatibility["execution"]["status"] == expected_status, "legacy terminal status preserved")
            check(
                compatibility["provenance"]["mode"] == "read-only-derived-legacy-terminal",
                "legacy compatibility provenance mode",
            )
            check(compatibility["revision"]["sequence"] == 0, "legacy compatibility is a snapshot")
            validate_state(compatibility)
            schema_validates(compatibility)
            replay = project(legacy_order_path, legacy_result_path, legacy_terminal_compat=True)
            check(_canonical_bytes(compatibility) == _canonical_bytes(replay), "legacy replay is deterministic")

        parent_path = root / "parent.json"
        parent_path.write_bytes(_canonical_bytes(state) + b"\n")
        rejects(
            lambda: project(
                legacy_order_path,
                root / "legacy-done-result.json",
                parent_path=parent_path,
                legacy_terminal_compat=True,
            ),
            "cannot use a parent",
        )
        explicit_execute = copy.deepcopy(legacy_order)
        explicit_execute["loopContract"]["phase"] = "execute"
        explicit_execute_path = root / "explicit-execute-order.json"
        explicit_execute_path.write_text(json.dumps(explicit_execute), encoding="utf-8")
        rejects(
            lambda: project(
                explicit_execute_path,
                root / "legacy-done-result.json",
                legacy_terminal_compat=True,
            ),
            "contradictory explicit lifecycle phase",
        )
        explicit_verify = copy.deepcopy(legacy_order)
        explicit_verify["loopContract"]["phase"] = "verify"
        explicit_verify_path = root / "explicit-verify-order.json"
        explicit_verify_path.write_text(json.dumps(explicit_verify), encoding="utf-8")
        explicit_verify_state = project(explicit_verify_path, root / "legacy-done-result.json")
        check(explicit_verify_state["provenance"]["mode"] == "read-only-derived", "explicit verify remains ordinary")
        validate_state(explicit_verify_state)
        explicit_verify_compat = project(
            explicit_verify_path,
            root / "legacy-done-result.json",
            legacy_terminal_compat=True,
        )
        check(
            explicit_verify_compat["provenance"]["mode"] == "read-only-derived-legacy-terminal",
            "explicit verify compatibility provenance",
        )
        validate_state(explicit_verify_compat)

        for phase, status in (("execute", "completed"), ("execute", "blocked"), ("execute", "failed"), ("verify", "planned"), ("verify", "running")):
            invalid = copy.deepcopy(state)
            invalid["execution"]["phase"] = phase
            invalid["execution"]["status"] = status
            rejects(lambda invalid=invalid: validate_state(invalid), "incoherent phase/status pair")

        for phase, status in (("execute", "planned"), ("execute", "running"), ("execute", "awaiting_verification"), ("verify", "awaiting_verification"), ("verify", "completed"), ("verify", "blocked"), ("verify", "failed")):
            valid = copy.deepcopy(state)
            valid["execution"]["phase"] = phase
            valid["execution"]["status"] = status
            validate_state(valid)

        unknown = copy.deepcopy(state)
        unknown["unexpected"] = True
        rejects(lambda: validate_state(unknown), "unknown keys")
        cross_scope_result = root / "cross-scope-result.json"
        mismatched_result = json.loads(result_path.read_text(encoding="utf-8"))
        mismatched_result["orderId"] = "other-order"
        cross_scope_result.write_text(json.dumps(mismatched_result), encoding="utf-8")
        rejects(lambda: project(order_path, cross_scope_result), "result.orderId")
        contradictory_order = copy.deepcopy(order)
        contradictory_order["loopContract"]["workItem"]["status"] = "completed"
        contradictory_order_path = root / "contradictory-order.json"
        contradictory_order_path.write_text(json.dumps(contradictory_order), encoding="utf-8")
        contradictory_result = copy.deepcopy(result)
        contradictory_result["status"] = "failed"
        contradictory_result_path = root / "contradictory-result.json"
        contradictory_result_path.write_text(json.dumps(contradictory_result), encoding="utf-8")
        rejects(lambda: project(contradictory_order_path, contradictory_result_path), "status disagree")
        invalid_result = copy.deepcopy(result)
        invalid_result["status"] = "unexpected"
        invalid_result_path = root / "invalid-result.json"
        invalid_result_path.write_text(json.dumps(invalid_result), encoding="utf-8")
        rejects(lambda: project(contradictory_order_path, invalid_result_path), "result.status")
        stale_parent = copy.deepcopy(state)
        stale_parent["revision"]["sequence"] = 1
        stale_parent["revision"]["parentSha256"] = "b" * 64
        rejects(lambda: validate_state(stale_parent, parent=state), "parent hash")
        unproven_revision = copy.deepcopy(state)
        unproven_revision["revision"]["sequence"] = 1
        unproven_revision["revision"]["parentSha256"] = "c" * 64
        rejects(lambda: validate_state(unproven_revision), "explicit parent state")
        schema_unproven = copy.deepcopy(unproven_revision)
        schema_unproven["revision"]["parentSha256"] = None
        errors = list(SCHEMA_VALIDATOR.iter_errors(schema_unproven))
        check(errors, "schema accepts nonzero revision without parent hash")
        missing_order_digest = copy.deepcopy(state)
        missing_order_digest["revision"].pop("orderSha256")
        rejects(lambda: validate_state(missing_order_digest), "orderSha256")
        null_order_digest = copy.deepcopy(state)
        null_order_digest["revision"]["orderSha256"] = None
        rejects(lambda: validate_state(null_order_digest), "orderSha256")
        phase_parent = copy.deepcopy(state)
        phase_parent["execution"] = {"phase": "execute", "status": "running"}
        phase_child = copy.deepcopy(state)
        phase_child["execution"] = {"phase": "verify", "status": "awaiting_verification"}
        phase_child["revision"]["sequence"] = 1
        phase_child["revision"]["parentSha256"] = hashlib.sha256(_canonical_bytes(phase_parent)).hexdigest()
        rejects(lambda: validate_state(phase_child, parent=phase_parent, parent_bytes=_canonical_bytes(phase_parent)), "requires awaiting_verification")
        phase_parent["execution"]["status"] = "awaiting_verification"
        phase_child["revision"]["parentSha256"] = hashlib.sha256(_canonical_bytes(phase_parent)).hexdigest()
        validate_state(phase_child, parent=phase_parent, parent_bytes=_canonical_bytes(phase_parent))
        invalid_transition = copy.deepcopy(state)
        invalid_transition["execution"]["status"] = "blocked"
        invalid_transition["revision"]["sequence"] = 1
        invalid_transition["revision"]["parentSha256"] = hashlib.sha256(_canonical_bytes(state)).hexdigest()
        rejects(lambda: validate_state(invalid_transition, parent=state, parent_bytes=_canonical_bytes(state)), "transition")
        for container in ("sources", "evidence"):
            bad_bytes = copy.deepcopy(state)
            bad_bytes["provenance"][container][0]["bytes"] = True
            rejects(lambda bad_bytes=bad_bytes: validate_state(bad_bytes), "bytes is invalid")

        duplicate = root / "duplicate.json"
        duplicate.write_text('{"orderVersion":"AGENT_ORDER_JSON_V1","orderVersion":"AGENT_ORDER_JSON_V1"}', encoding="utf-8")
        rejects(lambda: project(duplicate), "duplicate key")
        non_finite = root / "non-finite.json"
        non_finite.write_text('{"orderId":"x","objective":"x","value":NaN}', encoding="utf-8")
        rejects(lambda: project(non_finite), "non-finite")
        bad_evidence = root / "bad-evidence.json"
        bad_evidence.write_text(json.dumps([{**json.loads(evidence_path.read_text())[0], "scope": {"project": "wrong", "objective": "bounded state projection", "workItemId": "item-001", "orderId": "state-order-001"}}]), encoding="utf-8")
        rejects(lambda: project(order_path, result_path, bad_evidence), "does not match order scope")

        result_obj = json.loads(result_path.read_text(encoding="utf-8"))
        result_512_path = root / "result-512.json"
        result_obj["summary"] = "x" * MAX_SUMMARY_BYTES
        result_512_path.write_text(json.dumps(result_obj), encoding="utf-8")
        state_512 = project(order_path, result_512_path)
        check(state_512["execution"]["summary"] == "x" * MAX_SUMMARY_BYTES, "512-byte summary retained")
        check("summaryOmitted" not in state_512["execution"], "512-byte summary has no omission marker")
        validate_state(state_512)
        schema_validates(state_512)

        result_513_path = root / "result-513.json"
        result_obj["summary"] = "x" * (MAX_SUMMARY_BYTES + 1)
        result_513_path.write_text(json.dumps(result_obj), encoding="utf-8")
        state_513 = project(order_path, result_513_path)
        check("summary" not in state_513["execution"], "513-byte summary is omitted")
        check(
            state_513["execution"]["summaryOmitted"] == {"reason": "result-summary-over-bound", "sourceBytes": 513},
            "513-byte omission marker",
        )
        check(
            state_513["revision"]["resultSha256"] == hashlib.sha256(result_513_path.read_bytes()).hexdigest(),
            "over-limit result hash remains exact",
        )
        check(len(_canonical_bytes(state_513)) + 1 <= MAX_STATE_BYTES, "513-byte state remains bounded")
        validate_state(state_513)
        schema_validates(state_513)
        legacy_long_result = copy.deepcopy(legacy_result)
        legacy_long_result["status"] = "done"
        legacy_long_result["summary"] = "x" * (MAX_SUMMARY_BYTES + 1)
        legacy_long_result_path = root / "legacy-long-result.json"
        legacy_long_result_path.write_text(json.dumps(legacy_long_result), encoding="utf-8")
        legacy_long_state = project(legacy_order_path, legacy_long_result_path, legacy_terminal_compat=True)
        check(legacy_long_state["provenance"]["mode"] == "read-only-derived-legacy-terminal", "legacy long summary mode")
        check(legacy_long_state["execution"]["summaryOmitted"]["sourceBytes"] == MAX_SUMMARY_BYTES + 1, "legacy long summary omission")
        validate_state(legacy_long_state)
        schema_validates(legacy_long_state)

        result_utf8_path = root / "result-utf8.json"
        result_obj["summary"] = "é" * (MAX_SUMMARY_BYTES // 2)
        result_utf8_path.write_text(json.dumps(result_obj, ensure_ascii=False), encoding="utf-8")
        state_utf8 = project(order_path, result_utf8_path)
        check(len(state_utf8["execution"]["summary"].encode("utf-8")) == MAX_SUMMARY_BYTES, "UTF-8 512-byte summary retained")
        schema_validates(state_utf8)
        result_utf8_over_path = root / "result-utf8-over.json"
        result_obj["summary"] = "é" * ((MAX_SUMMARY_BYTES // 2) + 1)
        result_utf8_over_path.write_text(json.dumps(result_obj, ensure_ascii=False), encoding="utf-8")
        state_utf8_over = project(order_path, result_utf8_over_path)
        check("summary" not in state_utf8_over["execution"], "UTF-8 over-limit summary omitted")
        check(state_utf8_over["execution"]["summaryOmitted"]["sourceBytes"] == MAX_SUMMARY_BYTES + 2, "UTF-8 source bytes recorded")
        validate_state(state_utf8_over)
        schema_validates(state_utf8_over)

        missing_summary = copy.deepcopy(result_obj)
        missing_summary.pop("summary")
        missing_summary_path = root / "result-missing-summary.json"
        missing_summary_path.write_text(json.dumps(missing_summary), encoding="utf-8")
        state_missing_summary = project(order_path, missing_summary_path)
        check("summary" not in state_missing_summary["execution"], "missing summary remains absent")
        check("summaryOmitted" not in state_missing_summary["execution"], "missing summary has no omission marker")
        validate_state(state_missing_summary)
        schema_validates(state_missing_summary)

        oversized = copy.deepcopy(state)
        oversized["execution"]["summary"] = "x" * (MAX_SUMMARY_BYTES + 1)
        rejects(lambda: validate_state(oversized), "exceeds 512")
        malformed_omission = copy.deepcopy(state)
        malformed_omission["execution"].pop("summary")
        malformed_omission["execution"]["summaryOmitted"] = {"reason": "wrong", "sourceBytes": 513}
        rejects(lambda: validate_state(malformed_omission), "summaryOmitted.reason")
        unbound_omission = copy.deepcopy(state_513)
        unbound_omission["revision"]["resultSha256"] = None
        rejects(lambda: validate_state(unbound_omission), "requires a result source hash")
        boundary = copy.deepcopy(state)
        boundary["provenance"]["evidence"] = [
            {"kind": "receipt", "path": "x", "sha256": "a" * 64, "bytes": 0}
            for _ in range(32)
        ]
        remaining = MAX_STATE_BYTES - 1 - len(_canonical_bytes(boundary))
        check(0 <= remaining <= 32 * 1023, "construct state byte boundary")
        for ref in boundary["provenance"]["evidence"]:
            growth = min(1023, remaining)
            ref["path"] += "x" * growth
            remaining -= growth
        check(len(_canonical_bytes(boundary)) + 1 == MAX_STATE_BYTES, "state boundary includes output newline")
        validate_state(boundary)
        over_boundary = copy.deepcopy(boundary)
        over_boundary["provenance"]["evidence"][-1]["path"] += "x"
        rejects(lambda: validate_state(over_boundary), "state exceeds")
        output = root / "out.json"
        before = set(root.iterdir())
        run = subprocess.run([sys.executable, str(SCRIPT_DIR / "execution_state.py"), "--help"], cwd=root, text=True, capture_output=True, check=False)
        check(run.returncode == 0 and not (root / "state.json").exists(), "default-off help does not project or mutate")
        check(set(root.iterdir()) == before, "no repository/runtime mutation")
        run = subprocess.run([sys.executable, str(SCRIPT_DIR / "execution_state.py"), "project", "--order", str(order_path), "--result", str(result_path), "--evidence", str(evidence_path), "--output", str(output)], cwd=root, text=True, capture_output=True, check=False)
        check(run.returncode == 0 and output.exists(), "explicit projection CLI")
        legacy_cli_output = root / "legacy-cli.json"
        legacy_default = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "execution_state.py"), "project", "--order", str(legacy_order_path), "--result", str(root / "legacy-done-result.json"), "--output", str(legacy_cli_output)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        check(legacy_default.returncode != 0 and not legacy_cli_output.exists(), "legacy CLI remains strict by default")
        legacy_cli = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "execution_state.py"), "project", "--order", str(legacy_order_path), "--result", str(root / "legacy-done-result.json"), "--legacy-terminal-compat", "--output", str(legacy_cli_output)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        check(legacy_cli.returncode == 0 and legacy_cli_output.exists(), "legacy compatibility CLI")
        check(json.loads(legacy_cli_output.read_text(encoding="utf-8"))["provenance"]["mode"] == "read-only-derived-legacy-terminal", "legacy CLI provenance")
        check(hashlib.sha256(order_path.read_bytes()).hexdigest() == hashlib.sha256(original_order).hexdigest(), "order digest unchanged")
        for alias in (order_path, result_path, evidence_path):
            before_bytes = alias.read_bytes()
            collision = subprocess.run([sys.executable, str(SCRIPT_DIR / "execution_state.py"), "project", "--order", str(order_path), "--result", str(result_path), "--evidence", str(evidence_path), "--output", str(alias)], cwd=root, text=True, capture_output=True, check=False)
            check(collision.returncode != 0 and alias.read_bytes() == before_bytes, f"output collision rejected for {alias.name}")
        parent_bytes = output.read_bytes()
        collision = subprocess.run([sys.executable, str(SCRIPT_DIR / "execution_state.py"), "project", "--order", str(order_path), "--result", str(result_path), "--evidence", str(evidence_path), "--parent", str(output), "--output", str(output)], cwd=root, text=True, capture_output=True, check=False)
        check(collision.returncode != 0 and output.read_bytes() == parent_bytes, "output collision rejected for parent")
        hardlink = root / "hardlink-output.json"
        hardlink.hardlink_to(order_path)
        before_hardlink = hardlink.read_bytes()
        collision = subprocess.run([sys.executable, str(SCRIPT_DIR / "execution_state.py"), "project", "--order", str(order_path), "--output", str(hardlink)], cwd=root, text=True, capture_output=True, check=False)
        check(collision.returncode != 0 and hardlink.read_bytes() == before_hardlink, "hardlink output collision rejected")
    print("PASS execution-state projection, strict rejection, provenance, bounds, bytes, and default-off regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
