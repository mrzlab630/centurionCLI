#!/usr/bin/env python3
"""Owner-selected verification, advisory risk routing and order validation."""

from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timezone
from typing import Any, Iterable

from strict_json import StrictJSONError, strict_json_loads


ROUTING_PREFIX = "AQUILA_ROUTING_JSON_V1:"
CUTOVER_AT = datetime(2026, 8, 3, 11, 0, 42, tzinfo=timezone.utc)
PROFILES = ("V0", "V1", "V2", "V3")
PROFILE_RANK = {profile: index for index, profile in enumerate(PROFILES)}
SOL_PRIMARY_MODEL = "gpt-6.1-sol"
REVIEWER_BY_PROFILE = {
    "V0": "none",
    "V1": SOL_PRIMARY_MODEL,
    "V2": "claude-opus-5-5",
    "V3": "claude-opus-5-5",
}
REVIEWER_FALLBACK_BY_PROFILE: dict[str, str] = {}
ALLOWED_MODELS = {
    "gpt-6-luna",
    SOL_PRIMARY_MODEL,
    "gpt-6-astra",
    "claude-opus-5-5",
}
MODEL_REASONING_EFFORTS = {
    SOL_PRIMARY_MODEL: {"low", "medium", "high", "xhigh", "max"},
    "gpt-6-luna": {"high", "xhigh"},
    "gpt-6-astra": {"high", "xhigh"},
    "claude-opus-5-5": {"high", "xhigh", "max"},
}
ALLOWED_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}
ASTRA_ADVISORY_TRIGGERS = {
    "astra advisory: explicit user request",
    "astra advisory: material architecture ambiguity",
    "astra advisory: cross-system tradeoffs",
    "astra advisory: difficult diagnosis",
}
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
    return str(metadata.get("taskClass", "")).casefold()


def _contains_marker(text: str, markers: Iterable[str]) -> bool:
    normalized = re.sub(r"[-/_]+", " ", text)
    return any(re.search(r"(?<!\w)" + re.escape(marker.replace("_", " ")) + r"(?!\w)", normalized) for marker in markers)


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
        metadata["complexity"] != "low"
        or metadata["risk"] != "low"
        or metadata["ambiguity"] != "low"
        or metadata["reversibility"] != "high"
        or metadata["confidence"] != "high"
        or _contains_marker(_normalized_decision_text(metadata), HARD_RISK_MARKERS | V2_MARKERS)
    )


def _minimum_codex_effort(metadata: dict[str, Any]) -> str:
    decision_text = _normalized_decision_text(metadata)
    if metadata["executionProfile"] == "advisory":
        return "xhigh" if (
            metadata["complexity"] == "high"
            or metadata["risk"] == "high"
            or metadata["ambiguity"] == "high"
        ) else "high"
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
        return "low"
    if metadata["complexity"] == "low" and _contains_marker(decision_text, MECHANICAL_WORK_MARKERS):
        return "low"
    return "medium"


def minimum_profile(metadata: dict[str, Any]) -> str:
    """Return a review recommendation, never an additional source of authority.

    The historical function name is retained for callers. V3 is retired as a
    recommendation; explicit historical V3 records retain V2 review semantics.
    """
    decision_text = _normalized_decision_text(metadata)
    if metadata.get("risk") == "high" or _contains_marker(decision_text, HARD_RISK_MARKERS):
        return "V2"
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
    """Recommend verification from escaped defects; never change user authority."""
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
        if row.get("reviewer") in {SOL_PRIMARY_MODEL, "gpt-6-sol", "gpt-5.6-sol", "sol"} and row.get("status") == "done"
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
    """Read the approved verification choice and report separate recommendations."""
    profile, reasons = _effective_profile(metadata, history)
    advisory = metadata.get("executionProfile") == "advisory"
    terminal = metadata.get("executionProfile") == "terminal_review"
    reviewer = "none" if advisory or terminal else REVIEWER_BY_PROFILE[profile]
    return {
        "verificationProfile": profile,
        "route": "astra_advisory" if advisory else ("terminal_closure" if terminal else ("deterministic_only" if profile == "V0" else ("sol" if profile == "V1" else "claude-opus-5-5"))),
        "reviewer": reviewer,
        "fallbackReviewer": None,
        "specialistGateRequired": False,
        "specialistGateSatisfied": True,
        "reasons": reasons,
    }


def _effective_profile(metadata: dict[str, Any], history: Iterable[dict[str, Any]]) -> tuple[str, list[str]]:
    recommended = minimum_profile(metadata)
    reasons = [f"recommended verification profile {recommended}"]
    promotion, promotion_reasons = task_class_promotion(history, str(metadata.get("taskClass", "")))
    if promotion is not None and PROFILE_RANK[promotion] > PROFILE_RANK[recommended]:
        recommended = promotion
        reasons.extend(promotion_reasons)
    declared = metadata.get("verificationProfile")
    if recommended == "V1" and metadata.get("executionProfile") == "implementation" and not (
        metadata.get("executor") == "claude" and metadata.get("model") == "claude-opus-5-5"
    ):
        recommended = "V2"
        reasons.append("recommendation: independent Opus review for a Codex author")
    profile = declared if declared in PROFILE_RANK else recommended
    reasons.append("preserve owner-approved verification profile")
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
    if metadata["reasoningEffort"] not in MODEL_REASONING_EFFORTS[metadata["model"]]:
        allowed_efforts = ", ".join(sorted(MODEL_REASONING_EFFORTS[metadata["model"]], key=EFFORT_RANK.__getitem__))
        raise RoutingError(f"{metadata['model']} routing.reasoningEffort must be one of {allowed_efforts}")
    if metadata["verificationProfile"] not in PROFILES:
        raise RoutingError("routing.verificationProfile must be V0, V1, V2, or V3")
    if metadata["reviewer"] not in {"none", SOL_PRIMARY_MODEL, "claude-opus-5-5"}:
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
    if executor not in {"codex", "claude"}:
        raise RoutingError("routing.executor must be codex or claude for canonical routes")
    if executor == "codex" and model not in {"gpt-6-luna", SOL_PRIMARY_MODEL, "gpt-6-astra"}:
        raise RoutingError("codex routing.model must be a supported GPT-6 model")
    if executor == "claude" and model != "claude-opus-5-5":
        raise RoutingError("claude routing.model must be claude-opus-5-5")
    launch = order.get("launch")
    if isinstance(launch, dict) and isinstance(launch.get("command"), str):
        try:
            launch_arguments = shlex.split(launch["command"])
        except ValueError as exc:
            raise RoutingError("launch.command must have valid shell quoting") from exc
        if "--" in launch_arguments:
            launch_arguments = launch_arguments[:launch_arguments.index("--")]
        if any(argument.split("=", 1)[0] == "--fallback-model" for argument in launch_arguments):
            raise RoutingError("canonical routes do not permit --fallback-model")
        if executor == "claude":
            launch_models = []
            for index, argument in enumerate(launch_arguments):
                if argument == "--model":
                    launch_models.append(launch_arguments[index + 1] if index + 1 < len(launch_arguments) else "")
                elif argument.startswith("--model="):
                    launch_models.append(argument.split("=", 1)[1])
            if not launch_arguments or launch_arguments[0].rsplit("/", 1)[-1] != "claude" or launch_models != [model]:
                raise RoutingError("Claude launch.command must select exactly the canonical routing.model")
    execution_profile = metadata["executionProfile"]
    if (model == "gpt-6-astra") != (execution_profile == "advisory"):
        raise RoutingError("gpt-6-astra is limited to the advisory execution profile")
    profile = metadata["verificationProfile"]
    if executor == "codex" and model == "gpt-6-luna" and _requires_sol(metadata):
        raise RoutingError(f"codex routing.model requires {SOL_PRIMARY_MODEL} for complex, uncertain, or consequential work")
    if executor == "codex":
        minimum_effort = _minimum_codex_effort(metadata)
        if EFFORT_RANK[metadata["reasoningEffort"]] < EFFORT_RANK[minimum_effort]:
            raise RoutingError(f"codex routing.reasoningEffort requires at least {minimum_effort} for this work")

    if execution_profile == "advisory":
        if executor != "codex":
            raise RoutingError("Astra advisory requires executor=codex")
        if order.get("roleForTask") != "ARCHITECTUS":
            raise RoutingError("Astra advisory requires roleForTask=ARCHITECTUS")
        if metadata["reviewer"] != "none":
            raise RoutingError("Astra advisory requires reviewer=none; the user selects downstream verification")
        if "terminalGate" in metadata:
            raise RoutingError("Astra advisory cannot be a terminal review")
        if not any(reason in ASTRA_ADVISORY_TRIGGERS for reason in reasons):
            raise RoutingError("Astra advisory requires an explicit architectural trigger")
    elif execution_profile == "terminal_review":
        if metadata.get("terminalGate") is not True:
            raise RoutingError("terminal review orders require terminalGate=true")
        if profile == "V0":
            raise RoutingError("V0 has no reviewer order")
        if metadata["reviewer"] != "none":
            raise RoutingError("terminal review orders cannot select another reviewer")
        expected_model = SOL_PRIMARY_MODEL if profile == "V1" else "claude-opus-5-5"
        if model != expected_model:
            raise RoutingError(f"{profile} terminal review must run {expected_model}")
        expected_executor = "codex" if profile == "V1" else "claude"
        if executor != expected_executor:
            raise RoutingError(f"{profile} terminal review requires executor={expected_executor}")
    elif execution_profile == "implementation":
        if profile in {"V2", "V3"} and executor == "claude":
            raise RoutingError("independent reviewer unavailable under current V2/V3 policy")
        expected_reviewer = REVIEWER_BY_PROFILE[profile]
        if model == expected_reviewer:
            raise RoutingError("implementation model cannot act as its own independent reviewer")
        if metadata["reviewer"] != expected_reviewer:
            raise RoutingError(f"{profile} requires reviewer {expected_reviewer}")
    else:
        raise RoutingError("routing.executionProfile must be implementation, advisory, or terminal_review")

    if "trustPredicates" in metadata and not _trust_predicates_have_legacy_shape(metadata):
        raise RoutingError("routing.trustPredicates must retain the canonical boolean shape")
    if profile == "V0" and execution_profile == "implementation":
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
    # Historical V3/specialistGate metadata is readable, but grants no authority
    # and adds no admission gate. Mission authority is the recorded user order.


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
