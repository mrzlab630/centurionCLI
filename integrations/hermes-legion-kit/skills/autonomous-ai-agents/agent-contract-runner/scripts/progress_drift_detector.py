#!/usr/bin/env python3
"""Deterministic, read-only progress and goal-drift advisory detector.

Public API
----------
``evaluate_progress(mission, attempts, current_scope=None, budgets=None)``

``mission`` is the controller-owned objective/scope object and ``attempts`` is
an ordered list of controller observations.  Hashes in observations are used
as supplied; this module never hashes payloads or infers authorship.  Scope
may contain ``goal``, ``paths``/``allowedPaths``, ``targets``,
``technologies``, and ``acceptance``.  Attempts may contain the same scope
fields plus proof/acceptance coverage and ``blockerHash``, ``findingHash``,
``patchHash``, ``resultHash`` (or their plural forms).

The return value is a bounded JSON-safe ``AQUILA_PROGRESS_DECISION_V1``
advisory.  It is diagnostic only: it cannot clear attempts, issue a permit,
authorize execution, dispatch an executor, or mutate its inputs.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterable, cast

DECISION_VERSION = "AQUILA_PROGRESS_DECISION_V1"
MAX_ITEMS = 32
MAX_STRING = 256
MAX_FINDINGS = 32
MAX_REASON_CODES = 32
SENSITIVE = (
    "password", "secret", "token", "api_key", "apikey", "authorization", "bearer",
    "cookie", "credential", "private_key",
)
MAX_BUDGET_VALUE = 1e308

_SCOPE_ALIASES = {
    "paths": ("paths", "allowedPaths", "changedPaths", "pathTargets"),
    "targets": ("targets", "target", "services", "components"),
    "technologies": ("technologies", "technology", "stacks", "tech"),
    "acceptance": ("acceptance", "acceptanceCriteria", "criteria"),
}
_HASH_FIELDS = {
    "blocker": ("blockerHash", "blockerHashes"),
    "finding": ("findingHash", "findingHashes"),
    "patch": ("patchHash", "patchHashes"),
    "result": ("resultHash", "resultHashes"),
    "signature": ("signature", "signatures", "failureSignature", "loopSignature"),
}


class ProgressDetectorError(ValueError):
    """Raised only by direct internal validation helpers; public evaluation is fail-closed."""


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _safe_string(value: Any, *, max_length: int = MAX_STRING) -> str | None:
    if not isinstance(value, str) or not value or len(value) > max_length:
        return None
    lowered = value.lower()
    if any(marker in lowered for marker in SENSITIVE):
        return "<redacted>"
    return value


def _safe_label(value: Any) -> str | None:
    return _safe_string(value, max_length=MAX_STRING)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
        if len(result) >= MAX_ITEMS:
            break
    return result


def _as_object(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _as_values(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if value is None:
        return []
    return [value]


def _scope_source(value: Any) -> dict[str, Any]:
    obj = _as_object(value) or {}
    nested = _as_object(obj.get("scope"))
    return nested if nested is not None else obj


def _scope_values(scope: Any, field: str) -> set[str]:
    obj = _scope_source(scope)
    values: list[Any] = []
    for alias in _SCOPE_ALIASES[field]:
        if alias in obj:
            values.extend(_as_values(obj.get(alias)))
            break
    normalized: list[str] = []
    for item in values:
        if isinstance(item, dict):
            item_value = item.get("id", item.get("criterionId", item.get("name", item.get("path"))))
            label = _safe_label(item_value)
        else:
            label = _safe_label(item)
        if label is not None:
            normalized.append(label)
    return set(normalized)


def _scope_goal(scope: Any) -> str | None:
    obj = _scope_source(scope)
    for key in ("goal", "objective", "objectiveId"):
        label = _safe_label(obj.get(key))
        if label is not None:
            return label
    return None


def _coverage(value: Any) -> tuple[set[str], float | None]:
    """Extract caller-declared coverage identifiers/ratio without hashing content."""
    if value is None:
        return set(), None
    if _is_number(value):
        ratio = float(value)
        if ratio > 1:
            ratio /= 100.0
        return set(), max(0.0, min(1.0, ratio))
    if isinstance(value, dict):
        ratio: float | None = None
        for key in ("ratio", "coverage", "percent", "percentage"):
            if _is_number(value.get(key)):
                ratio = float(value[key])
                if ratio > 1:
                    ratio /= 100.0
                ratio = max(0.0, min(1.0, ratio))
                break
        values: list[Any] = []
        for key in ("covered", "passed", "complete", "items", "criteria", "proofHashes", "hashes"):
            if key in value:
                values.extend(_as_values(value.get(key)))
        identifiers: list[str] = []
        for item in values:
            if isinstance(item, dict):
                item = item.get("id", item.get("criterionId", item.get("hash", item.get("sha256"))))
            label = _safe_label(item)
            if label is not None:
                identifiers.append(label)
        return set(identifiers), ratio
    identifiers = []
    for item in _as_values(value):
        if isinstance(item, dict):
            item = item.get("id", item.get("criterionId", item.get("hash", item.get("sha256"))))
        label = _safe_label(item)
        if label is not None:
            identifiers.append(label)
    return set(identifiers), None


def _attempt_coverage(attempt: dict[str, Any], kind: str) -> tuple[set[str], float | None]:
    keys = ("proofCoverage", "proof", "proofHashes") if kind == "proof" else (
        "acceptanceCoverage", "acceptance", "coveredAcceptance"
    )
    for key in keys:
        if key in attempt:
            return _coverage(attempt.get(key))
    return set(), None


def _hash_values(value: Any) -> list[str]:
    result: list[str] = []
    for item in _as_values(value):
        if isinstance(item, dict):
            item = item.get("hash", item.get("sha256", item.get("signature")))
        # Hashes/signatures are controller-supplied opaque identifiers.  Keep
        # their exact bytes (within the bound), except redact sensitive
        # markers; do not normalize, recompute, or treat them as proof of
        # authorship.
        safe_item = _safe_string(item)
        if safe_item is not None:
            result.append(safe_item)
    return _unique(result)


def _signatures(attempt: dict[str, Any], index: int) -> list[tuple[str, str, int]]:
    found: list[tuple[str, str, int]] = []
    for kind, fields in _HASH_FIELDS.items():
        for field in fields:
            if field in attempt:
                for value in _hash_values(attempt.get(field)):
                    found.append((kind, value, index))
                break
    # Nested caller-supplied signature buckets are accepted, but no payload is
    # serialized or hashed by this detector.
    bucket = attempt.get("signatures")
    if isinstance(bucket, dict):
        for raw_kind, raw_values in bucket.items():
            kind = _safe_label(raw_kind)
            if kind is None:
                continue
            for value in _hash_values(raw_values):
                found.append((kind, value, index))
    return found


def _explicit_conflict(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return False


def _attempt_conflict(attempt: dict[str, Any]) -> bool:
    for key in ("conflictingEvidence", "evidenceConflict", "conflicts", "conflicting"):
        if _explicit_conflict(attempt.get(key)):
            return True
    evidence = attempt.get("evidence")
    if isinstance(evidence, dict) and any(_explicit_conflict(evidence.get(key)) for key in ("conflict", "conflicting", "contradictory")):
        return True
    if attempt.get("proofFailed") is True and str(attempt.get("proofStatus", "")).lower() in {"pass", "passed", "success"}:
        return True
    if attempt.get("acceptanceFailed") is True and str(attempt.get("acceptanceStatus", "")).lower() in {"pass", "passed", "success"}:
        return True
    declared_classes = {
        _status_class(attempt.get(key))
        for key in ("status", "outcome", "proofStatus", "acceptanceStatus")
    } - {None}
    if len(declared_classes) > 1:
        return True
    evidence_classes: set[str] = set()
    evidence_items = evidence if isinstance(evidence, list) else [evidence]
    for item in evidence_items:
        if isinstance(item, dict):
            evidence_class = _status_class(item.get("status"))
            if evidence_class is not None:
                evidence_classes.add(evidence_class)
    if len(evidence_classes) > 1 or (declared_classes and evidence_classes and declared_classes != evidence_classes):
        return True
    return False


def _status_class(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.lower()
    if text in {"failed", "failure", "blocked", "error", "fail", "false"}:
        return "failure"
    if text in {"done", "completed", "success", "passed", "pass", "allow", "true"}:
        return "success"
    return None


def _outcome_class(attempt: dict[str, Any]) -> str | None:
    values = [attempt.get(key) for key in ("status", "outcome", "proofStatus", "acceptanceStatus")]
    text = " ".join(str(value).lower() for value in values if isinstance(value, str))
    if any(word in text.split() for word in ("failed", "failure", "blocked", "error", "fail")):
        return "failure"
    if any(word in text.split() for word in ("done", "completed", "success", "passed", "pass", "allow")):
        return "success"
    return None


def _budget_limit(budgets: dict[str, Any], names: tuple[str, ...]) -> float | int | None:
    for name in names:
        value = budgets.get(name)
        if _is_number(value) and value >= 0:
            return min(float(cast(float, value)), MAX_BUDGET_VALUE)
    return None


def _bounded_sum(values: Iterable[float]) -> tuple[float, bool]:
    total = 0.0
    arithmetic_error = False
    for value in values:
        bounded = min(value, MAX_BUDGET_VALUE)
        if bounded != value or total > MAX_BUDGET_VALUE - bounded:
            arithmetic_error = True
            total = MAX_BUDGET_VALUE
        else:
            total += bounded
    return total, arithmetic_error


def _budget_state(attempts: list[dict[str, Any]], supplied: Any, mission: dict[str, Any]) -> dict[str, Any]:
    budget_obj = _as_object(supplied)
    if budget_obj is None:
        budget_obj = _as_object(mission.get("budgets")) or {}
    max_attempts = _budget_limit(budget_obj, ("maxAttempts", "attemptBudget", "attempts"))
    max_wall = _budget_limit(budget_obj, ("maxWallSeconds", "wallTimeSeconds", "wallSeconds"))
    max_cost = _budget_limit(budget_obj, ("maxCostUsd", "costBudgetUsd", "costUsd"))
    durations = [
        float(a[key])
        for a in attempts
        for key in ("durationSeconds", "wallTimeSeconds", "wallSeconds")
        if _is_number(a.get(key)) and a[key] >= 0
    ]
    cumulative_wall = [float(a[key]) for a in attempts for key in ("elapsedWallSeconds", "totalWallSeconds", "cumulativeWallSeconds") if _is_number(a.get(key)) and a[key] >= 0]
    cumulative_cost = [float(a[key]) for a in attempts for key in ("cumulativeCostUsd", "totalCostUsd") if _is_number(a.get(key)) and a[key] >= 0]
    costs = [
        float(a[key])
        for a in attempts
        for key in ("costUsd", "cost")
        if _is_number(a.get(key)) and a[key] >= 0
    ]
    direct_wall = [
        float(budget_obj[key])
        for key in ("elapsedWallSeconds", "wallSecondsUsed", "spentWallSeconds")
        if _is_number(budget_obj.get(key)) and budget_obj[key] >= 0
    ]
    direct_cost = [
        float(budget_obj[key])
        for key in ("spentCostUsd", "costUsedUsd", "usedCostUsd")
        if _is_number(budget_obj.get(key)) and budget_obj[key] >= 0
    ]
    if direct_wall:
        cumulative_wall.append(max(direct_wall))
    if direct_cost:
        cumulative_cost.append(max(direct_cost))
    wall, wall_arithmetic_error = _bounded_sum(durations) if not cumulative_wall else (max(cumulative_wall), False)
    cost, cost_arithmetic_error = _bounded_sum(costs) if not cumulative_cost else (max(cumulative_cost), False)
    arithmetic_error = wall_arithmetic_error or cost_arithmetic_error
    exhausted: list[str] = []
    if max_attempts is not None and len(attempts) >= max_attempts:
        exhausted.append("attempt_budget_exhausted")
    if max_wall is not None and wall >= max_wall:
        exhausted.append("wall_budget_exhausted")
    if max_cost is not None and cost >= max_cost:
        exhausted.append("cost_budget_exhausted")
    return {
        "maxAttempts": max_attempts,
        "maxWallSeconds": max_wall,
        "maxCostUsd": max_cost,
        "observedAttempts": len(attempts),
        "observedWallSeconds": wall,
        "observedCostUsd": cost,
        "exhausted": exhausted,
        "arithmeticError": arithmetic_error,
    }


def _finding(kind: str, before: Iterable[str], after: Iterable[str], attempt_index: int | None = None) -> dict[str, Any]:
    before_list = _unique(sorted(before))
    after_list = _unique(sorted(after))
    item: dict[str, Any] = {
        "kind": kind,
        "added": _unique(sorted(set(after_list) - set(before_list))),
        "removed": _unique(sorted(set(before_list) - set(after_list))),
        "beforeMutation": True,
    }
    if attempt_index is not None:
        item["attemptIndex"] = attempt_index
    return item


def _decision_template(decision: str, reasons: list[str], repeated: list[dict[str, Any]], progress: list[dict[str, Any]], drift: dict[str, Any], budget: dict[str, Any], owner: bool) -> dict[str, Any]:
    return {
        "decisionVersion": DECISION_VERSION,
        "decision": decision,
        "reasonCodes": _unique(reasons)[:MAX_REASON_CODES],
        "repeatedSignatures": repeated[:MAX_ITEMS],
        "progressSignals": progress[:MAX_ITEMS],
        "goalDrift": drift,
        "budgetState": budget,
        "requiresOwnerDecision": bool(owner),
    }


def _paths_included(current: set[str], baseline: set[str]) -> bool:
    """Exact/trailing-** inclusion; fnmatch would let * cross directory bounds."""
    def rule(value: str) -> tuple[PurePosixPath, bool] | None:
        recursive = value.endswith("/**")
        base = value[:-3] if recursive else value
        path = PurePosixPath(base)
        if not base or ".." in path.parts or any(c in base for c in "*?["):
            return None
        return path, recursive
    approved = [rule(value) for value in baseline]
    for value in current:
        requested = rule(value)
        if requested is None:
            return False
        path, recursive = requested
        if not any(parent is not None and ((path == parent[0] and (parent[1] or not recursive)) or
                   (parent[1] and parent[0] in path.parents)) for parent in approved):
            return False
    return True


def evaluate_progress(
    mission: Any,
    attempts: Any,
    current_scope: Any = None,
    budgets: Any = None,
) -> dict[str, Any]:
    """Return a reproducible controller advisory without changing any input.

    Repeated caller-supplied signatures and no material proof/acceptance
    improvement escalate.  Scope additions/changes and acceptance regressions
    block before mutation.  Explicit or contradictory evidence blocks.  A
    first/empty attempt is allowed unless its own evidence is contradictory or
    its scope already drifts.  ``orderId`` is reported only as a change signal;
    it never resets history.
    """
    if not isinstance(mission, dict) or not isinstance(attempts, list) or any(not isinstance(item, dict) for item in attempts):
        return _decision_template(
            "block", ["invalid_input"], [], [], {"detected": False, "beforeMutation": True, "findings": []},
            {"maxAttempts": None, "maxWallSeconds": None, "maxCostUsd": None, "observedAttempts": 0, "observedWallSeconds": 0, "observedCostUsd": 0, "exhausted": [], "arithmeticError": False}, True,
        )
    attempt_list = list(attempts)
    mission_scope = _scope_source(mission.get("scope", mission))
    baseline_paths = _scope_values(mission_scope, "paths")
    baseline_targets = _scope_values(mission_scope, "targets")
    baseline_tech = _scope_values(mission_scope, "technologies")
    baseline_acceptance = _scope_values(mission_scope, "acceptance")
    findings: list[dict[str, Any]] = []
    reasons: list[str] = []
    explicit_conflict = _explicit_conflict(mission.get("conflictingEvidence"))
    for index, attempt in enumerate(attempt_list):
        if _attempt_conflict(attempt):
            explicit_conflict = True
        attempt_scope = _scope_source(attempt.get("scope", attempt))
        for field, baseline, code in (
            ("paths", baseline_paths, "goal_drift_paths"),
            ("targets", baseline_targets, "goal_drift_targets"),
            ("technologies", baseline_tech, "goal_drift_technologies"),
        ):
            current = _scope_values(attempt_scope, field)
            if baseline and current and (not _paths_included(current, baseline) if field == "paths" else current != baseline):
                findings.append(_finding(field, baseline, current, index))
                reasons.append(code)
        current_goal = _scope_goal(attempt_scope)
        baseline_goal = _scope_goal(mission_scope)
        if baseline_goal and current_goal and baseline_goal != current_goal:
            findings.append({"kind": "goal", "before": baseline_goal, "after": current_goal, "added": [], "removed": [], "attemptIndex": index, "beforeMutation": True})
            reasons.append("goal_drift_goal")
    if explicit_conflict:
        reasons.append("conflicting_evidence")

    selected_scope = _scope_source(current_scope) if current_scope is not None else (_scope_source(attempt_list[-1].get("scope", attempt_list[-1])) if attempt_list else mission_scope)
    for field, baseline, code in (
        ("paths", baseline_paths, "goal_drift_paths"),
        ("targets", baseline_targets, "goal_drift_targets"),
        ("technologies", baseline_tech, "goal_drift_technologies"),
    ):
        current = _scope_values(selected_scope, field)
        if baseline and current and (not _paths_included(current, baseline) if field == "paths" else current != baseline) and not any(f.get("kind") == field and f.get("attemptIndex") is None for f in findings):
            findings.append(_finding(field, baseline, current))
            reasons.append(code)
    current_acceptance = _scope_values(selected_scope, "acceptance")
    acceptance_supplied = any(key in selected_scope for key in _SCOPE_ALIASES["acceptance"])
    if baseline_acceptance and acceptance_supplied and baseline_acceptance != current_acceptance:
        findings.append(_finding("acceptance", baseline_acceptance, current_acceptance))
        reasons.append("acceptance_coverage_regressed")
    baseline_proof = mission_scope.get("requiredProof", mission_scope.get("proofCommands"))
    selected_proof = selected_scope.get("requiredProof", selected_scope.get("proofCommands", baseline_proof))
    if baseline_proof is not None and selected_proof != baseline_proof:
        findings.append({"kind": "proof", "beforeMutation": True})
        reasons.append("required_proof_changed")
    if any(key in selected_scope for key in _SCOPE_ALIASES["paths"]) and not _scope_values(selected_scope, "paths"):
        findings.append({"kind": "paths", "beforeMutation": True})
        reasons.append("empty_paths_do_not_prove_goal")
    current_goal = _scope_goal(selected_scope)
    baseline_goal = _scope_goal(mission_scope)
    if baseline_goal and current_goal and baseline_goal != current_goal and not any(
        finding.get("kind") == "goal" and finding.get("attemptIndex") is None for finding in findings
    ):
        findings.append({"kind": "goal", "before": baseline_goal, "after": current_goal, "added": [], "removed": [], "beforeMutation": True})
        reasons.append("goal_drift_goal")

    signature_rows: dict[tuple[str, str], set[int]] = {}
    outcomes: dict[tuple[str, str], set[str]] = {}
    for index, attempt in enumerate(attempt_list):
        outcome = _outcome_class(attempt)
        for kind, value, attempt_index in _signatures(attempt, index):
            key = (kind, value)
            signature_rows.setdefault(key, set()).add(attempt_index)
            if outcome:
                outcomes.setdefault(key, set()).add(outcome)
    repeated: list[dict[str, Any]] = []
    signature_conflict = False
    for (kind, value), indexes in sorted(signature_rows.items()):
        if len(indexes) >= 2:
            repeated.append({"kind": kind, "hash": value, "count": len(indexes), "attemptIndexes": sorted(indexes)[:MAX_ITEMS]})
            reasons.append("repeated_signatures")
            # A previously successful product can later hit a blocker with
            # the same patch/report. Outcome labels do not contradict bytes.
    if signature_conflict:
        reasons.append("conflicting_evidence")

    progress_signals: list[dict[str, Any]] = []
    seen_proofs: set[str] = set()
    seen_acceptance: set[str] = set()
    previous_order: str | None = None
    material_progress = False
    coverage_regressed = False
    prior_acceptance_count = 0
    prior_acceptance_ratio: float | None = None
    for index, attempt in enumerate(attempt_list):
        proofs, proof_ratio = _attempt_coverage(attempt, "proof")
        acceptance, acceptance_ratio = _attempt_coverage(attempt, "acceptance")
        new_proofs = proofs - seen_proofs
        new_acceptance = acceptance - seen_acceptance
        # Inputs are controller observations; raw report/result/patch hashes
        # alone are not proof of progress.
        material = bool(new_proofs or new_acceptance) and attempt.get("controllerVerified") is True
        if proof_ratio is not None and (not progress_signals or proof_ratio > max((signal.get("proofCoverageRatio") or 0) for signal in progress_signals)):
            material = material or (attempt.get("controllerVerified") is True and (not progress_signals or proof_ratio - max((signal.get("proofCoverageRatio") or 0) for signal in progress_signals) >= 0.05))
        if acceptance_ratio is not None and (not progress_signals or acceptance_ratio > max((signal.get("acceptanceCoverageRatio") or 0) for signal in progress_signals)):
            material = material or (attempt.get("controllerVerified") is True and (not progress_signals or acceptance_ratio - max((signal.get("acceptanceCoverageRatio") or 0) for signal in progress_signals) >= 0.05))
        if acceptance and len(acceptance) < prior_acceptance_count:
            coverage_regressed = True
        if acceptance_ratio is not None and prior_acceptance_ratio is not None and acceptance_ratio < prior_acceptance_ratio:
            coverage_regressed = True
        signal = {
            "attemptIndex": index,
            "orderIdChanged": previous_order is not None and attempt.get("orderId") != previous_order,
            "newProofCount": len(new_proofs),
            "newAcceptanceCount": len(new_acceptance),
            "proofCoverageCount": len(proofs),
            "acceptanceCoverageCount": len(acceptance),
            "proofCoverageRatio": proof_ratio,
            "acceptanceCoverageRatio": acceptance_ratio,
            "material": bool(material),
        }
        progress_signals.append(signal)
        material_progress = material_progress or material
        if attempt.get("controllerVerified") is True:
            seen_proofs.update(proofs)
            seen_acceptance.update(acceptance)
        prior_acceptance_count = max(prior_acceptance_count, len(acceptance))
        if acceptance_ratio is not None:
            prior_acceptance_ratio = max(prior_acceptance_ratio or 0.0, acceptance_ratio)
        previous_order = attempt.get("orderId") if isinstance(attempt.get("orderId"), str) else previous_order
    if coverage_regressed:
        reasons.append("acceptance_coverage_regressed")
    budget_state = _budget_state(attempt_list, budgets, mission)
    reasons.extend(budget_state["exhausted"])
    if budget_state["arithmeticError"]:
        reasons.extend(["budget_arithmetic", "conflicting_evidence"])
        explicit_conflict = True
    tail_no_progress = len(progress_signals) >= 2 and not any(signal["material"] for signal in progress_signals[-2:])
    consecutive_blocker = len(attempt_list) >= 2 and bool(attempt_list[-1].get("blockerHash")) and attempt_list[-1].get("blockerHash") == attempt_list[-2].get("blockerHash") and tail_no_progress
    if tail_no_progress:
        reasons.append("no_progress")
    if not attempt_list:
        reasons.append("empty_or_first_attempt")
    elif len(attempt_list) == 1 and not material_progress:
        reasons.append("empty_or_first_attempt")
    elif material_progress:
        reasons.append("progress_observed")

    reasons = _unique(reasons)
    drift = {"detected": bool(findings), "beforeMutation": True, "findings": findings[:MAX_FINDINGS]}
    if explicit_conflict or signature_conflict:
        decision, owner = "block", False
    elif coverage_regressed:
        decision, owner = "block", False
    elif findings:
        # Scope drift is recoverable only through a fresh controller/owner
        # decision; it must not authorize the currently observed mutation.
        decision, owner = "replan", True
    elif budget_state["exhausted"] or consecutive_blocker or tail_no_progress:
        decision, owner = "escalate", bool(budget_state["exhausted"])
    else:
        decision, owner = "allow", False
    result = _decision_template(decision, reasons, repeated, progress_signals, drift, budget_state, owner)
    # Ensure the public artifact is JSON-safe even if a future field is added.
    json.dumps(result, allow_nan=False, separators=(",", ":"))
    return result


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission", required=True, type=Path)
    parser.add_argument("--attempts", required=True, type=Path)
    parser.add_argument("--current-scope", type=Path)
    parser.add_argument("--budgets", type=Path)
    args = parser.parse_args(argv)
    try:
        mission = json.loads(args.mission.read_text(encoding="utf-8"))
        attempts = json.loads(args.attempts.read_text(encoding="utf-8"))
        current = json.loads(args.current_scope.read_text(encoding="utf-8")) if args.current_scope else None
        budget = json.loads(args.budgets.read_text(encoding="utf-8")) if args.budgets else None
        print(json.dumps(evaluate_progress(mission, attempts, current, budget), sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"progress detector rejected input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
