#!/usr/bin/env python3
"""Shared response-envelope parsing for executor handoffs.

The controller accepts either one strict JSON document or one fenced ``json``
document with whitespace around it.  Anything else is rejected before schema
validation.  The raw bytes remain available to the caller for evidence and the
normalized bytes are deterministic for hashing and downstream custody.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable

from strict_json import StrictJSONError, strict_json_load_bytes


RESPONSE_ENVELOPE_VERSION = "AGENT_RESPONSE_ENVELOPE_V1"
RAW_JSON = "raw_json"
JSON_FENCE = "json_fence"
SUPPORTED_TRANSPORTS = frozenset({RAW_JSON, JSON_FENCE})
_MEDIA_TYPE_RE = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:[\t ]*;[^\r\n]*)?")
_JSON_FENCE_RE = re.compile(
    r"\A[\t\n\r ]*```json[\t ]*\r?\n(?P<body>[\s\S]*?)\r?\n```[\t\n\r ]*\Z",
)


class ResponseEnvelopeError(ValueError):
    """Raised when executor output is not an unambiguous response envelope."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def valid_media_type(value: Any) -> bool:
    return isinstance(value, str) and _MEDIA_TYPE_RE.fullmatch(value) is not None


@dataclass(frozen=True)
class ParsedResponse:
    value: Any
    raw_bytes: bytes
    normalized_bytes: bytes
    transport: str

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()

    @property
    def normalized_sha256(self) -> str:
        return hashlib.sha256(self.normalized_bytes).hexdigest()


def _unicode_scalars(value: Any) -> None:
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode_scalars(key)
            _unicode_scalars(item)
    elif isinstance(value, list):
        for item in value:
            _unicode_scalars(item)


def _response_json(content: bytes, label: str) -> Any:
    try:
        value = strict_json_load_bytes(content, label)
        _unicode_scalars(value)
    except (UnicodeError, RecursionError) as exc:
        raise StrictJSONError(f"{label} contains invalid Unicode or excessive nesting") from exc
    return value


def _allowed_transports(value: Iterable[str] | None) -> frozenset[str]:
    if value is None:
        return SUPPORTED_TRANSPORTS
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", "acceptedTransports must be a list of strings")
    allowed = frozenset(value)
    unknown = allowed - SUPPORTED_TRANSPORTS
    if unknown:
        raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", f"unsupported response transports: {sorted(unknown)}")
    if not allowed:
        raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", "at least one response transport is required")
    return allowed


def parse_response_bytes(
    raw_bytes: bytes,
    label: str = "response",
    *,
    allowed_transports: Iterable[str] | None = None,
) -> ParsedResponse:
    """Parse one raw JSON response or one clean ``json`` fence.

    The fence is anchored to the complete document.  This deliberately rejects
    prose before/after JSON, multiple objects, multiple fences, refusal text,
    truncated documents, duplicate keys, and non-finite numbers.
    """
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", f"{label} must be bytes")
    content = bytes(raw_bytes)
    allowed = _allowed_transports(allowed_transports)
    raw_error: StrictJSONError | None = None

    if RAW_JSON in allowed:
        try:
            value = _response_json(content, label)
        except StrictJSONError as exc:
            raw_error = exc
        else:
            return ParsedResponse(value, content, content, RAW_JSON)

    if JSON_FENCE in allowed:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", f"{label} is not valid UTF-8: {exc}") from exc
        match = _JSON_FENCE_RE.fullmatch(text)
        if match is not None:
            inner = match.group("body").encode("utf-8")
            try:
                value = _response_json(inner, f"{label} fenced JSON")
            except StrictJSONError as exc:
                raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", str(exc)) from exc
            return ParsedResponse(value, content, inner, JSON_FENCE)

    if raw_error is not None:
        raise ResponseEnvelopeError("RESPONSE_FORMAT_ERROR", str(raw_error)) from raw_error
    raise ResponseEnvelopeError(
        "RESPONSE_FORMAT_ERROR",
        f"{label} must be raw JSON or exactly one fenced json block with whitespace around it",
    )


def handoff_errors(value: Any, order_id: str) -> list[str]:
    required = {"version", "schemaId", "inReplyTo", "senderRole", "recipientRole"}
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - {"objectiveId"}:
        return ["RESPONSE_SCHEMA_ERROR: handoff has invalid fields"]
    errors = []
    if value["version"] != "AGENT_HANDOFF_V1" or value["schemaId"] != "AGENT_RESULT_JSON_V1":
        errors.append("RESPONSE_SCHEMA_ERROR: handoff version/schemaId mismatch")
    if value["inReplyTo"] != order_id:
        errors.append("RESPONSE_IDENTITY_ERROR: handoff.inReplyTo must match orderId")
    for key in ("senderRole", "recipientRole", "objectiveId"):
        if key in value and (not isinstance(value[key], str) or not value[key].strip()):
            errors.append(f"RESPONSE_SCHEMA_ERROR: handoff.{key} must be a non-empty string")
    return errors


def validate_handoff_order(order: dict[str, Any], routing: dict[str, Any] | None = None) -> list[str]:
    contract = order.get("outputContract", {})
    if "handoff" not in contract:
        return []
    expected = contract["handoff"]
    errors = handoff_errors(expected, order.get("orderId"))
    if errors:
        return errors
    for key, order_key in (("senderRole", "roleForTask"), ("recipientRole", "controller")):
        if expected[key] != order.get(order_key):
            errors.append(f"RESPONSE_IDENTITY_ERROR: handoff.{key} must match order.{order_key}")
    if routing is None:
        routing = order.get("routing")
    if isinstance(routing, dict) and "objectiveId" in expected and expected["objectiveId"] != routing.get("objectiveId"):
        errors.append("RESPONSE_IDENTITY_ERROR: handoff.objectiveId must match routing.objectiveId")
    return errors


def validate_response_handoff(candidate: dict[str, Any], order: dict[str, Any], routing: dict[str, Any] | None = None) -> list[str]:
    errors = validate_handoff_order(order, routing)
    expected = order.get("outputContract", {}).get("handoff")
    if expected is not None and "handoff" not in candidate:
        errors.append("RESPONSE_SCHEMA_ERROR: result.handoff is required by the order output contract")
    if expected is not None and candidate.get("handoff") != expected:
        errors.append("RESPONSE_IDENTITY_ERROR: result.handoff must equal order.outputContract.handoff")
    if "handoff" in candidate:
        handoff = candidate["handoff"]
        errors.extend(handoff_errors(handoff, candidate.get("orderId")))
        if isinstance(handoff, dict):
            if handoff.get("senderRole") != order.get("roleForTask"):
                errors.append("RESPONSE_IDENTITY_ERROR: result.handoff.senderRole must match order.roleForTask")
            if handoff.get("recipientRole") != order.get("controller"):
                errors.append("RESPONSE_IDENTITY_ERROR: result.handoff.recipientRole must match order.controller")
            if routing is not None and "objectiveId" in handoff and handoff.get("objectiveId") != routing.get("objectiveId"):
                errors.append("RESPONSE_IDENTITY_ERROR: result.handoff.objectiveId must match routing.objectiveId")
    return errors


def response_state_errors(candidate: Any) -> list[str]:
    if not isinstance(candidate, dict):
        return []
    if candidate.get("type") == "refusal" or candidate.get("refusal"):
        return ["RESPONSE_REFUSED: provider reported a refusal"]
    if candidate.get("status") in ("incomplete", "in_progress") or candidate.get("incomplete_details"):
        return ["RESPONSE_INCOMPLETE: provider response is not complete"]
    return []


def response_envelope(parsed: ParsedResponse, *, raw_evidence_path: str, normalized_path: str) -> dict[str, Any]:
    """Return controller-owned metadata binding raw and normalized bytes."""
    return {
        "version": RESPONSE_ENVELOPE_VERSION,
        "transport": parsed.transport,
        "rawEvidencePath": raw_evidence_path,
        "rawSha256": parsed.raw_sha256,
        "rawBytes": len(parsed.raw_bytes),
        "normalizedCandidatePath": normalized_path,
        "normalizedSha256": parsed.normalized_sha256,
        "normalizedBytes": len(parsed.normalized_bytes),
    }
