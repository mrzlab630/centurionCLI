#!/usr/bin/env python3
"""Regression matrix for Aquila V0-V3 routing and immutable attempt telemetry."""

from __future__ import annotations

import json
import shutil
import atexit
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

import attempt_ledger
from attempt_ledger import LedgerError, append_attempt, load_attempt_history
from review_ladder import (
    POST_EXECUTION_PREDICATES,
    ROUTING_PREFIX,
    RoutingError,
    MODEL_REASONING_EFFORTS,
    REVIEWER_FALLBACK_BY_PROFILE,
    SOL_PRIMARY_MODEL,
    minimum_profile,
    select_review_route,
    task_class_promotion,
    validate_order_routing,
)


ROOT = Path(tempfile.mkdtemp(prefix="review-ladder-regression-"))
atexit.register(shutil.rmtree, ROOT, ignore_errors=True)
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
        "executor": "claude" if profile == "V1" else "codex",
        "model": "claude-opus-5-5" if profile == "V1" else SOL_PRIMARY_MODEL,
        "reasoningEffort": "high",
        "executionProfile": "implementation",
        "verificationProfile": profile,
        "reviewer": {"V0": "none", "V1": SOL_PRIMARY_MODEL, "V2": "claude-opus-5-5", "V3": "claude-opus-5-5"}[profile],
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
    order = {
        "createdAt": created_at,
        "executor": executor,
        "riskLevel": risk,
        "roleForTask": "ARCHITECTUS" if payload and payload.get("executionProfile") == "advisory" else "regression fixture",
        "notesForExecutor": notes,
    }
    if payload and payload.get("verificationProfile") == "V0":
        order["proofCommands"] = [{"command": "python3 -c 'pass'", "cwd": "/tmp", "required": True}]
    return order


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
        "model": "gpt-6-luna",
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
    base_routing = json.dumps(metadata("V1"), separators=(",", ":"))
    strict_routing = {
        "duplicate-key": '{"objectiveId":"ambiguous",' + base_routing[1:],
        "nan": base_routing[:-1] + ',"ambiguous":NaN}',
        "infinity": base_routing[:-1] + ',"ambiguous":Infinity}',
        "negative-infinity": base_routing[:-1] + ',"ambiguous":-Infinity}',
        "overflow": base_routing[:-1] + ',"ambiguous":1e999}',
    }
    for raw in strict_routing.values():
        strict_order = order_for(None)
        strict_order["notesForExecutor"] = [ROUTING_PREFIX + raw]
        expect_error(strict_order, "strict JSON")
    print("PASS post-cutover missing, duplicate, malformed, noncanonical, and non-finite metadata fail closed")

    for profile in ("V0", "V1", "V2"):
        parsed = validate_order_routing(order_for(metadata(profile)))
        assert parsed is not None and parsed["verificationProfile"] == profile
        selected = select_review_route(parsed)
        expected_route = {"V0": "deterministic_only", "V1": "sol", "V2": "claude-opus-5-5"}[profile]
        assert selected["route"] == expected_route
        assert selected["fallbackReviewer"] is None
        if profile == "V0":
            assert selected["reviewer"] == "none", "V0 must launch no reviewer"
    print("PASS V0-V2 routes select the enforced reviewer and V0 selects none")

    forged_v3 = metadata("V3")
    selected_forged_v3 = select_review_route(forged_v3)
    assert selected_forged_v3["specialistGateRequired"] is False
    assert selected_forged_v3["specialistGateSatisfied"] is True
    effective_v3 = metadata("V2", risk="high", verificationProfile="V2")
    selected_effective_v3 = select_review_route(effective_v3)
    assert selected_effective_v3["verificationProfile"] == "V2"
    assert selected_effective_v3["specialistGateRequired"] is False
    validate_order_routing(order_for(forged_v3))
    print("PASS legacy V3 is readable without a verifier; risk never automatically selects V3")

    for profile in ("V2", "V3"):
        claude_implementation = metadata(profile, executor="claude", model="claude-opus-5-5")
        expect_error(order_for(claude_implementation), "independent reviewer unavailable under current V2/V3 policy")
        same_model_alias = dict(claude_implementation, executor="other")
        expect_error(order_for(same_model_alias), "routing.executor must be codex or claude")
    expect_error(
        order_for(metadata("V2", executor="claudeFable", model="other")),
        "routing.model is not an allowed model",
    )
    print("PASS Claude-owned V2/V3 implementation cannot select its own Opus reviewer")

    sol_v0 = metadata("V0", complexity="high", model=SOL_PRIMARY_MODEL)
    validate_order_routing(order_for(sol_v0))
    print("PASS executor model identity alone does not force senior review")

    assert REVIEWER_FALLBACK_BY_PROFILE == {}
    for model in ("gpt-6-sol", "claude-opus-5", "claude-sonnet-4-6", "fable", "gemini-3.8-flash", "agy", "other"):
        expect_error(order_for(metadata("V0", model=model)), "routing.model is not an allowed model")
    for reviewer in ("gpt-6-sol", "claude-opus-5", "gemini-3.8-flash"):
        expect_error(order_for(metadata("V1", reviewer=reviewer)), "routing.reviewer is not a supported reviewer route")
    for executor in ("agy", "other", "claudeFable"):
        expect_error(order_for(metadata("V1", executor=executor)), "routing.executor must be codex or claude")
    expect_error(order_for(metadata("V0", model="claude-opus-5-5")), "codex routing.model")
    expect_error(order_for(metadata("V1", model=SOL_PRIMARY_MODEL)), "claude routing.model")
    print("PASS canonical adapter/model pairs reject removed models, reviewers, aliases, and fallbacks")

    claude_launch = order_for(metadata("V1"))
    for command in (
        "claude --model claude-opus-5-5 -p review",
        "claude --model=claude-opus-5-5 -p review",
    ):
        validate_order_routing(dict(claude_launch, launch={"command": command}))
    for command, expected in (
        ("claude --model claude-opus-5-5 --fallback-model claude-opus-5 -p review", "do not permit --fallback-model"),
        ("claude --model claude-opus-5-5 --fallback-model=claude-opus-5 -p review", "do not permit --fallback-model"),
        ("claude --model claude-opus-5 -p review", "select exactly the canonical routing.model"),
        ("claude --model claude-opus-5-5 --model claude-opus-5 -p review", "select exactly the canonical routing.model"),
        ("claude -p review", "select exactly the canonical routing.model"),
    ):
        expect_error(dict(claude_launch, launch={"command": command}), expected)
    print("PASS canonical Claude launcher selects Opus 5.5 without hidden legacy fallback or duplicate model flags")

    routine_luna = metadata(
        "V2", model="gpt-6-luna", complexity="low", risk="low", ambiguity="low", evidenceNeed="low",
        reasons=["escalation: independent review of Codex work"],
    )
    validate_order_routing(order_for(routine_luna))
    for effort in ("none", "low", "medium", "max"):
        expect_error(order_for(dict(routine_luna, reasoningEffort=effort)), "must be one of high, xhigh")
    for effort in ("high", "xhigh"):
        validate_order_routing(order_for(dict(routine_luna, reasoningEffort=effort)))
    high_evidence = dict(routine_luna, evidenceNeed="high")
    expect_error(order_for(dict(high_evidence, reasoningEffort="medium")), "must be one of high, xhigh")
    validate_order_routing(order_for(dict(high_evidence, reasoningEffort="high")))
    for task_class in ("exact_extraction", "mechanical_micro_edit"):
        validate_order_routing(order_for(metadata("V0", model="gpt-6-luna", taskClass=task_class, complexity="low", reasoningEffort="high")))
        validate_order_routing(order_for(metadata("V0", model=SOL_PRIMARY_MODEL, taskClass=task_class, complexity="low", reasoningEffort="low")))
    expect_error(order_for(metadata("V0", reasoningEffort="none")), "must be one of low, medium, high, xhigh, max")
    exact_high_evidence = metadata(
        "V0", model="gpt-6-luna", taskClass="exact_extraction", complexity="low",
        reasoningEffort="none", evidenceNeed="high",
    )
    expect_error(order_for(exact_high_evidence), "must be one of high, xhigh")
    validate_order_routing(order_for(dict(exact_high_evidence, reasoningEffort="high")))
    complex_work = metadata("V2", model=SOL_PRIMARY_MODEL, risk="low", ambiguity="low", complexity="high", evidenceNeed="low")
    expect_error(order_for(dict(complex_work, reasoningEffort="medium")), "requires at least high")
    validate_order_routing(order_for(dict(complex_work, reasoningEffort="high")))
    ambiguous_work = metadata("V2", model=SOL_PRIMARY_MODEL, risk="low", ambiguity="high", evidenceNeed="high")
    expect_error(order_for(dict(ambiguous_work, reasoningEffort="high")), "requires at least xhigh")
    validate_order_routing(order_for(dict(ambiguous_work, reasoningEffort="xhigh")))
    print("PASS model-specific effort sets enforce Luna high/xhigh and preserve Sol evidence floors")
    validate_order_routing(order_for(metadata("V1", executor="codex", model="gpt-6-luna", complexity="low")))
    expect_error(order_for(metadata("V2", model="gpt-6-luna", complexity="high")), f"requires {SOL_PRIMARY_MODEL}")
    expect_error(order_for(metadata("V2", model="gpt-6-luna")), f"requires {SOL_PRIMARY_MODEL}")
    expect_error(order_for(metadata("V2", model="gpt-6-luna", confidence="low")), f"requires {SOL_PRIMARY_MODEL}")
    sol_with_gap = metadata("V1", executor="codex", model=SOL_PRIMARY_MODEL, reasoningEffort="high")
    expect_error(order_for(sol_with_gap), "own independent reviewer")
    validate_order_routing(order_for(metadata("V2", model=SOL_PRIMARY_MODEL, risk="low", ambiguity="low", reasons=["Sol executor with a proof gap"])))
    old_routine = metadata("V1", executor="codex", model="gpt-5.6-terra")
    expect_error(order_for(old_routine), "routing.model is not an allowed model")
    for task in ("hard-debugging", "long_horizon"):
        route = metadata("V2", model="gpt-6-luna", complexity="low", risk="low", ambiguity="low", taskClass=task)
        expect_error(order_for(route), f"requires {SOL_PRIMARY_MODEL}")
    hard_debug = metadata("V2", model=SOL_PRIMARY_MODEL, risk="low", ambiguity="low", taskClass="hard_debugging")
    expect_error(order_for(dict(hard_debug, reasoningEffort="high")), "requires at least xhigh")
    validate_order_routing(order_for(dict(hard_debug, reasoningEffort="xhigh")))
    long_horizon = metadata("V2", model=SOL_PRIMARY_MODEL, risk="low", ambiguity="low", taskClass="long_horizon")
    expect_error(order_for(dict(long_horizon, reasoningEffort="medium")), "requires at least high")
    validate_order_routing(order_for(long_horizon))
    print("PASS existing model routes remain valid and a selected independent review rejects same-model authorship")

    post_claims = metadata("V0", model="gpt-6-luna", complexity="low")
    assert "deterministicFailureOracle" not in POST_EXECUTION_PREDICATES
    post_claims["trustPredicates"]["deterministicFailureOracle"] = False
    post_claims["trustPredicates"]["requiredArtifactsPass"] = False
    post_claims["trustPredicates"]["requiredProofsPass"] = False
    # These legacy fields are retained for wire compatibility, but their
    # executor assertions cannot grant or remove V0 admission. The controller
    # observes the real artifact/proof outcomes after dispatch.
    validate_order_routing(order_for(post_claims))
    no_proof = order_for(metadata("V0"))
    no_proof["proofCommands"] = []
    expect_error(no_proof, "requires at least one required proofCommand")
    optional_only = order_for(metadata("V0"))
    optional_only["proofCommands"][0]["required"] = False
    expect_error(optional_only, "requires at least one required proofCommand")
    print("PASS V0 separates pre-execution trust from controller-owned post-execution proof")
    medium_v1 = metadata("V1", risk="medium")
    validate_order_routing(order_for(medium_v1))
    irreversible_v1 = metadata("V1", reversibility="low")
    validate_order_routing(order_for(irreversible_v1))
    security_v0 = metadata("V0", taskClass="security_boundary")
    validate_order_routing(order_for(dict(security_v0, reasoningEffort="xhigh")))
    v3_no_gate = metadata("V3")
    v3_no_gate.pop("specialistGate")
    validate_order_routing(order_for(v3_no_gate))
    high_risk_v0 = metadata("V0", taskClass="production_change", risk="high", reasoningEffort="xhigh")
    high_risk_v0["trustPredicates"] = dict.fromkeys(TRUST, False)
    validate_order_routing(order_for(high_risk_v0))
    assert select_review_route(high_risk_v0)["verificationProfile"] == "V0"
    print("PASS owner-selected verification remains valid for high risk and truthful false trust predicates")

    for reason in ("no production changes", "no dependency changes", "no security impact", "production change", "architecture discussion"):
        safe = metadata("V0", reasons=[reason])
        assert minimum_profile(safe) == "V0"
        validate_order_routing(order_for(safe))
        dangerous = dict(safe, taskClass="production_change")
        assert minimum_profile(dangerous) == "V2"
        validate_order_routing(order_for(dangerous))
        assert minimum_profile(dict(safe, risk="high")) == "V2"
        assert minimum_profile(dict(safe, risk="medium")) == "V2"
    assert minimum_profile(metadata("V0", taskClass="product_title")) == "V0"
    print("PASS risk recommendations are independent of explanations and never veto the approved profile")

    terminal = metadata(
        "V1",
        executor="codex",
        executionProfile="terminal_review",
        reviewer="none",
        terminalGate=True,
        model=SOL_PRIMARY_MODEL,
        reasoningEffort="high",
    )
    validate_order_routing(order_for(terminal))
    recursive = dict(terminal)
    recursive["reviewer"] = SOL_PRIMARY_MODEL
    expect_error(order_for(recursive), "cannot select another reviewer")
    old_primary = dict(terminal, model="gpt-6-sol")
    expect_error(order_for(old_primary), "routing.model is not an allowed model")
    explicit_fallback = dict(terminal, model="gpt-6-sol", reasons=["fallback: verified provider unavailability"])
    expect_error(order_for(explicit_fallback), "routing.model is not an allowed model")
    primary_route = select_review_route(metadata("V1"))
    assert primary_route["reviewer"] == SOL_PRIMARY_MODEL
    assert primary_route["fallbackReviewer"] is None
    print("PASS gpt-6.1-sol is the only active Sol route and provider failure cannot authorize legacy fallback")
    medium_terminal = dict(terminal, risk="medium")
    validate_order_routing(order_for(medium_terminal))
    high_terminal = dict(terminal, risk="high")
    validate_order_routing(order_for(high_terminal))
    v3_terminal = metadata(
        "V3",
        executor="claude",
        executionProfile="terminal_review",
        reviewer="none",
        terminalGate=True,
        model="claude-opus-5-5",
    )
    v3_terminal_no_gate = dict(v3_terminal)
    v3_terminal_no_gate.pop("specialistGate")
    validate_order_routing(order_for(v3_terminal_no_gate))
    validate_order_routing(order_for(v3_terminal))
    v2_terminal = dict(v3_terminal, risk="medium", verificationProfile="V2")
    v2_terminal.pop("specialistGate")
    validate_order_routing(order_for(v2_terminal))
    recursive_v3 = dict(v3_terminal, reviewer="claude-opus-5-5")
    expect_error(order_for(recursive_v3), "cannot select another reviewer")
    print("PASS selected review semantics and no recursive reviewer remain independent of risk and retired V3 gates")

    advisory = metadata(
        "V2", executor="codex", model="gpt-6-astra", executionProfile="advisory",
        reviewer="none", reasoningEffort="high", taskClass="architecture_advisory",
        reasons=["astra advisory: material architecture ambiguity"],
    )
    validate_order_routing(order_for(advisory))
    validate_order_routing(order_for(dict(advisory, reasoningEffort="xhigh")))
    assert MODEL_REASONING_EFFORTS["gpt-6-astra"] == {"high", "xhigh"}
    selected_advisory = select_review_route(advisory)
    assert selected_advisory["route"] == "astra_advisory" and selected_advisory["reviewer"] == "none"
    assert selected_advisory["verificationProfile"] == "V2"
    for selected in ("V0", "V1", "V2", "V3"):
        chosen = dict(advisory, verificationProfile=selected)
        validate_order_routing(order_for(chosen))
        assert select_review_route(chosen)["verificationProfile"] == selected
    for bad, expected in (
        (dict(advisory, reasoningEffort="none"), "must be one of high, xhigh"),
        (dict(advisory, reasoningEffort="medium"), "must be one of high, xhigh"),
        (dict(advisory, reasoningEffort="max"), "must be one of high, xhigh"),
        (dict(advisory, reviewer="claude-opus-5-5"), "reviewer=none"),
        (dict(advisory, model="gpt-6-sol"), "routing.model is not an allowed model"),
        (dict(advisory, terminalGate=True), "cannot be a terminal review"),
        (dict(advisory, reasons=["routine work"]), "explicit architectural trigger"),
    ):
        expect_error(order_for(bad), expected)
    wrong_role = order_for(advisory)
    wrong_role["roleForTask"] = "CONSILIARIUS"
    expect_error(wrong_role, "roleForTask=ARCHITECTUS")
    expect_error(order_for(dict(advisory, executionProfile="implementation", reviewer="claude-opus-5-5")), "limited to the advisory")
    expect_error(order_for(dict(advisory, executionProfile="terminal_review", terminalGate=True)), "limited to the advisory")
    high_advisory = dict(advisory, risk="high", verificationProfile="V3", specialistGate={"required": True, "approved": True, "approver": "Boss"})
    expect_error(order_for(high_advisory), "requires at least xhigh")
    high_advisory["reasoningEffort"] = "xhigh"
    validate_order_routing(order_for(high_advisory))
    no_gate = dict(high_advisory)
    no_gate.pop("specialistGate")
    validate_order_routing(order_for(no_gate))
    print("PASS Astra advice preserves user-selected V0-V3 verification without impersonating review or implementation")

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
    promoted_codex = metadata("V0")
    selected_codex = select_review_route(promoted_codex, low_history)
    assert selected_codex["verificationProfile"] == "V0" and selected_codex["reviewer"] == "none"
    expect_error(
        order_for(
            dict(
                promoted_codex,
                verificationProfile="V1",
                reviewer=SOL_PRIMARY_MODEL,
                reasons=selected_codex["reasons"],
            )
        ),
        "own independent reviewer",
        low_history,
    )
    validate_order_routing(order_for(dict(promoted_codex, verificationProfile="V2", reviewer="claude-opus-5-5", reasons=selected_codex["reasons"])), low_history)
    low_history.extend(ledger_row(f"clean-after-{index}") for index in range(5))
    floor, _ = task_class_promotion(low_history, "routine_implementation")
    assert floor is None
    high_sol = [ledger_row("sol-high", reviewer="gpt-6-sol", failureClass="sol_miss", severity="high")]
    assert task_class_promotion(high_sol, "routine_implementation")[0] == "V2"
    legacy_sol = [ledger_row("old-sol-high", reviewer="gpt-5.6-sol", failureClass="sol_miss", severity="high")]
    assert task_class_promotion(legacy_sol, "routine_implementation")[0] == "V2"
    medium_sol = [
        ledger_row("sol-medium-1", reviewer="gpt-6-sol", failureClass="sol_miss", severity="medium"),
        ledger_row("sol-medium-2", reviewer="gpt-6-sol", failureClass="sol_miss", severity="medium"),
    ]
    assert task_class_promotion(medium_sol, "routine_implementation")[0] == "V2"
    promoted_v0 = metadata("V0")
    validate_order_routing(order_for(promoted_v0), medium_escape)
    selected_promotion = select_review_route(promoted_v0, medium_escape)
    assert selected_promotion["verificationProfile"] == "V0"
    assert selected_promotion["reviewer"] == "none"
    assert any(reason.startswith("promotion:") for reason in selected_promotion["reasons"])
    declared_promotion = dict(
        promoted_v0,
        verificationProfile="V2",
        reviewer="claude-opus-5-5",
        reasons=selected_promotion["reasons"],
    )
    validate_order_routing(order_for(declared_promotion), medium_escape)
    base_v2 = metadata("V2")
    ignored_promotion = select_review_route(base_v2, low_history[:3])
    assert ignored_promotion["verificationProfile"] == "V2"
    assert not any(reason.startswith("promotion:") for reason in ignored_promotion["reasons"])
    print("PASS escaped-defect history informs recommendations without overriding owner-selected review")

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
        assert "strict JSON" in str(exc)
    else:
        raise AssertionError("malformed ledger history must fail closed")
    base_ledger = json.dumps(ledger_row("strict-ledger"), separators=(",", ":"))
    strict_ledger_rows = {
        "duplicate-key": '{"orderId":"ambiguous",' + base_ledger[1:],
        "nan": base_ledger[:-1] + ',"ambiguous":NaN}',
        "infinity": base_ledger[:-1] + ',"ambiguous":Infinity}',
        "negative-infinity": base_ledger[:-1] + ',"ambiguous":-Infinity}',
        "overflow": base_ledger[:-1] + ',"ambiguous":1e999}',
    }
    for name, raw in strict_ledger_rows.items():
        strict_ledger = ROOT / f"strict-{name}.jsonl"
        strict_ledger.write_text(raw + "\n", encoding="utf-8")
        try:
            load_attempt_history(strict_ledger)
        except LedgerError as exc:
            assert "strict JSON" in str(exc)
        else:
            raise AssertionError(f"ledger must reject {name} JSON")
    for value in (float("nan"), float("inf"), float("-inf")):
        try:
            append_attempt(ROOT / "programmatic-non-finite.jsonl", ledger_row("programmatic", durationSeconds=value))
        except LedgerError as exc:
            assert "durationSeconds" in str(exc)
        else:
            raise AssertionError("ledger must reject programmatic non-finite numeric values")
    print("PASS ledger rejects duplicate keys, NaN, Infinity, -Infinity, 1e999, and programmatic non-finite values")
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
