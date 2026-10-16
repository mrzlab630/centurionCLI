#!/usr/bin/env python3
"""Offline regressions for the AQUILA_PROGRESS_DECISION_V1 detector."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from progress_drift_detector import DECISION_VERSION, evaluate_progress  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def mission() -> dict[str, Any]:
    return {
        "goal": "ship the parser safely",
        "paths": ["src/parser.py", "tests/test_parser.py"],
        "targets": ["parser"],
        "technologies": ["python"],
        "acceptance": ["parser-proof", "regression-proof"],
    }


def attempt(order_id: str, **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "orderId": order_id,
        "status": "failed",
        "controllerVerified": True,
        "blockerHash": "blocker-1",
        "findingHash": "finding-1",
        "patchHash": "patch-1",
        "resultHash": "result-1",
        "proofCoverage": [],
        "acceptanceCoverage": [],
    }
    value.update(overrides)
    return value


def main() -> int:
    base = mission()

    first = evaluate_progress(base, [])
    check(first["decisionVersion"] == DECISION_VERSION, "decision version")
    check(first["decision"] == "allow", "empty mission is allowed")
    check("empty_or_first_attempt" in first["reasonCodes"], "empty attempt reason")
    check(first["requiresOwnerDecision"] is False, "empty mission needs no owner decision")

    repeated_attempts = [attempt("order-a"), attempt("order-b")]
    repeated = evaluate_progress(base, repeated_attempts)
    check(repeated["decision"] == "escalate", "repeated signatures escalate")
    check("repeated_signatures" in repeated["reasonCodes"], "repeated signature reason")
    check(len(repeated["repeatedSignatures"]) >= 4, "blocker/finding/patch/result signatures are retained")
    check(repeated["progressSignals"][1]["orderIdChanged"] is True, "order rename is visible")
    check("no_progress" in repeated["reasonCodes"], "unchanged evidence is no progress")

    renamed_no_progress = evaluate_progress(base, [
        attempt("fresh-child-1", blockerHash="same-blocker", status="blocked"),
        attempt("fresh-child-2", blockerHash="same-blocker", status="blocked"),
    ])
    check(renamed_no_progress["decision"] == "escalate", "changed order IDs do not reset the loop")

    progressing = evaluate_progress(base, [
        attempt("progress-1", blockerHash="blocker-1", findingHash="finding-1", patchHash="patch-1", resultHash="result-1", status="done", proofCoverage=["proof-1"], acceptanceCoverage=["parser-proof"]),
        attempt("progress-2", blockerHash="blocker-2", findingHash="finding-2", patchHash="patch-2", resultHash="result-2", status="done", proofCoverage=["proof-1", "proof-2"], acceptanceCoverage=["parser-proof", "regression-proof"]),
    ])
    check(progressing["decision"] == "allow", "materially improved proof remains allowed")
    check("progress_observed" in progressing["reasonCodes"], "progress reason")
    check(progressing["progressSignals"][1]["newProofCount"] == 1, "new proof is measured")

    budget = evaluate_progress(base, [attempt("budget-1", durationSeconds=6, costUsd=3)], {"paths": base["paths"]}, {"maxAttempts": 1, "maxWallSeconds": 5, "maxCostUsd": 2})
    check(budget["decision"] == "escalate", "budget exhaustion escalates")
    check(set(budget["budgetState"]["exhausted"]) == {"attempt_budget_exhausted", "wall_budget_exhausted", "cost_budget_exhausted"}, "all budget dimensions are reported")

    drift = evaluate_progress(
        base,
        [attempt("drift-1", status="done", proofCoverage=["proof-1"], acceptanceCoverage=["parser-proof"])],
        {"paths": ["src/parser.py", "src/unapproved.py"], "targets": ["other-target"], "technologies": ["rust"], "acceptance": ["parser-proof"]},
    )
    check(drift["decision"] == "replan", "path/target/technology drift requires replan")
    check(drift["goalDrift"]["detected"] is True, "goal drift is detected")
    check(drift["goalDrift"]["beforeMutation"] is True, "drift is a pre-mutation signal")
    drift_kinds = {item["kind"] for item in drift["goalDrift"]["findings"]}
    check({"paths", "targets", "technologies"}.issubset(drift_kinds), "all scope drift dimensions are reported")

    goal_drift = evaluate_progress(base, [attempt("goal-drift-1", status="done")], {"goal": "different mission"})
    check(goal_drift["decision"] != "allow", "current-scope goal drift cannot allow")
    check(goal_drift["goalDrift"]["detected"] is True, "current-scope goal drift is detected")
    check(any(item["kind"] == "goal" for item in goal_drift["goalDrift"]["findings"]), "goal drift finding")

    secret_signature = evaluate_progress(base, [
        attempt("secret-1", blockerHash="token=first-secret"),
        attempt("secret-2", blockerHash="token=second-secret"),
    ])
    serialized_secret_signature = json.dumps(secret_signature)
    check("first-secret" not in serialized_secret_signature and "second-secret" not in serialized_secret_signature, "secret signatures are redacted")
    check("<redacted>" in serialized_secret_signature, "redacted signature remains countable")

    huge_budget = evaluate_progress(base, [attempt("huge-1", durationSeconds=1e308), attempt("huge-2", durationSeconds=1e308)])
    check(huge_budget["decision"] == "block", "budget arithmetic fails closed")
    check("budget_arithmetic" in huge_budget["reasonCodes"], "budget arithmetic reason")
    check("conflicting_evidence" in huge_budget["reasonCodes"], "budget arithmetic conflict reason")
    json.dumps(huge_budget, allow_nan=False)

    acceptance_regression = evaluate_progress(base, [
        attempt("acceptance-1", status="done", acceptanceCoverage=["parser-proof", "regression-proof"], proofCoverage=["proof-1"]),
        attempt("acceptance-2", status="done", acceptanceCoverage=["parser-proof"], proofCoverage=["proof-1", "proof-2"]),
    ])
    check(acceptance_regression["decision"] == "block", "acceptance reduction blocks")
    check("acceptance_coverage_regressed" in acceptance_regression["reasonCodes"], "acceptance regression reason")

    conflicting = evaluate_progress(base, [attempt("conflict-1", conflictingEvidence=True)])
    check(conflicting["decision"] == "block", "conflicting evidence fails closed")
    check(conflicting["requiresOwnerDecision"] is False, "evidence reconciliation is controller work")
    check("conflicting_evidence" in conflicting["reasonCodes"], "conflict reason")

    original_mission = copy.deepcopy(base)
    original_attempts = [attempt("immutable", proofCoverage=["proof-1"])]
    original_scope = copy.deepcopy(original_mission)
    original_attempt_bytes = copy.deepcopy(original_attempts)
    evaluate_progress(original_mission, original_attempts, original_scope, {"maxAttempts": 2})
    check(original_mission == original_scope, "mission input remains unchanged")
    check(original_attempts == original_attempt_bytes, "attempt input remains unchanged")

    narrowed = dict(base, paths=["src/parser.py"])
    check(evaluate_progress(base, [], narrowed)["decision"] == "allow", "path subset preserves goal/criteria")
    wildcard = dict(base, paths=["src/**"])
    check(evaluate_progress(wildcard, [], dict(base, paths=["src/parser.py"]))["decision"] == "allow", "trailing /** includes children")
    check(evaluate_progress(wildcard, [], dict(base, paths=["src/../outside.py"]))["decision"] != "allow", "path traversal rejected")
    check(evaluate_progress(base, [], dict(narrowed, acceptance=[]))["decision"] != "allow", "empty acceptance cannot erase criteria")
    check(evaluate_progress(base, [], dict(base, paths=[]))["decision"] != "allow", "empty paths cannot prove goal")
    with_proof = dict(base, requiredProof=[{"command": "verify parser"}])
    check(evaluate_progress(with_proof, [], dict(narrowed, requiredProof=[]))["decision"] != "allow", "required proof cannot be removed")
    after_success = evaluate_progress(base, [
        attempt("success", status="done", blockerHash="old", proofCoverage=["verified-result"], acceptanceCoverage=["parser-proof"]),
        attempt("blocked-1", blockerHash="new", proofCoverage=["verified-result"], acceptanceCoverage=["parser-proof"]),
        attempt("blocked-2", blockerHash="new", proofCoverage=["verified-result"], acceptanceCoverage=["parser-proof"]),
    ])
    check(after_success["decision"] == "escalate" and "no_progress" in after_success["reasonCodes"], "two blockers after success stop old strategy")
    check(after_success["requiresOwnerDecision"] is False, "one bounded strategy choice belongs to controller")
    report_hashes = evaluate_progress(base, [attempt("raw-1", controllerVerified=False, proofCoverage=["hash-a"]), attempt("raw-2", controllerVerified=False, proofCoverage=["hash-b"])])
    check("no_progress" in report_hashes["reasonCodes"], "unverified new hashes are not progress")

    forbidden_fields = {"permit", "stepPermit", "dispatch", "authorize", "authorization", "clear", "reset"}
    for result in (first, repeated, progressing, budget, drift, acceptance_regression, conflicting):
        check(forbidden_fields.isdisjoint(result), "advisory contains no permit/dispatch fields")
        json.dumps(result, allow_nan=False)

    print("PASS progress, no-progress, repeated signatures, and order-renaming regressions")
    print("PASS material progress, budgets, scope drift, acceptance regression, and conflicting evidence")
    print("PASS first-attempt behavior, immutable inputs, bounded JSON, and no permit/dispatch fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
