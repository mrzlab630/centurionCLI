#!/usr/bin/env python3
"""Exercise accepted handoffs through real Gateway processes with fake CLIs."""

from __future__ import annotations

import hashlib
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from accepted_inputs import verify_input_results
from artifact_lineage import verify_anchor
import regression_result_gateway as fixture


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_stage(name: str, profile: str, *, inputs: list[dict[str, Any]] | None = None, product: bool = False) -> dict[str, Any]:
    executor = "claude" if profile == "terminal_review" else "codex"
    mode = "stdout-claude-wrapper" if executor == "claude" else "valid"
    paths = fixture.make_case(
        name, mode, executor=executor, side_effect=product,
        candidate_source="stdout" if executor == "claude" else "file",
    )
    old_order = Path(paths["order"])
    order = fixture.read_json(old_order)
    namespace = fixture.artifact_namespace(fixture.ROOT, order["orderId"])
    paths["order"] = namespace / "order.json"
    paths["test_count"] = namespace / ("advice.md" if profile == "advisory" else "handoff.md")
    paths["namespace"] = namespace
    if inputs is not None:
        order["inputResults"] = inputs
    if profile == "advisory":
        order.update(roleForTask="ARCHITECTUS", riskLevel="medium")
        order["allowedPaths"] = [str(namespace / "**")]
        route = fixture.routing_metadata(
            order["orderId"], executor, taskClass="architecture_advisory",
            complexity="high", risk="medium", ambiguity="high", model="gpt-6-astra",
            reasoningEffort="xhigh", executionProfile="advisory", verificationProfile="V2",
            reviewer="none", confidence="medium",
            reasons=["astra advisory: material architecture ambiguity"],
        )
        order["launch"]["command"] = shlex.join([
            "codex", "exec", "--model", "gpt-6-astra", "-c", "model_reasoning_effort=xhigh",
            "--sandbox", "read-only", "-C", str(fixture.ROOT),
            "--output-last-message", str(paths["candidate"]), "--json",
            "valid", str(paths["candidate"]), order["orderId"], executor, "done", "NONE", "0", "0",
        ])
    elif profile == "terminal_review":
        order.update(roleForTask="REVIEWER", riskLevel="medium")
        route = fixture.routing_metadata(
            order["orderId"], executor, risk="medium", model="claude-opus-5",
            executionProfile="terminal_review", verificationProfile="V2", reviewer="none",
            terminalGate=True, reasoningEffort="high",
        )
    else:
        order.update(roleForTask="CODER", riskLevel="medium")
        route = fixture.routing_metadata(
            order["orderId"], executor, risk="medium", model="gpt-6-sol",
            reasoningEffort="high", executionProfile="implementation", verificationProfile="V2",
            reviewer="claude-opus-5",
        )
        command = shlex.split(order["launch"]["command"])
        command[command.index("--model") + 1] = "gpt-6-sol"
        command[command.index("-c") + 1] = "model_reasoning_effort=high"
        order["launch"]["command"] = shlex.join(command)
    fixture.set_routing(order, route)
    fixture.write_json(Path(paths["order"]), order)
    old_order.unlink()
    return paths


def input_for(paths: dict[str, Any]) -> dict[str, Any]:
    order = fixture.read_json(Path(paths["order"]))
    acceptance = Path(paths["namespace"]) / "controller-acceptance.json"
    return {
        "orderId": order["orderId"],
        "resultPath": str(paths["result"]),
        "resultSha256": sha256(Path(paths["result"])),
        "acceptancePath": str(acceptance),
        "acceptanceSha256": sha256(acceptance),
        "closurePath": str(paths["closure"]),
        "artifacts": [{"path": str(paths["test_count"]), "sha256": sha256(Path(paths["test_count"])), "mediaType": "text/markdown"}],
    }


def add_proof(paths: dict[str, Any], argv: list[str]) -> None:
    order = fixture.read_json(Path(paths["order"]))
    order["proofCommands"] = [{"argv": argv, "command": shlex.join(argv), "cwd": str(fixture.ROOT), "required": True}]
    fixture.write_json(Path(paths["order"]), order)


def accepted(paths: dict[str, Any]) -> dict[str, Any]:
    completed = fixture.run_gateway(paths)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    result = fixture.read_json(Path(paths["result"]))
    acceptance = fixture.read_json(Path(paths["namespace"]) / "controller-acceptance.json")
    assert result["status"] == "done"
    assert acceptance["status"] == "passed", acceptance
    assert sha256(Path(paths["result"])) == acceptance["canonicalResultSha256"]
    assert Path(paths["test_count"]).read_text(encoding="utf-8") == "launch\n"
    return acceptance


def assert_no_launch(paths: dict[str, Any]) -> None:
    completed = fixture.run_gateway(paths)
    assert completed.returncode != 0, completed.stdout
    assert "accepted input verification failed before launch" in completed.stderr, completed.stderr
    assert not Path(paths["test_count"]).exists()
    if paths["side_effect"] != Path("NONE"):
        assert not Path(paths["side_effect"]).exists()
    for key in ("candidate", "result", "start_receipt", "closure"):
        assert not Path(paths[key]).exists(), key


def main() -> int:
    if sys.flags.optimize:
        print("FAIL regression_accepted_inputs_gateway.py requires assertions", file=sys.stderr)
        return 1
    fixture.install_fake_executors()

    advisory = make_stage("input-chain-advisory", "advisory")
    accepted(advisory)
    advisory_input = input_for(advisory)
    implementation = make_stage("input-chain-implementation", "implementation", inputs=[advisory_input], product=True)
    fixture.set_lineage_order(implementation, Path(implementation["side_effect"]))
    accepted(implementation)
    implementation_input = input_for(implementation)
    implementation_anchor = Path(implementation["namespace"]) / "lineage-anchor.json"
    implementation_anchor_hash = sha256(implementation_anchor)
    verify_anchor(implementation_anchor, fixture.ROOT, expected_sha256=implementation_anchor_hash)

    reviewer = make_stage("input-chain-review", "terminal_review", inputs=[implementation_input])
    fixture.set_lineage_order(
        reviewer, Path(implementation["side_effect"]), implementation_anchor, implementation_anchor_hash,
    )
    acceptance = accepted(reviewer)
    review_order = fixture.read_json(Path(reviewer["order"]))
    nested = verify_input_results(review_order, fixture.ROOT)
    assert nested[0]["orderId"] == implementation_input["orderId"]
    assert nested[0]["nested"][0]["orderId"] == advisory_input["orderId"]
    proof = fixture.read_json(Path(reviewer["namespace"]) / "controller-proof.json")
    assert proof["observedChecks"]["inputResults"] == nested
    review_anchor = Path(reviewer["namespace"]) / "lineage-anchor.json"
    verify_anchor(review_anchor, fixture.ROOT, expected_sha256=acceptance["lineageAnchorSha256"])
    assert fixture.read_json(Path(reviewer["result"]))["filesChanged"] == []
    assert Path(implementation["side_effect"]).read_text(encoding="utf-8") == "effect\n"
    print("PASS Gateway accepts Astra advisory -> Sol implementation -> independent Opus terminal review with nested inputResults and separate product lineage")

    for kind in ("acceptance", "artifact"):
        predecessor = make_stage(f"input-preflight-{kind}-advisory", "advisory")
        accepted(predecessor)
        successor = make_stage(f"input-preflight-{kind}-successor", "implementation", inputs=[input_for(predecessor)], product=True)
        target = Path(predecessor["namespace"]) / "controller-acceptance.json" if kind == "acceptance" else Path(predecessor["test_count"])
        target.write_bytes(target.read_bytes() + b"tampered\n")
        assert_no_launch(successor)
    print("PASS input acceptance or selected artifact tampering rejects before custody or child side effects")

    predecessor = make_stage("input-proof-drift-advisory", "advisory")
    accepted(predecessor)
    original_input_bytes = Path(predecessor["test_count"]).read_bytes()
    successor = make_stage("input-proof-drift-successor", "implementation", inputs=[input_for(predecessor)], product=True)
    add_proof(successor, [
        sys.executable, "-c",
        "from pathlib import Path; import sys; p=Path(sys.argv[1]); p.write_text(p.read_text()+'changed in proof\\n')",
        str(predecessor["test_count"]),
    ])
    completed = fixture.run_gateway(successor)
    assert completed.returncode != 0, completed.stdout
    result_path = Path(successor["result"])
    canonical_bytes = result_path.read_bytes()
    assert json.loads(canonical_bytes)["status"] == "done"
    terminal = fixture.read_json(Path(successor["namespace"]) / "controller-acceptance.json")
    assert terminal["status"] == "rejected" and "accepted input verification failed after proof" in terminal["reason"], terminal
    assert terminal["canonicalResultSha256"] == sha256(result_path)
    closure = fixture.read_json(Path(successor["closure"]))
    assert closure["canonicalResultSha256"] == terminal["canonicalResultSha256"]
    assert Path(successor["test_count"]).read_text(encoding="utf-8") == "launch\n"
    assert Path(successor["side_effect"]).read_text(encoding="utf-8") == "effect\n"
    retry = fixture.run_gateway(successor)
    assert retry.returncode != 0
    assert result_path.read_bytes() == canonical_bytes
    assert Path(successor["test_count"]).read_text(encoding="utf-8") == "launch\n"
    assert Path(successor["side_effect"]).read_text(encoding="utf-8") == "effect\n"
    Path(predecessor["test_count"]).write_bytes(original_input_bytes)
    retry_after_restoration = fixture.run_gateway(successor)
    assert retry_after_restoration.returncode != 0
    assert "already exists" in retry_after_restoration.stderr, retry_after_restoration.stderr
    assert result_path.read_bytes() == canonical_bytes
    assert Path(successor["test_count"]).read_text(encoding="utf-8") == "launch\n"
    assert Path(successor["side_effect"]).read_text(encoding="utf-8") == "effect\n"
    print("PASS post-launch input drift rejects acceptance, preserves canonical done bytes, and never replays product execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
