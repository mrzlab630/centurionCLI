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
    "V1": "gpt-6-sol",
    "V2": "claude-opus-5",
    "V3": "claude-opus-5",
}
ALLOWED_MODELS = {
    "gpt-6-luna",
    "gpt-6-sol",
    "gpt-6-astra",
    "gemini-3.8-flash",
    "claude-opus-5",
    "agy",
    "hermes-delegate-task",
    "other",
}
GEMINI_CREATIVE_ROLES = {
    "AEDILIS",
    "PICTOR",
    "NOMENCLATOR",
    "GLOSSATOR",
    "LUDIFEX",
    "ORATOR",
    "MERCATOR",
    "SCRIBA",
    "TABULARIUS",
    "INTERPRES",
}
ALLOWED_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}
ASTRA_ADVISORY_TRIGGERS = {
    "astra advisory: explicit user request",
    "astra advisory: material architecture ambiguity",
    "astra advisory: cross-system tradeoffs",
    "astra advisory: difficult diagnosis",
}
V3_APPROVAL_UNAVAILABLE = "V3 requires independently verified approval evidence; no trusted verification source configured"
EFFORT_RANK = {effort: rank for rank, effort in enumerate(("none", "low", "medium", "high", "xhigh", "max"))}
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
# Keep the legacy wire shape, but do not use executor assertions about future
# proof outcomes to admit a V0 route. Those outcomes are controller-owned and
# are evaluated after execution by the artifact/proof verification gate.
PRE_EXECUTION_PREDICATES = (
    "localNarrowBlastRadius",
    "cheapReversal",
    "noSensitiveOrExternalSideEffects",
    "noUncertainty",
    "noScopeOrAssumptionIssues",
)
POST_EXECUTION_PREDICATES = (
    "requiredArtifactsPass",
    "requiredProofsPass",
)
# deterministicFailureOracle remains a legacy semantic claim, not an observed
# admission/postcondition. Actual required commands supply pass/fail evidence.
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
    "hard debugging",
    "hard_debugging",
    "long horizon",
    "long_horizon",
    "consequential",
}
XHIGH_EFFORT_MARKERS = {"hard debugging", "hard_debugging", "security", "architecture", "cross service", "cross_service"}
HIGH_EFFORT_MARKERS = {"long horizon", "long_horizon", "consequential", "non trivial", "non_trivial"}
EXACT_WORK_MARKERS = {"exact extraction", "exact_extraction", "exact classification", "exact_classification", "format conversion", "format_conversion", "format transformation", "format_transformation"}
MECHANICAL_WORK_MARKERS = EXACT_WORK_MARKERS | {"mechanical", "micro edit", "micro_edit", "simple retrieval", "simple_retrieval"}


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


def _trust_predicates_have_legacy_shape(metadata: dict[str, Any]) -> bool:
    predicates = metadata.get("trustPredicates")
    return (
        isinstance(predicates, dict)
        and set(predicates) == set(TRUST_PREDICATES)
        and all(isinstance(predicates.get(key), bool) for key in TRUST_PREDICATES)
    )


def _all_pre_execution_predicates(metadata: dict[str, Any]) -> bool:
    """Return whether controller-independent V0 safety predicates hold."""
    predicates = metadata.get("trustPredicates")
    return _trust_predicates_have_legacy_shape(metadata) and all(
        predicates.get(key) is True for key in PRE_EXECUTION_PREDICATES
    )


def _requires_sol(metadata: dict[str, Any]) -> bool:
    return (
        metadata["complexity"] == "high"
        or metadata["risk"] != "low"
        or metadata["ambiguity"] != "low"
        or metadata["reversibility"] != "high"
        or metadata["confidence"] != "high"
        or _contains_marker(_normalized_decision_text(metadata), HARD_RISK_MARKERS | V2_MARKERS)
    )


def _minimum_codex_effort(metadata: dict[str, Any]) -> str:
    decision_text = _normalized_decision_text(metadata)
    if metadata["ambiguity"] == "high" or _contains_marker(decision_text, XHIGH_EFFORT_MARKERS):
        return "xhigh"
    if (
        metadata["executionProfile"] == "terminal_review"
        or metadata["complexity"] == "high"
        or metadata["risk"] != "low"
        or metadata["ambiguity"] != "low"
        or metadata["reversibility"] != "high"
        or metadata["evidenceNeed"] == "high"
        or _contains_marker(decision_text, HIGH_EFFORT_MARKERS)
    ):
        return "high"
    if metadata["complexity"] == "low" and _contains_marker(decision_text, EXACT_WORK_MARKERS) and _all_pre_execution_predicates(metadata):
        return "none"
    if metadata["complexity"] == "low" and _contains_marker(decision_text, MECHANICAL_WORK_MARKERS):
        return "low"
    return "medium"


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
    if metadata.get("risk") == "low" and _all_pre_execution_predicates(metadata):
        return "V0"
    if metadata.get("executor") == "codex" and metadata.get("executionProfile") == "implementation":
        return "V2"
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
        if row.get("reviewer") in {"gpt-6-sol", "gpt-5.6-sol", "sol"} and row.get("status") == "done"
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
    profile, reasons = _effective_profile(metadata, history)
    advisory = metadata.get("executionProfile") == "advisory"
    terminal = metadata.get("executionProfile") == "terminal_review"
    reviewer = "none" if advisory or terminal else REVIEWER_BY_PROFILE[profile]
    gate_satisfied = profile != "V3"
    return {
        "verificationProfile": profile,
        "route": "astra_advisory" if advisory else ("terminal_closure" if terminal else ("deterministic_only" if profile == "V0" else ("sol" if profile == "V1" else "claude-opus-5"))),
        "reviewer": reviewer,
        "specialistGateRequired": profile == "V3",
        "specialistGateSatisfied": gate_satisfied,
        "reasons": reasons,
    }


def _effective_profile(metadata: dict[str, Any], history: Iterable[dict[str, Any]]) -> tuple[str, list[str]]:
    profile = minimum_profile(metadata)
    reasons = [f"base routing floor {profile}"]
    promotion, promotion_reasons = task_class_promotion(history, str(metadata.get("taskClass", "")))
    if promotion is not None and PROFILE_RANK[promotion] > PROFILE_RANK[profile]:
        profile = promotion
        reasons.extend(promotion_reasons)
    declared = metadata.get("verificationProfile")
    if declared in PROFILE_RANK and PROFILE_RANK[declared] > PROFILE_RANK[profile]:
        profile = declared
        reasons.append("preserve declared verification profile")
    if profile == "V1" and metadata.get("executor") == "codex" and metadata.get("executionProfile") == "implementation":
        profile = "V2"
        reasons.append("promotion: Codex implementation requires an independent Claude reviewer")
    return profile, reasons


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
    if metadata["reviewer"] not in {"none", "gpt-6-sol", "claude-opus-5"}:
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
    if executor == "codex" and model not in {"gpt-6-luna", "gpt-6-sol", "gpt-6-astra"}:
        raise RoutingError("codex routing.model must be a supported GPT-6 model")
    if executor == "claude" and model != "claude-opus-5":
        raise RoutingError("claude routing.model must be claude-opus-5")
    if executor == "agy" and model not in {"agy", "gemini-3.8-flash"}:
        raise RoutingError("agy routing.model must be agy or gemini-3.8-flash")
    if model == "gemini-3.8-flash":
        if executor != "agy":
            raise RoutingError("gemini-3.8-flash requires executor=agy")
        role = str(order.get("roleForTask", "")).upper()
        if role not in GEMINI_CREATIVE_ROLES:
            raise RoutingError(
                "gemini-3.8-flash is reserved for UI, design, language, and creative Legionary roles"
            )
        if metadata["reasoningEffort"] not in {"low", "medium", "high"}:
            raise RoutingError("Gemini through agy supports only low, medium, or high effort")

    execution_profile = metadata["executionProfile"]
    if model == "gemini-3.8-flash" and execution_profile != "implementation":
        raise RoutingError("gemini-3.8-flash may only run as an implementation executor")
    if (model == "gpt-6-astra") != (execution_profile == "advisory"):
        raise RoutingError("gpt-6-astra is limited to the advisory execution profile")
    profile = metadata["verificationProfile"]
    base_floor = minimum_profile(metadata)
    floor, _ = _effective_profile(metadata, history)
    if PROFILE_RANK[profile] < PROFILE_RANK[floor]:
        raise RoutingError(f"routing profile {profile} violates hard floor {floor}")
    if executor == "codex" and model == "gpt-6-luna" and _requires_sol(metadata):
        raise RoutingError("codex routing.model requires gpt-6-sol for complex, uncertain, or consequential work")
    if executor == "codex":
        minimum_effort = _minimum_codex_effort(metadata)
        if EFFORT_RANK[metadata["reasoningEffort"]] < EFFORT_RANK[minimum_effort]:
            raise RoutingError(f"codex routing.reasoningEffort requires at least {minimum_effort} for this work")

    if execution_profile == "advisory":
        if executor != "codex":
            raise RoutingError("Astra advisory requires executor=codex")
        if order.get("roleForTask") != "ARCHITECTUS":
            raise RoutingError("Astra advisory requires roleForTask=ARCHITECTUS")
        if profile not in {"V2", "V3"} or metadata["reviewer"] != "none":
            raise RoutingError("Astra advisory records V2/V3 downstream floor with reviewer=none")
        if "terminalGate" in metadata:
            raise RoutingError("Astra advisory cannot be a terminal review")
        if EFFORT_RANK[metadata["reasoningEffort"]] < EFFORT_RANK["xhigh"]:
            raise RoutingError("Astra advisory requires at least xhigh effort")
        if not any(reason in ASTRA_ADVISORY_TRIGGERS for reason in reasons):
            raise RoutingError("Astra advisory requires an explicit architectural trigger")
    elif execution_profile == "terminal_review":
        if metadata.get("terminalGate") is not True:
            raise RoutingError("terminal review orders require terminalGate=true")
        if profile == "V0":
            raise RoutingError("V0 has no reviewer order")
        if metadata["reviewer"] != "none":
            raise RoutingError("terminal review orders cannot select another reviewer")
        expected_model = "gpt-6-sol" if profile == "V1" else "claude-opus-5"
        if model != expected_model:
            raise RoutingError(f"{profile} terminal review must run {expected_model}")
        expected_executor = "codex" if profile == "V1" else "claude"
        if executor != expected_executor:
            raise RoutingError(f"{profile} terminal review requires executor={expected_executor}")
    elif execution_profile == "implementation":
        if profile in {"V2", "V3"} and (executor in {"claude", "claudeFable"} or model == REVIEWER_BY_PROFILE[profile]):
            raise RoutingError("independent reviewer unavailable under current V2/V3 policy")
        if PROFILE_RANK[profile] > PROFILE_RANK[base_floor] and not any(
            reason.casefold().startswith(("promotion:", "escalation:")) for reason in reasons
        ):
            raise RoutingError("routing above the deterministic floor requires a promotion: or escalation: reason")
        expected_reviewer = REVIEWER_BY_PROFILE[profile]
        if model == expected_reviewer:
            raise RoutingError("implementation model cannot act as its own independent reviewer")
        if metadata["reviewer"] != expected_reviewer:
            raise RoutingError(f"{profile} requires reviewer {expected_reviewer}")
    else:
        raise RoutingError("routing.executionProfile must be implementation, advisory, or terminal_review")

    if profile == "V0" and not _all_pre_execution_predicates(metadata):
        raise RoutingError("V0 requires every pre-execution trust predicate to be true")
    if profile == "V0":
        proofs = order.get("proofCommands")
        has_required_proof = isinstance(proofs, list) and any(
            isinstance(proof, dict)
            and proof.get("required") is True
            and isinstance(proof.get("command"), str)
            and bool(proof["command"].strip())
            for proof in proofs
        )
        if not has_required_proof:
            raise RoutingError("V0 requires at least one required proofCommand before dispatch")
    if profile == "V3":
        gate = metadata.get("specialistGate")
        if not isinstance(gate, dict) or set(gate) != {"required", "approved", "approver"}:
            raise RoutingError("V3 requires explicit specialistGate required/approved/approver fields")
        if gate.get("required") is not True or gate.get("approved") is not True:
            raise RoutingError("V3 specialist/Boss gate is not approved")
        if not isinstance(gate.get("approver"), str) or not gate["approver"].strip():
            raise RoutingError("V3 specialistGate.approver must be non-empty")
        raise RoutingError(V3_APPROVAL_UNAVAILABLE)


def validate_terminal_review_result(routing: dict[str, Any] | None, result: dict[str, Any]) -> None:
    if routing is None or routing["executionProfile"] != "terminal_review":
        return
    if result.get("filesChanged") != []:
        raise RoutingError("terminal_review result filesChanged must be empty; corrections require a separate implementation order")
    self_review = result.get("selfReview")
    if isinstance(self_review, dict) and self_review.get("fixesApplied"):
        raise RoutingError("terminal_review result selfReview.fixesApplied must be empty")


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
