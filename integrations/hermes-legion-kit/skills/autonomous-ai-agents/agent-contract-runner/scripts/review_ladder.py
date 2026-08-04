#!/usr/bin/env python3
"""Deterministic Aquila V0-V3 routing and post-cutover order validation."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

from strict_json import StrictJSONError, strict_json_loads


ROUTING_PREFIX = "AQUILA_ROUTING_JSON_V1:"
CUTOVER_AT = datetime(2026, 8, 3, 11, 0, 42, tzinfo=timezone.utc)
PROFILES = ("V0", "V1", "V2", "V3")
PROFILE_RANK = {profile: index for index, profile in enumerate(PROFILES)}
REVIEWER_BY_PROFILE = {
    "V0": "none",
    "V1": "gpt-5.6-sol",
    "V2": "claude-opus-5",
    "V3": "claude-opus-5",
}
ALLOWED_MODELS = {
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
    "claude-opus-5",
    "agy",
    "hermes-delegate-task",
    "other",
}
ALLOWED_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}
LEVELS = {"low", "medium", "high"}
TRUST_PREDICATES = (
    "localNarrowBlastRadius",
    "cheapReversal",
    "deterministicFailureOracle",
    "noSensitiveOrExternalSideEffects",
    "requiredArtifactsPass",
    "requiredProofsPass",
    "noUncertainty",
    "noScopeOrAssumptionIssues",
)
REQUIRED_ROUTING_FIELDS = {
    "objectiveId",
    "attempt",
    "taskClass",
    "complexity",
    "risk",
    "ambiguity",
    "reversibility",
    "evidenceNeed",
    "executor",
    "model",
    "reasoningEffort",
    "executionProfile",
    "verificationProfile",
    "reviewer",
    "confidence",
    "reasons",
}
OPTIONAL_ROUTING_FIELDS = {"trustPredicates", "specialistGate", "terminalGate"}
HARD_RISK_MARKERS = {
    "security",
    "auth",
    "authentication",
    "secret",
    "secrets",
    "payment",
    "payments",
    "money",
    "wallet",
    "kyc",
    "data loss",
    "data_loss",
    "migration",
    "production",
    "dependency",
    "supply chain",
    "supply_chain",
    "public endpoint",
    "public_endpoint",
    "infrastructure",
    "infra",
}
V2_MARKERS = {
    "shared contract",
    "shared_contract",
    "api contract",
    "api_contract",
    "architecture",
    "difficult diagnosis",
    "difficult_diagnosis",
    "cross service",
    "cross_service",
    "data model",
    "data_model",
    "data decision",
    "data_decision",
    "shared schema",
    "shared_schema",
    "schema change",
    "schema_change",
    "hidden failure",
    "hidden_failure",
    "verification control plane",
    "verification_control_plane",
}


class RoutingError(ValueError):
    """Raised when routing metadata or a routing decision is invalid."""


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RoutingError("createdAt must be a non-empty ISO-8601 timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RoutingError("createdAt must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise RoutingError("createdAt must include a timezone")
    return parsed.astimezone(timezone.utc)


def _normalized_decision_text(metadata: dict[str, Any]) -> str:
    reasons = metadata.get("reasons", [])
    values = [metadata.get("taskClass", ""), *[reason for reason in reasons if isinstance(reason, str)]]
    return " ".join(values).casefold()


def _contains_marker(text: str, markers: Iterable[str]) -> bool:
    normalized = re.sub(r"[-/]+", " ", text)
    return any(marker in text or marker.replace("_", " ") in normalized for marker in markers)


def _all_trust_predicates(metadata: dict[str, Any]) -> bool:
    predicates = metadata.get("trustPredicates")
    return (
        isinstance(predicates, dict)
        and set(predicates) == set(TRUST_PREDICATES)
        and all(predicates.get(key) is True for key in TRUST_PREDICATES)
    )


def minimum_profile(metadata: dict[str, Any]) -> str:
    """Return the non-negotiable verification floor for an implementation decision."""
    decision_text = _normalized_decision_text(metadata)
    if metadata.get("risk") == "high" or _contains_marker(decision_text, HARD_RISK_MARKERS):
        return "V3"
    if (
        metadata.get("risk") == "medium"
        or metadata.get("ambiguity") in {"medium", "high"}
        or metadata.get("reversibility") != "high"
        or _contains_marker(decision_text, V2_MARKERS)
    ):
        return "V2"
    if metadata.get("risk") == "low" and _all_trust_predicates(metadata):
        return "V0"
    return "V1"


def _severity(row: dict[str, Any]) -> str:
    value = row.get("severity")
    if isinstance(value, str):
        return value.casefold()
    failure_class = str(row.get("failureClass", "")).casefold()
    for candidate in ("high", "medium", "low"):
        if failure_class.endswith(f":{candidate}") or failure_class.endswith(f"_{candidate}"):
            return candidate
    return ""


def task_class_promotion(history: Iterable[dict[str, Any]], task_class: str) -> tuple[str | None, list[str]]:
    """Return an active task-class floor from escaped V0 defects or Sol misses."""
    rows = [row for row in history if row.get("taskClass") == task_class]
    reasons: list[str] = []

    for row in rows:
        if str(row.get("failureClass", "")).casefold().startswith("escaped_defect") and _severity(row) in {"medium", "high"}:
            reasons.append("promotion: medium/high escaped V0 defect promotes task class to V2")
            return "V2", reasons

    completed = [row for row in rows if row.get("status") == "done"]
    recent_ten = completed[-10:]
    low_positions = [
        index
        for index, row in enumerate(recent_ten)
        if str(row.get("failureClass", "")).casefold().startswith("escaped_defect") and _severity(row) == "low"
    ]
    if len(low_positions) >= 2:
        trigger_position = low_positions[-1]
        completed_after_trigger = len(recent_ten) - trigger_position - 1
        if completed_after_trigger < 5:
            reasons.append("promotion: two low escaped V0 defects in ten objectives activate a five-objective promotion")
            return "V1", reasons

    sol_rows = [
        row
        for row in rows
        if row.get("reviewer") in {"gpt-5.6-sol", "sol"} and row.get("status") == "done"
    ]
    for row in sol_rows:
        if str(row.get("failureClass", "")).casefold().startswith("sol_miss") and _severity(row) == "high":
            reasons.append("promotion: one high Sol miss promotes task class to Claude")
            return "V2", reasons
    if len(sol_rows) >= 2 and all(
        str(row.get("failureClass", "")).casefold().startswith("sol_miss") and _severity(row) == "medium"
        for row in sol_rows[-2:]
    ):
        reasons.append("promotion: two consecutive medium Sol misses promote task class to Claude")
        return "V2", reasons
    return None, reasons


def select_review_route(metadata: dict[str, Any], history: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    """Select V0-V3 and the terminal reviewer without launching any process."""
    profile = minimum_profile(metadata)
    reasons = [f"base routing floor {profile}"]
    promotion, promotion_reasons = task_class_promotion(history, str(metadata.get("taskClass", "")))
    if promotion is not None and PROFILE_RANK[promotion] > PROFILE_RANK[profile]:
        profile = promotion
        reasons.extend(promotion_reasons)
    reviewer = REVIEWER_BY_PROFILE[profile]
    gate = metadata.get("specialistGate") if profile == "V3" else None
    gate_satisfied = profile != "V3" or (
        isinstance(gate, dict)
        and gate.get("required") is True
        and gate.get("approved") is True
        and isinstance(gate.get("approver"), str)
        and bool(gate["approver"].strip())
    )
    return {
        "verificationProfile": profile,
        "route": "deterministic_only" if profile == "V0" else ("sol" if profile == "V1" else "claude-opus-5"),
        "reviewer": reviewer,
        "specialistGateRequired": profile == "V3",
        "specialistGateSatisfied": gate_satisfied,
        "reasons": reasons,
    }


def _require_string(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RoutingError(f"routing.{key} must be a non-empty string")
    return value


def validate_routing_metadata(
    metadata: dict[str, Any],
    order: dict[str, Any],
    history: Iterable[dict[str, Any]] = (),
) -> None:
    missing = sorted(REQUIRED_ROUTING_FIELDS - set(metadata))
    unknown = sorted(set(metadata) - REQUIRED_ROUTING_FIELDS - OPTIONAL_ROUTING_FIELDS)
    if missing:
        raise RoutingError("routing metadata missing fields: " + ", ".join(missing))
    if unknown:
        raise RoutingError("routing metadata contains unknown fields: " + ", ".join(unknown))

    for key in (
        "objectiveId",
        "taskClass",
        "executor",
        "model",
        "reasoningEffort",
        "executionProfile",
        "verificationProfile",
        "reviewer",
        "confidence",
    ):
        _require_string(metadata, key)
    attempt = metadata.get("attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise RoutingError("routing.attempt must be a positive integer")
    for key in ("complexity", "risk", "ambiguity", "reversibility", "evidenceNeed", "confidence"):
        if metadata.get(key) not in LEVELS:
            raise RoutingError(f"routing.{key} must be low, medium, or high")
    if metadata["model"] not in ALLOWED_MODELS:
        raise RoutingError("routing.model is not an allowed model")
    if metadata["reasoningEffort"] not in ALLOWED_REASONING_EFFORTS:
        raise RoutingError("routing.reasoningEffort is not supported")
    if metadata["verificationProfile"] not in PROFILES:
        raise RoutingError("routing.verificationProfile must be V0, V1, V2, or V3")
    if metadata["reviewer"] not in {"none", "gpt-5.6-sol", "claude-opus-5"}:
        raise RoutingError("routing.reviewer is not a supported reviewer route")
    reasons = metadata.get("reasons")
    if not isinstance(reasons, list) or not reasons or not all(isinstance(item, str) and item.strip() for item in reasons):
        raise RoutingError("routing.reasons must be a non-empty string array")
    if metadata["executor"] != order.get("executor"):
        raise RoutingError("routing.executor must match order.executor")
    if metadata["risk"] != order.get("riskLevel"):
        raise RoutingError("routing.risk must match order.riskLevel")

    executor = metadata["executor"]
    model = metadata["model"]
    if executor == "codex" and model not in {"gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
        raise RoutingError("codex routing.model must be a supported GPT-5.6 model")
    if executor == "claude" and model != "claude-opus-5":
        raise RoutingError("claude routing.model must be claude-opus-5")
    if executor == "agy" and model != "agy":
        raise RoutingError("agy routing.model must be agy")

    execution_profile = metadata["executionProfile"]
    profile = metadata["verificationProfile"]
    base_floor = minimum_profile(metadata)
    promotion, _ = task_class_promotion(history, metadata["taskClass"])
    floor = base_floor
    if promotion is not None and PROFILE_RANK[promotion] > PROFILE_RANK[floor]:
        floor = promotion
    if PROFILE_RANK[profile] < PROFILE_RANK[floor]:
        raise RoutingError(f"routing profile {profile} violates hard floor {floor}")

    if execution_profile == "terminal_review":
        if metadata.get("terminalGate") is not True:
            raise RoutingError("terminal review orders require terminalGate=true")
        if profile == "V0":
            raise RoutingError("V0 has no reviewer order")
        if metadata["reviewer"] != "none":
            raise RoutingError("terminal review orders cannot select another reviewer")
        expected_model = "gpt-5.6-sol" if profile == "V1" else "claude-opus-5"
        if model != expected_model:
            raise RoutingError(f"{profile} terminal review must run {expected_model}")
    elif execution_profile == "implementation":
        if PROFILE_RANK[profile] > PROFILE_RANK[base_floor] and not any(
            reason.casefold().startswith(("promotion:", "escalation:")) for reason in reasons
        ):
            raise RoutingError("routing above the deterministic floor requires a promotion: or escalation: reason")
        expected_reviewer = REVIEWER_BY_PROFILE[profile]
        if metadata["reviewer"] != expected_reviewer:
            raise RoutingError(f"{profile} requires reviewer {expected_reviewer}")
    else:
        raise RoutingError("routing.executionProfile must be implementation or terminal_review")

    if profile == "V0" and not _all_trust_predicates(metadata):
        raise RoutingError("V0 requires every canonical trust predicate to be true")
    if profile == "V3":
        gate = metadata.get("specialistGate")
        if not isinstance(gate, dict) or set(gate) != {"required", "approved", "approver"}:
            raise RoutingError("V3 requires explicit specialistGate required/approved/approver fields")
        if gate.get("required") is not True or gate.get("approved") is not True:
            raise RoutingError("V3 specialist/Boss gate is not approved")
        if not isinstance(gate.get("approver"), str) or not gate["approver"].strip():
            raise RoutingError("V3 specialistGate.approver must be non-empty")


def parse_routing_entry(entry: str) -> dict[str, Any]:
    payload_text = entry[len(ROUTING_PREFIX) :]
    if not payload_text:
        raise RoutingError("routing metadata payload is empty")
    try:
        payload = strict_json_loads(payload_text, "routing metadata")
    except StrictJSONError as exc:
        raise RoutingError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise RoutingError("routing metadata must be a JSON object")
    canonical = ROUTING_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if entry != canonical:
        raise RoutingError("routing metadata must be compact canonical JSON")
    return payload


def validate_order_routing(
    order: dict[str, Any],
    history: Iterable[dict[str, Any]] = (),
) -> dict[str, Any] | None:
    """Validate the cutover boundary and return parsed metadata for new orders."""
    created_at = _parse_timestamp(order.get("createdAt"))
    if created_at < CUTOVER_AT:
        return None
    notes = order.get("notesForExecutor")
    if not isinstance(notes, list):
        raise RoutingError("notesForExecutor must be an array")
    entries = [item for item in notes if isinstance(item, str) and item.startswith(ROUTING_PREFIX)]
    if len(entries) != 1:
        raise RoutingError("post-cutover orders require exactly one AQUILA_ROUTING_JSON_V1 entry")
    metadata = parse_routing_entry(entries[0])
    validate_routing_metadata(metadata, order, history)
    return metadata
