#!/usr/bin/env python3
"""Regression matrix for Aquila V0-V3 routing and immutable attempt telemetry."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest import mock

import attempt_ledger
from attempt_ledger import LedgerError, append_attempt, load_attempt_history
from review_ladder import (
    ROUTING_PREFIX,
    RoutingError,
    select_review_route,
    task_class_promotion,
    validate_order_routing,
)


ROOT = Path("/tmp/review-ladder-regression")
TRUST = {
    "localNarrowBlastRadius": True,
    "cheapReversal": True,
    "deterministicFailureOracle": True,
    "noSensitiveOrExternalSideEffects": True,
    "requiredArtifactsPass": True,
    "requiredProofsPass": True,
    "noUncertainty": True,
    "noScopeOrAssumptionIssues": True,
}


def metadata(profile: str, **overrides: Any) -> dict[str, Any]:
    risk = "high" if profile == "V3" else ("medium" if profile == "V2" else "low")
    payload: dict[str, Any] = {
        "objectiveId": "routing-objective",
        "attempt": 1,
        "taskClass": "routine_implementation",
        "complexity": "medium",
        "risk": risk,
        "ambiguity": "medium" if profile == "V2" else "low",
        "reversibility": "high",
        "evidenceNeed": "high" if profile != "V0" else "low",
        "executor": "codex",
        "model": "gpt-5.6-sol",
        "reasoningEffort": "high",
        "executionProfile": "implementation",
        "verificationProfile": profile,
        "reviewer": {"V0": "none", "V1": "gpt-5.6-sol", "V2": "claude-opus-5", "V3": "claude-opus-5"}[profile],
        "confidence": "high",
        "reasons": [f"fixture route {profile}"],
    }
    if profile == "V0":
        payload["trustPredicates"] = dict(TRUST)
    if profile == "V3":
        payload["specialistGate"] = {"required": True, "approved": True, "approver": "Boss"}
    payload.update(overrides)
    return payload


def order_for(payload: dict[str, Any] | None, created_at: str = "2026-08-03T11:00:42Z") -> dict[str, Any]:
    executor = payload.get("executor", "codex") if payload else "codex"
    risk = payload.get("risk", "low") if payload else "low"
    notes = [] if payload is None else [ROUTING_PREFIX + json.dumps(payload, separators=(",", ":"))]
    return {
        "createdAt": created_at,
        "executor": executor,
        "riskLevel": risk,
        "notesForExecutor": notes,
    }


def expect_error(
    order: dict[str, Any],
    text: str,
    history: tuple[dict[str, Any], ...] | list[dict[str, Any]] = (),
) -> None:
    try:
        validate_order_routing(order, history)
    except RoutingError as exc:
        assert text in str(exc), f"expected {text!r}, got {exc!r}"
    else:
        raise AssertionError(f"expected routing failure containing {text!r}")


def ledger_row(order_id: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "objectiveId": "objective-1",
        "orderId": order_id,
        "attempt": 1,
        "taskClass": "routine_implementation",
        "executor": "codex",
        "model": "gpt-5.6-terra",
        "reviewer": "none",
        "risk": "low",
        "status": "done",
        "failureClass": "none",
        "resultPath": f"/tmp/{order_id}.json",
        "durationSeconds": 1.5,
    }
    row.update(overrides)
    return row


def main() -> int:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)

    assert validate_order_routing(order_for(None, "2026-08-03T11:00:41Z")) is None
    print("PASS pre-cutover order remains valid without routing metadata")

    expect_error(order_for(None), "exactly one")
    duplicate = order_for(metadata("V1"))
    duplicate["notesForExecutor"].append(duplicate["notesForExecutor"][0])
    expect_error(duplicate, "exactly one")
    malformed = order_for(None)
    malformed["notesForExecutor"] = [ROUTING_PREFIX + "{"]
    expect_error(malformed, "strict JSON")
    noncanonical = order_for(metadata("V1"))
    noncanonical["notesForExecutor"] = [ROUTING_PREFIX + json.dumps(metadata("V1"))]
    expect_error(noncanonical, "compact canonical")
    print("PASS post-cutover missing, duplicate, malformed, and noncanonical metadata fail closed")

    for profile in ("V0", "V1", "V2", "V3"):
        parsed = validate_order_routing(order_for(metadata(profile)))
        assert parsed is not None and parsed["verificationProfile"] == profile
        selected = select_review_route(parsed)
        expected_route = {"V0": "deterministic_only", "V1": "sol", "V2": "claude-opus-5", "V3": "claude-opus-5"}[profile]
        assert selected["route"] == expected_route
        if profile == "V0":
            assert selected["reviewer"] == "none", "V0 must launch no reviewer"
        if profile == "V3":
            assert selected["specialistGateRequired"] and selected["specialistGateSatisfied"]
    print("PASS every V0-V3 route selects the enforced reviewer and V0 selects none")

    sol_v0 = metadata("V0", complexity="high", model="gpt-5.6-sol")
    validate_order_routing(order_for(sol_v0))
    print("PASS executor model identity alone does not force senior review")

    trust_failure = metadata("V0")
    trust_failure["trustPredicates"]["requiredProofsPass"] = False
    expect_error(order_for(trust_failure), "hard floor V1")
    medium_v1 = metadata("V1", risk="medium")
    expect_error(order_for(medium_v1), "hard floor V2")
    irreversible_v1 = metadata("V1", reversibility="low")
    expect_error(order_for(irreversible_v1), "hard floor V2")
    security_v0 = metadata("V0", taskClass="security_boundary")
    expect_error(order_for(security_v0), "hard floor V3")
    v3_no_gate = metadata("V3")
    v3_no_gate.pop("specialistGate")
    expect_error(order_for(v3_no_gate), "specialistGate")
    print("PASS V0 trust predicates and V2/V3 hard floors cannot be weakened")

    terminal = metadata(
        "V1",
        executionProfile="terminal_review",
        reviewer="none",
        terminalGate=True,
        model="gpt-5.6-sol",
    )
    validate_order_routing(order_for(terminal))
    recursive = dict(terminal)
    recursive["reviewer"] = "gpt-5.6-sol"
    expect_error(order_for(recursive), "cannot select another reviewer")
    medium_terminal = dict(terminal, risk="medium")
    expect_error(order_for(medium_terminal), "hard floor V2")
    high_terminal = dict(terminal, risk="high")
    expect_error(order_for(high_terminal), "hard floor V3")
    v3_terminal = metadata(
        "V3",
        executor="claude",
        executionProfile="terminal_review",
        reviewer="none",
        terminalGate=True,
        model="claude-opus-5",
    )
    v3_terminal_no_gate = dict(v3_terminal)
    v3_terminal_no_gate.pop("specialistGate")
    expect_error(order_for(v3_terminal_no_gate), "specialistGate")
    validate_order_routing(order_for(v3_terminal))
    recursive_v3 = dict(v3_terminal, reviewer="claude-opus-5")
    expect_error(order_for(recursive_v3), "cannot select another reviewer")
    print("PASS terminal reviewer orders enforce V2/V3 floors, V3 gate, and no recursive reviewer")

    medium_escape = [ledger_row("escape-medium", failureClass="escaped_defect", severity="medium")]
    floor, _ = task_class_promotion(medium_escape, "routine_implementation")
    assert floor == "V2"
    low_history = [
        ledger_row("low-1", failureClass="escaped_defect", severity="low"),
        ledger_row("clean-1"),
        ledger_row("low-2", failureClass="escaped_defect", severity="low"),
    ]
    floor, _ = task_class_promotion(low_history, "routine_implementation")
    assert floor == "V1"
    low_history.extend(ledger_row(f"clean-after-{index}") for index in range(5))
    floor, _ = task_class_promotion(low_history, "routine_implementation")
    assert floor is None
    high_sol = [ledger_row("sol-high", reviewer="gpt-5.6-sol", failureClass="sol_miss", severity="high")]
    assert task_class_promotion(high_sol, "routine_implementation")[0] == "V2"
    medium_sol = [
        ledger_row("sol-medium-1", reviewer="gpt-5.6-sol", failureClass="sol_miss", severity="medium"),
        ledger_row("sol-medium-2", reviewer="gpt-5.6-sol", failureClass="sol_miss", severity="medium"),
    ]
    assert task_class_promotion(medium_sol, "routine_implementation")[0] == "V2"
    promoted_v0 = metadata("V0")
    expect_error(order_for(promoted_v0), "hard floor V2", medium_escape)
    selected_promotion = select_review_route(promoted_v0, medium_escape)
    assert selected_promotion["verificationProfile"] == "V2"
    assert selected_promotion["reviewer"] == "claude-opus-5"
    assert any(reason.startswith("promotion:") for reason in selected_promotion["reasons"])
    declared_promotion = dict(
        promoted_v0,
        verificationProfile="V2",
        reviewer="claude-opus-5",
        reasons=selected_promotion["reasons"],
    )
    validate_order_routing(order_for(declared_promotion), medium_escape)
    base_v2 = metadata("V2")
    ignored_promotion = select_review_route(base_v2, low_history[:3])
    assert ignored_promotion["verificationProfile"] == "V2"
    assert not any(reason.startswith("promotion:") for reason in ignored_promotion["reasons"])
    print("PASS escaped V0 and Sol-miss promotions enforce production floors with canonical reasons")

    ledger = ROOT / "attempts.jsonl"
    first = append_attempt(ledger, ledger_row("ledger-1"))
    first_line = ledger.read_bytes()
    assert all(first[field] == "unmeasured" for field in ("uncachedInput", "cachedInput", "output", "costUsd"))
    assert first["telemetryStatus"] == "unmeasured"
    append_attempt(
        ledger,
        ledger_row(
            "ledger-2",
            attempt=2,
            uncachedInput=12,
            cachedInput=8,
            output=3,
            costUsd=0.04,
            telemetryStatus="measured",
        ),
    )
    ledger_bytes = ledger.read_bytes()
    assert ledger_bytes.startswith(first_line) and len(ledger_bytes.splitlines()) == 2
    assert '"uncachedInput":0' not in first_line.decode("utf-8")
    with mock.patch.object(attempt_ledger.fcntl, "flock", wraps=attempt_ledger.fcntl.flock) as flock_call:
        loaded = load_attempt_history(ledger)
    assert len(loaded) == 2 and loaded[1]["orderId"] == "ledger-2"
    assert flock_call.call_args_list[0].args[1] == attempt_ledger.fcntl.LOCK_SH
    assert ledger.read_bytes() == ledger_bytes
    malformed_ledger = ROOT / "malformed.jsonl"
    malformed_ledger.write_text("{not-json\n", encoding="utf-8")
    try:
        load_attempt_history(malformed_ledger)
    except LedgerError as exc:
        assert "not valid JSON" in str(exc)
    else:
        raise AssertionError("malformed ledger history must fail closed")
    try:
        append_attempt(ledger, ledger_row("ledger-2", attempt=3))
    except ValueError as exc:
        assert "orderId already exists" in str(exc)
    else:
        raise AssertionError("ledger must reject duplicate immutable order identity")
    print("PASS ledger snapshot is shared-locked, read-only, fail-closed, and lineage-unique")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
