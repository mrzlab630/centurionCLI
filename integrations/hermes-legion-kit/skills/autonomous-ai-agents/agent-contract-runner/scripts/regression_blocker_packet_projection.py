#!/usr/bin/env python3
"""Offline regressions for blocker_packet_projection.py."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from blocker_packet_projection import (  # noqa: E402
    AUTHORITY,
    PACKET_VERSION,
    BlockerProjectionError,
    build_blocker_packet,
    classify_blocker,
    serialize_packet,
    validate_packet,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def order() -> dict:
    return {
        "orderVersion": "AGENT_ORDER_JSON_V1",
        "orderId": "blocker-order-001",
        "missionId": "mission-001",
        "objectiveId": "objective-001",
        "stepId": "step-001",
        "allowedPaths": ["src/*"],
        "verificationProfile": "V2",
    }


def result(status: str = "done") -> dict:
    return {
        "resultVersion": "AGENT_RESULT_JSON_V1",
        "orderId": "blocker-order-001",
        "status": status,
        "summary": "fixture summary is intentionally not copied",
        "filesChanged": [],
        "proof": [{"status": "pass", "exitCode": 0}],
    }


def assert_packet(packet: dict, category: str) -> None:
    check(packet["packetVersion"] == PACKET_VERSION, "packet version")
    check(packet["authority"] == AUTHORITY, "controller-only authority")
    check(packet["category"] == category, f"category: {category}")
    validate_packet(packet)
    encoded = serialize_packet(packet)
    check(json.loads(encoded.decode("utf-8")) == packet, "strict JSON round trip")
    check(b"permit" not in encoded.lower(), "packet must not issue a permit")
    check(b"approved" not in encoded.lower(), "packet must not issue approval")


def main() -> int:
    base_order = order()

    # Missing and malformed candidate/result evidence fail closed.
    assert_packet(build_blocker_packet(base_order, None), "transport_controller")
    malformed = {"resultVersion": "WRONG", "orderId": base_order["orderId"]}
    assert_packet(build_blocker_packet(base_order, malformed), "contract_result")

    # Launcher timeout/nonzero closure is transport/controller evidence.
    assert_packet(
        build_blocker_packet(base_order, result(), closure={"timedOut": True, "exitCode": 124}),
        "transport_controller",
    )

    # Proof failure, canonical blocked result, and acceptance rejection remain distinct.
    assert_packet(
        build_blocker_packet(base_order, result(), proof=[{"status": "fail", "exitCode": 1}]),
        "proof",
    )
    assert_packet(build_blocker_packet(base_order, result("blocked")), "contract_result")
    assert_packet(
        build_blocker_packet(base_order, result(), closure={"acceptanceStatus": "rejected"}),
        "contract_result",
    )

    # Scope deviation is not silently reframed as a product result issue.
    deviating = result()
    deviating["scopeDeviations"] = ["unapproved path"]
    assert_packet(build_blocker_packet(base_order, deviating), "strategy_scope")

    # Observed product/side effect is explicitly surfaced and never replay-authorized.
    changed = result("failed")
    changed["filesChanged"] = [{"path": "src/module.py", "action": "modified"}]
    packet = build_blocker_packet(base_order, changed, closure={"sideEffectObserved": True})
    assert_packet(packet, "product_in_scope")
    check(packet["productBytesChanged"] is True, "product byte change")
    check(packet["sideEffectObserved"] is True, "side effect observed")

    # A completed result without enough blocker evidence remains unknown and
    # must require explicit controller reconciliation at high risk.
    completed_unknown = build_blocker_packet(base_order, result())
    assert_packet(completed_unknown, "unknown")
    check(completed_unknown["requiresOwnerDecision"] is False, "unknown evidence requires internal reconciliation")
    check(completed_unknown["risk"] == "high", "unknown evidence cannot be a high-risk false-negative")

    # V3 has no implicit approval path.
    v3 = dict(base_order, verificationProfile="V3")
    authority = build_blocker_packet(v3, result())
    assert_packet(authority, "security_authority")
    check(authority["requiresOwnerDecision"] is True, "missing external authority needs customer")

    # A blocked loop stops autonomous progress.
    assert_packet(
        build_blocker_packet(base_order, result(), loop_state={"status": "blocked", "noProgress": True}),
        "loop_no_progress",
    )

    # Contradictory product evidence is unknown, not guessed into a recovery.
    conflicting = result("failed")
    conflicting["productBytesChanged"] = False
    conflicting["filesChanged"] = [{"path": "src/module.py", "action": "modified"}]
    conflict_packet = build_blocker_packet(base_order, conflicting)
    assert_packet(conflict_packet, "unknown")
    check(conflict_packet["scopeStillBound"] is False, "conflict fails closed on scope")
    check(conflict_packet["requiresOwnerDecision"] is False, "conflict is internal controller work")

    # Raw bytes are immutable references bound to their exact digest and size.
    raw = b"immutable raw closure evidence\x00\xff"
    raw_copy = bytes(raw)
    packet = build_blocker_packet(base_order, result("failed"), raw_evidence={"evidence/closure.bin": raw})
    assert_packet(packet, "contract_result")
    reference = packet["evidenceReferences"][0]
    check(reference["path"] == "evidence/closure.bin", "raw evidence path")
    check(reference["sha256"] == hashlib.sha256(raw).hexdigest(), "raw evidence hash")
    check(reference["bytes"] == len(raw), "raw evidence size")
    check(raw == raw_copy, "raw bytes were not changed")

    # Inputs are observed but never mutated and untrusted summaries/secrets are not copied.
    source_order = copy.deepcopy(base_order)
    source_result = result("failed")
    source_result["summary"] = "do not emit token=secret-value"
    before_order = copy.deepcopy(source_order)
    before_result = copy.deepcopy(source_result)
    safe_packet = build_blocker_packet(source_order, source_result)
    check(source_order == before_order and source_result == before_result, "inputs were not mutated")
    check("secret-value" not in json.dumps(safe_packet), "secret-bearing value was not emitted")
    check("do not emit" not in safe_packet["summary"], "arbitrary result summary was not copied")

    # External prerequisite remains deterministic and controller-only.
    assert_packet(
        build_blocker_packet(base_order, result(), closure={"externalPrerequisite": False}),
        "external_prerequisite",
    )

    # Public classifier agrees with the builder and never returns authority.
    check(classify_blocker(base_order, None) == "transport_controller", "classifier API")
    check("authority" not in classify_blocker.__dict__, "classifier does not hold authority state")

    # Validation rejects non-strict or forged packet values.
    forged = build_blocker_packet(base_order, result())
    forged["summary"] = float("nan")
    try:
        validate_packet(forged)
    except BlockerProjectionError:
        pass
    else:
        raise AssertionError("unsafe forged packet was accepted")

    print("regression_blocker_packet_projection: PASS (21 checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
