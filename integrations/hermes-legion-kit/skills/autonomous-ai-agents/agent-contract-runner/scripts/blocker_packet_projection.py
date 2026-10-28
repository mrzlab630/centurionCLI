#!/usr/bin/env python3
"""Evidence-only projection of autonomous-control-plane blockers.

This module deliberately does not dispatch work, retry execution, authorize a
step, issue a permit, alter a canonical result, or accept a result.  It reads
already-supplied JSON-like objects and, optionally, raw evidence bytes.  Raw
bytes are referenced by SHA-256 and size only; they are never copied to the
packet.

Public API:

``build_blocker_packet(order, result, closure=None, proof=None,
loop_state=None, raw_evidence=None)``
    Return a deterministic, JSON-safe ``AQUILA_BLOCKER_PACKET_V1`` projection.

``classify_blocker(...)``
    Return one deterministic blocker category without producing authority.

``validate_packet(packet)`` and ``serialize_packet(packet)``
    Validate or canonically serialize a generated packet.  Both fail closed.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

PACKET_VERSION = "AQUILA_BLOCKER_PACKET_V1"
RESULT_VERSION = "AGENT_RESULT_JSON_V1"
ORDER_VERSION = "AGENT_ORDER_JSON_V1"
AUTHORITY = "controller-evidence-only"
CATEGORIES = (
    "transport_controller",
    "contract_result",
    "proof",
    "product_in_scope",
    "strategy_scope",
    "security_authority",
    "loop_no_progress",
    "external_prerequisite",
    "unknown",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_RE = re.compile(
    r"(?:secret|token|password|passwd|api[_-]?key|authorization|bearer|cookie|credential|private[_-]?key)",
    re.IGNORECASE,
)
_SAFE_PATH_RE = re.compile(r"^[^\x00\r\n]{1,1024}$")
_MAX_TEXT = 256
_MAX_LIST = 64
_MAX_DEPTH = 10

FIRST_UNMET_GATE = {
    "transport_controller": "transport_closure",
    "contract_result": "canonical_result_contract",
    "proof": "proof",
    "product_in_scope": "product_side_effect_review",
    "strategy_scope": "scope_binding",
    "security_authority": "trusted_authority",
    "loop_no_progress": "progress",
    "external_prerequisite": "external_prerequisite",
    "unknown": "controller_reconciliation",
}


class BlockerProjectionError(ValueError):
    """Raised when a packet is not strict, bounded, and JSON-safe."""


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _safe_text(value: Any, *, limit: int = _MAX_TEXT) -> str | None:
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    if _SECRET_RE.search(value):
        return None
    return value


def _text(value: Any) -> str:
    """Flatten bounded input text for classification without emitting it."""
    parts: list[str] = []
    seen: set[int] = set()

    def walk(item: Any, depth: int) -> None:
        if depth > _MAX_DEPTH or len(parts) >= 256:
            return
        if isinstance(item, str):
            parts.append(item.casefold())
            return
        if isinstance(item, (bytes, bytearray, memoryview)):
            return
        if isinstance(item, Mapping):
            marker = id(item)
            if marker in seen:
                return
            seen.add(marker)
            for key in sorted((key for key in item if isinstance(key, str)), key=str):
                parts.append(key.casefold())
                walk(item[key], depth + 1)
            return
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray, memoryview)):
            marker = id(item)
            if marker in seen:
                return
            seen.add(marker)
            for child in item[:_MAX_LIST]:
                walk(child, depth + 1)

    walk(value, 0)
    return " ".join(parts)


def _objects(*values: Any) -> list[Mapping[str, Any]]:
    return [value for value in values if isinstance(value, Mapping)]


def _truthy_field(objects: Sequence[Mapping[str, Any]], names: set[str]) -> bool:
    return any(item.get(name) is True for item in objects for name in names)


def _false_field(objects: Sequence[Mapping[str, Any]], names: set[str]) -> bool:
    return any(item.get(name) is False for item in objects for name in names)


def _values_for(objects: Sequence[Mapping[str, Any]], names: set[str]) -> list[Any]:
    return [item[name] for item in objects for name in names if name in item]


def _boolean_observation(
    objects: Sequence[Mapping[str, Any]], names: set[str]
) -> tuple[bool | None, bool]:
    values = [value for value in _values_for(objects, names) if isinstance(value, bool)]
    if not values:
        return None, False
    return (True if any(values) else False), len(set(values)) > 1


def _status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.casefold().replace("-", "_").replace(" ", "_")


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _identity_value(value: Any) -> str | None:
    if isinstance(value, str) and value and len(value) <= 256 and not _SECRET_RE.search(value):
        return value
    return None


def _nested_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("id", "missionId", "orderId", "stepId", "workItemId"):
            found = _identity_value(value.get(key))
            if found is not None:
                return found
    return _identity_value(value)


def _identity(order: Any, result: Any, closure: Any, loop_state: Any) -> tuple[dict[str, Any], bool]:
    """Extract only known identity fields and report contradictory values."""
    sources = _objects(order, result, closure, loop_state)
    conflicts = False

    def choose(keys: tuple[str, ...]) -> str | None:
        nonlocal conflicts
        values: list[str] = []
        for source in sources:
            for key in keys:
                if key in source:
                    found = _nested_id(source[key])
                    if found is not None:
                        values.append(found)
        unique = sorted(set(values))
        if len(unique) > 1:
            conflicts = True
            return None
        return unique[0] if unique else None

    mission_id = choose(("missionId", "mission_id", "mission"))
    objective_id = choose(("objectiveId", "objective_id"))
    order_id = choose(("orderId", "order_id"))
    step_id = choose(("stepId", "step_id", "currentStepId", "workItemId", "step"))

    identity: dict[str, Any] = {
        "mission": {"missionId": mission_id, "objectiveId": objective_id}
        if mission_id is not None or objective_id is not None
        else None,
        "order": {"orderId": order_id} if order_id is not None else None,
        "step": {"stepId": step_id} if step_id is not None else None,
    }
    return identity, conflicts


def _valid_json_shape(value: Any, *, depth: int = 0) -> bool:
    if depth > _MAX_DEPTH:
        return False
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return len(value) <= _MAX_LIST and all(_valid_json_shape(item, depth=depth + 1) for item in value)
    if isinstance(value, dict):
        return len(value) <= 128 and all(
            isinstance(key, str) and _valid_json_shape(item, depth=depth + 1)
            for key, item in value.items()
        )
    return False


def _contains_secret_material(value: Any, *, depth: int = 0) -> bool:
    if depth > _MAX_DEPTH:
        return True
    if isinstance(value, str):
        return bool(_SECRET_RE.search(value))
    if isinstance(value, Mapping):
        return any(
            (isinstance(key, str) and _SECRET_RE.search(key))
            or _contains_secret_material(item, depth=depth + 1)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret_material(item, depth=depth + 1) for item in value)
    return False


def _path_is_safe(path: Any) -> bool:
    return isinstance(path, str) and bool(_SAFE_PATH_RE.fullmatch(path)) and not _SECRET_RE.search(path)


def _raw_items(raw_evidence: Any) -> tuple[list[tuple[str | None, bytes]], bool]:
    """Normalize caller-owned raw bytes without retaining or mutating them."""
    if raw_evidence is None:
        return [], False

    def as_bytes(value: Any) -> bytes | None:
        if isinstance(value, bytes):
            return bytes(value)
        if isinstance(value, (bytearray, memoryview)):
            return bytes(value)
        return None

    direct = as_bytes(raw_evidence)
    if direct is not None:
        return [(None, direct)], False

    items: list[tuple[str | None, bytes]] = []
    malformed = False
    if isinstance(raw_evidence, Mapping):
        # Also accept one descriptor: {path: ..., data/bytes/content: b"..."}.
        descriptor_data = next(
            (raw_evidence[key] for key in ("data", "content", "rawBytes", "bytes") if key in raw_evidence),
            None,
        )
        descriptor_bytes = as_bytes(descriptor_data)
        if descriptor_bytes is not None:
            path = raw_evidence.get("path")
            items.append((path if isinstance(path, str) else None, descriptor_bytes))
        else:
            for path in sorted(raw_evidence, key=lambda item: str(item)):
                content = as_bytes(raw_evidence[path]) if isinstance(path, str) else None
                if content is None:
                    malformed = True
                else:
                    items.append((path, content))
    elif isinstance(raw_evidence, Sequence) and not isinstance(raw_evidence, (str, bytes, bytearray, memoryview)):
        for item in raw_evidence[:_MAX_LIST]:
            if isinstance(item, Mapping):
                content = next(
                    (as_bytes(item[key]) for key in ("data", "content", "rawBytes", "bytes") if key in item),
                    None,
                )
                if content is None:
                    malformed = True
                else:
                    path = item.get("path")
                    items.append((path if isinstance(path, str) else None, content))
            else:
                content = as_bytes(item)
                if content is None:
                    malformed = True
                else:
                    items.append((None, content))
    else:
        malformed = True
    return items, malformed


def _evidence_references(raw_evidence: Any) -> tuple[list[dict[str, Any]], bool]:
    items, malformed = _raw_items(raw_evidence)
    refs: list[dict[str, Any]] = []
    for supplied_path, content in items:
        digest = hashlib.sha256(content).hexdigest()
        path = supplied_path if _path_is_safe(supplied_path) else f"raw-evidence/{digest}.bin"
        refs.append({"path": path, "sha256": digest, "bytes": len(content)})
    refs.sort(key=lambda item: (item["path"], item["sha256"], item["bytes"]))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for ref in refs:
        key = (ref["path"], ref["sha256"], ref["bytes"])
        if key not in seen:
            seen.add(key)
            deduped.append(ref)
    return deduped, malformed


def _closure_failed(closure: Any) -> bool:
    objects = _objects(closure)
    for item in objects:
        for key in ("timedOut", "timeout", "captureFailure", "transportFailure", "streamFailure"):
            if item.get(key) is True:
                return True
        for key in ("exitCode", "returnCode", "processExitCode"):
            value = item.get(key)
            if _is_int(value) and value != 0:
                return True
        state = _status(item.get("status") or item.get("closureStatus") or item.get("transportStatus"))
        if state in {"failed", "failure", "timeout", "timed_out", "aborted", "error"}:
            return True
    text = _text(closure)
    return any(marker in text for marker in ("transport failure", "capture failure", "timed out", "timeout"))


def _result_malformed(order: Any, result: Any) -> bool:
    if not isinstance(result, Mapping):
        return True
    if result.get("resultVersion") != RESULT_VERSION:
        return True
    if isinstance(order, Mapping) and "orderId" in order and result.get("orderId") != order.get("orderId"):
        return True
    if _status(result.get("status")) not in {"done", "blocked", "failed"}:
        return True
    return False


def _order_malformed(order: Any) -> bool:
    return not isinstance(order, Mapping) or (
        "orderVersion" in order and order.get("orderVersion") != ORDER_VERSION
    ) or ("orderId" in order and not _identity_value(order.get("orderId")))


def _proof_failed(proof: Any, result: Any) -> bool:
    values: list[Any] = []
    if isinstance(proof, Mapping):
        values.append(proof)
    elif isinstance(proof, list):
        values.extend(proof)
    if isinstance(result, Mapping) and isinstance(result.get("proof"), list):
        values.extend(result["proof"])
    if proof is not None and not isinstance(proof, (Mapping, list)):
        return True
    for item in values:
        if not isinstance(item, Mapping):
            return True
        state = _status(item.get("status") or item.get("result"))
        if state in {"fail", "failed", "failure", "error", "not_run", "blocked"}:
            return True
        exit_code = item.get("exitCode")
        if _is_int(exit_code) and exit_code != 0:
            return True
        if item.get("passed") is False or item.get("verified") is False:
            return True
    return False


def _acceptance_rejected(result: Any, closure: Any, proof: Any) -> bool:
    for item in _objects(result, closure, proof):
        for key in ("accepted", "acceptancePassed", "controllerAccepted", "acceptedByController"):
            if item.get(key) is False:
                return True
        for key in ("acceptanceStatus", "acceptanceResult", "controllerAcceptance", "acceptance"):
            value = item.get(key)
            if isinstance(value, str) and _status(value) in {"rejected", "failed", "failure", "denied"}:
                return True
            if isinstance(value, Mapping) and (
                value.get("accepted") is False
                or _status(value.get("status")) in {"rejected", "failed", "denied"}
            ):
                return True
    return False


def _scope_observation(order: Any, result: Any) -> tuple[bool | None, bool]:
    if not isinstance(result, Mapping):
        return False, False
    deviations = result.get("scopeDeviations")
    forbidden = result.get("forbiddenPatternHits")
    if _nonempty_list(deviations) or _nonempty_list(forbidden):
        return False, False
    explicit, conflict = _boolean_observation(
        _objects(order, result), {"scopeStillBound", "scopeBound", "inScope"}
    )
    if explicit is False:
        return False, conflict

    changed = result.get("filesChanged")
    allowed = order.get("allowedPaths") if isinstance(order, Mapping) else None
    forbidden_paths = order.get("forbiddenPaths") if isinstance(order, Mapping) else None
    if isinstance(changed, list) and isinstance(allowed, list) and allowed:
        for item in changed:
            path = item.get("path") if isinstance(item, Mapping) else None
            if not isinstance(path, str) or not any(fnmatch.fnmatch(path, pattern) for pattern in allowed if isinstance(pattern, str)):
                return False, conflict
    if isinstance(changed, list) and isinstance(forbidden_paths, list):
        for item in changed:
            path = item.get("path") if isinstance(item, Mapping) else None
            if isinstance(path, str) and any(fnmatch.fnmatch(path, pattern) for pattern in forbidden_paths if isinstance(pattern, str)):
                return False, conflict
    if explicit is not None:
        return explicit, conflict
    return True, conflict


def _product_observation(result: Any, closure: Any) -> tuple[bool | None, bool]:
    objects = _objects(result, closure)
    explicit, conflict = _boolean_observation(
        objects, {"productBytesChanged", "productChanged", "productMutationObserved"}
    )
    derived: list[bool] = []
    if isinstance(result, Mapping) and isinstance(result.get("filesChanged"), list):
        for item in result["filesChanged"]:
            action = _status(item.get("action")) if isinstance(item, Mapping) else None
            if action is not None:
                derived.append(action != "none")
    if derived:
        derived_value = any(derived)
        if explicit is not None and explicit != derived_value:
            conflict = True
        explicit = derived_value if explicit is None else explicit
    return explicit, conflict


def _side_effect_observation(result: Any, closure: Any, product_changed: bool | None) -> tuple[bool | None, bool]:
    explicit, conflict = _boolean_observation(
        _objects(result, closure),
        {"sideEffectObserved", "sideEffectsObserved", "sideEffect", "externalSideEffect"},
    )
    if product_changed is True:
        if explicit is False:
            conflict = True
        explicit = True
    return explicit, conflict


def _evidence_conflicts(
    order: Any,
    result: Any,
    closure: Any,
    proof: Any,
    loop_state: Any,
    raw_evidence: Any,
) -> bool:
    """Return whether any independent observation disagrees."""
    _, identity_conflict = _identity(order, result, closure, loop_state)
    _, scope_conflict = _scope_observation(order, result)
    product_changed, product_conflict = _product_observation(result, closure)
    _, side_effect_conflict = _side_effect_observation(result, closure, product_changed)
    _, side_scope_conflict = _boolean_observation(_objects(result, closure), {"sideEffectObserved"})
    _, raw_bad = _evidence_references(raw_evidence)
    return bool(
        identity_conflict
        or scope_conflict
        or product_conflict
        or side_effect_conflict
        or side_scope_conflict
        or raw_bad
    )


def _authority_unavailable(order: Any, closure: Any) -> bool:
    # Only explicit controller observations can identify missing user authority.
    # Retired verifier flags, V3 labels and quoted worker prose are not vetoes.
    return any(item.get("authorityAvailable") is False for item in _objects(order, closure))


def _loop_blocked(loop_state: Any) -> bool:
    if not isinstance(loop_state, Mapping):
        return False
    state = _status(loop_state.get("status") or loop_state.get("state") or loop_state.get("decision"))
    if state in {"blocked", "stopped", "no_progress", "escalate", "escalation"}:
        return True
    for key in ("blocked", "noProgress", "repeatedFailure", "goalDrift", "budgetExhausted"):
        if loop_state.get(key) is True:
            return True
    return any(
        marker in _text(loop_state)
        for marker in ("no progress", "repeated failure", "goal drift", "budget exhausted")
    )


def _external_prerequisite(*values: Any) -> bool:
    text = _text(values)
    if any(marker in text for marker in ("external prerequisite", "dependency unavailable", "network unavailable", "environment prerequisite")):
        return True
    return any(
        item.get(key) is False
        for item in _objects(*values)
        for key in ("externalPrerequisite", "prerequisiteMet", "dependencyAvailable", "environmentReady", "networkAvailable")
    )


def classify_blocker(
    order: Any,
    result: Any,
    closure: Any = None,
    proof: Any = None,
    loop_state: Any = None,
    raw_evidence: Any = None,
) -> str:
    """Classify supplied evidence using a fixed, fail-closed precedence order."""
    if _evidence_conflicts(order, result, closure, proof, loop_state, raw_evidence):
        return "unknown"
    if _authority_unavailable(order, closure):
        return "security_authority"
    if _loop_blocked(loop_state):
        return "loop_no_progress"
    if _external_prerequisite(order, result, closure, proof, loop_state):
        return "external_prerequisite"
    if _closure_failed(closure):
        return "transport_controller"
    if result is None:
        return "transport_controller"
    if _order_malformed(order) or _result_malformed(order, result):
        return "contract_result"
    scope_bound, scope_conflict = _scope_observation(order, result)
    product_changed, product_conflict = _product_observation(result, closure)
    side_effect, side_effect_conflict = _side_effect_observation(result, closure, product_changed)
    _, side_scope_conflict = _boolean_observation(_objects(result, closure), {"sideEffectObserved"})
    if scope_conflict or product_conflict or side_effect_conflict or side_scope_conflict:
        return "unknown"
    if scope_bound is False:
        return "strategy_scope"
    if _acceptance_rejected(result, closure, proof):
        return "contract_result"
    if _proof_failed(proof, result):
        return "proof"
    if isinstance(result, Mapping) and _status(result.get("status")) in {"blocked", "failed"}:
        if side_effect is True or product_changed is True:
            return "product_in_scope"
        return "contract_result"
    if side_effect is True or product_changed is True:
        return "product_in_scope"
    return "unknown"


def _hypotheses(category: str, *, product_changed: bool | None, side_effect: bool | None, raw_bad: bool) -> list[str]:
    values = {
        "transport_controller": ["candidate_or_controller_transport_is_unavailable"],
        "contract_result": ["canonical_result_is_missing_or_rejected"],
        "proof": ["required_proof_did_not_pass"],
        "product_in_scope": ["product_side_effect_requires_controller_review"],
        "strategy_scope": ["observed_change_is_outside_frozen_scope"],
        "security_authority": ["required_authority_evidence_is_unavailable"],
        "loop_no_progress": ["bounded_loop_reports_no_progress_or_blocked_state"],
        "external_prerequisite": ["external_prerequisite_is_unavailable"],
        "unknown": ["evidence_is_insufficient_or_conflicting"],
    }[category]
    if product_changed is None:
        values.append("product_byte_change_is_not_observed")
    if side_effect is None:
        values.append("side_effect_state_is_uncertain")
    if raw_bad:
        values.append("raw_evidence_input_is_malformed")
    return values


def _recovery_candidates(category: str, *, side_effect: bool | None) -> list[str]:
    candidates = {
        "transport_controller": ["repair_transport_without_replaying_product_work"],
        "contract_result": ["perform_result_only_correction_without_product_replay"],
        "proof": ["collect_or_rerun_required_proof_without_widening_scope"],
        "product_in_scope": ["review_existing_side_effect_before_any_retry"],
        "strategy_scope": ["request_owner_scope_or_strategy_decision"],
        "security_authority": ["record_user_scope_decision"],
        "loop_no_progress": ["warn_about_progress_and_recommend_strategy_within_authorized_budget"],
        "external_prerequisite": ["resolve_prerequisite_outside_executor_scope"],
        "unknown": ["reconcile_conflicting_evidence_before_action"],
    }[category]
    if side_effect is True and "review_existing_side_effect_before_any_retry" not in candidates:
        candidates.append("do_not_replay_observed_side_effect")
    return candidates


def build_blocker_packet(
    order: Any,
    result: Any,
    closure: Any = None,
    proof: Any = None,
    loop_state: Any = None,
    raw_evidence: Any = None,
) -> dict[str, Any]:
    """Build a controller-evidence-only blocker packet without side effects."""
    category = classify_blocker(order, result, closure, proof, loop_state, raw_evidence)
    identity, _ = _identity(order, result, closure, loop_state)
    product_changed, product_conflict = _product_observation(result, closure)
    side_effect, side_effect_conflict = _side_effect_observation(result, closure, product_changed)
    _, side_scope_conflict = _boolean_observation(_objects(result, closure), {"sideEffectObserved"})
    scope_bound, _ = _scope_observation(order, result)
    references, raw_bad = _evidence_references(raw_evidence)
    conflicting = _evidence_conflicts(order, result, closure, proof, loop_state, raw_evidence)
    if product_conflict:
        product_changed = None
    if side_effect_conflict or side_scope_conflict:
        side_effect = None
    if conflicting:
        category = "unknown"
        scope_bound = False
    if scope_bound is None:
        scope_bound = False
    # Unknown, insufficient, or conflicting evidence is itself a blocker: a
    # completed-looking result must not receive an implicit low-risk outcome.
    blocker_present = category == "unknown" or conflicting or _closure_failed(closure) or result is None
    packet: dict[str, Any] = {
        "packetVersion": PACKET_VERSION,
        "identity": identity,
        "category": category,
        "summary": {
            "transport_controller": "Controller transport or closure evidence is unavailable.",
            "contract_result": "The candidate or canonical result cannot satisfy the result contract.",
            "proof": "Required proof evidence did not pass.",
            "product_in_scope": "A product-side effect is observed and must not be replayed implicitly.",
            "strategy_scope": "Observed evidence is outside the frozen strategy or scope.",
            "security_authority": "The controller reports that required user authority is unavailable.",
            "loop_no_progress": "The bounded control loop is blocked or reports no progress.",
            "external_prerequisite": "An external prerequisite is unavailable.",
            "unknown": "Evidence is insufficient or conflicting; the controller must reconcile it.",
        }[category],
        "evidenceReferences": references,
        "productBytesChanged": product_changed,
        "sideEffectObserved": side_effect,
        "scopeStillBound": bool(scope_bound),
        "hypotheses": _hypotheses(category, product_changed=product_changed, side_effect=side_effect, raw_bad=raw_bad),
        "recoveryCandidates": _recovery_candidates(category, side_effect=side_effect),
        "risk": "high" if category in {"unknown", "security_authority", "strategy_scope", "product_in_scope", "loop_no_progress", "external_prerequisite"} or conflicting or side_effect is None else ("medium" if blocker_present else "low"),
        # Projection asks the customer only for missing external authority.
        # Transport, proof, uncertainty and bounded replanning are controller work.
        "requiresOwnerDecision": category == "security_authority" or any(
            item.get("decisionOwner") == "customer" or item.get("externalAuthorityRequired") is True
            for item in _objects(loop_state, closure, proof)
        ),
        "firstUnmetGate": FIRST_UNMET_GATE[category],
        "authority": AUTHORITY,
    }
    for key, value in (("missionId", identity["mission"] and identity["mission"].get("missionId")), ("objectiveId", identity["mission"] and identity["mission"].get("objectiveId")), ("orderId", identity["order"] and identity["order"].get("orderId")), ("stepId", identity["step"] and identity["step"].get("stepId"))):
        if value is not None:
            packet[key] = value
    return validate_packet(packet)


def validate_packet(packet: Any) -> dict[str, Any]:
    """Validate a packet and return it; reject non-JSON-safe or unsafe fields."""
    if not isinstance(packet, dict):
        raise BlockerProjectionError("packet must be an object")
    required = {
        "packetVersion", "identity", "category", "summary", "evidenceReferences",
        "productBytesChanged", "sideEffectObserved", "scopeStillBound", "hypotheses",
        "recoveryCandidates", "risk", "requiresOwnerDecision", "firstUnmetGate", "authority",
    }
    if not required.issubset(packet):
        raise BlockerProjectionError("packet is missing required fields")
    if packet.get("packetVersion") != PACKET_VERSION or packet.get("authority") != AUTHORITY:
        raise BlockerProjectionError("packet version or authority is invalid")
    if packet.get("category") not in CATEGORIES:
        raise BlockerProjectionError("packet category is invalid")
    if packet.get("risk") not in {"low", "medium", "high"}:
        raise BlockerProjectionError("packet risk is invalid")
    for key in ("productBytesChanged", "sideEffectObserved"):
        if packet[key] is not None and not _is_bool(packet[key]):
            raise BlockerProjectionError(f"{key} must be boolean or null")
    if not _is_bool(packet["scopeStillBound"]) or not _is_bool(packet["requiresOwnerDecision"]):
        raise BlockerProjectionError("packet boolean fields are invalid")
    if not isinstance(packet.get("summary"), str) or _SECRET_RE.search(packet["summary"]):
        raise BlockerProjectionError("packet summary is unsafe")
    if not isinstance(packet.get("firstUnmetGate"), str) or packet["firstUnmetGate"] != FIRST_UNMET_GATE[packet["category"]]:
        raise BlockerProjectionError("packet firstUnmetGate is inconsistent")
    if not isinstance(packet.get("identity"), dict) or not _valid_json_shape(packet["identity"]):
        raise BlockerProjectionError("packet identity is not JSON-safe")
    for item in packet["evidenceReferences"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "bytes"}:
            raise BlockerProjectionError("evidence reference shape is invalid")
        if not _path_is_safe(item["path"]) or not _SHA256_RE.fullmatch(item["sha256"]):
            raise BlockerProjectionError("evidence reference path or digest is invalid")
        if not _is_int(item["bytes"]) or item["bytes"] < 0:
            raise BlockerProjectionError("evidence reference size is invalid")
    for key in ("hypotheses", "recoveryCandidates"):
        if not isinstance(packet[key], list) or not all(isinstance(item, str) and not _SECRET_RE.search(item) for item in packet[key]):
            raise BlockerProjectionError(f"packet {key} is unsafe")
    for key in ("missionId", "objectiveId", "orderId", "stepId"):
        if key in packet and _identity_value(packet[key]) is None:
            raise BlockerProjectionError(f"packet {key} is unsafe")
    if not _valid_json_shape(packet):
        raise BlockerProjectionError("packet contains non-strict JSON values")
    if _contains_secret_material(packet):
        raise BlockerProjectionError("packet contains secret-bearing material")
    return packet


def serialize_packet(packet: Mapping[str, Any]) -> bytes:
    """Return canonical strict JSON bytes for a validated packet."""
    validate_packet(dict(packet))
    try:
        return json.dumps(packet, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise BlockerProjectionError(f"packet cannot be serialized as strict JSON: {exc}") from exc


# Explicit alias for callers that prefer a schema-oriented name.
serialize_blocker_packet = serialize_packet


if __name__ == "__main__":
    print("blocker_packet_projection: PASS (importable evidence-only API)")
