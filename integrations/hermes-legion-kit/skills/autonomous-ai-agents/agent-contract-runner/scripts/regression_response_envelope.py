#!/usr/bin/env python3
"""Proof for compatible response ingress, evidence binding, and direct adapters."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_contract_runner import PathPolicy, RunnerError, direct_response_paths, validate_order, verify_result
from agent_result_builder import BuilderError, build_result
from response_envelope import ResponseEnvelopeError, parse_response_bytes, validate_handoff_order, validate_response_handoff
from result_gateway import extract_stdout_candidate


SCRIPTS = Path(__file__).resolve().parent


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def rejects(action, text=""):
    try:
        action()
    except (ResponseEnvelopeError, RunnerError, BuilderError) as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError("expected rejection")


def fixture(root, name):
    repo = root / name
    repo.mkdir()
    order_id = f"response-{name}"
    control = repo / ".centurion" / "agents_results" / order_id
    control.mkdir(parents=True)
    artifact = repo / "product.txt"
    artifact.write_bytes(b"product\n")
    handoff = {"version": "AGENT_HANDOFF_V1", "schemaId": "AGENT_RESULT_JSON_V1", "inReplyTo": order_id, "senderRole": "CODER", "recipientRole": "Aquila"}
    order = {
        "orderVersion": "AGENT_ORDER_JSON_V1", "orderId": order_id,
        "createdAt": "2026-06-17T00:00:00Z", "controller": "Aquila", "executor": "hermes_delegate_task",
        "roleForTask": "CODER", "riskLevel": "low", "objective": "response contract proof",
        "workspace": {"repoPath": str(repo), "branchOrWorktree": "fixture", "projectName": "response-proof"},
        "launch": {"surface": "fixture", "command": "hermes_delegate_task", "timeoutSeconds": 10,
                   "resultJsonPath": str(control / "result.json"), "candidateJsonPath": str(control / "candidate.json")},
        "context": [], "allowedPaths": [str(repo / "**")], "forbiddenPaths": [], "forbiddenActions": [],
        "nonGoals": [], "acceptanceCriteria": ["validated result"], "expectedArtifacts": [],
        "proofCommands": [{"command": shlex.join([sys.executable, "-c", "pass"]), "cwd": str(repo), "required": True}],
        "outputContract": {"resultVersion": "AGENT_RESULT_JSON_V1", "resultPath": str(control / "result.json"),
                           "stdoutAllowed": False, "proseAllowedAfterJson": False, "handoff": handoff},
        "stopConditions": [], "notesForExecutor": [],
    }
    payload = {
        "resultVersion": "AGENT_RESULT_JSON_V1", "orderId": order_id, "executor": order["executor"],
        "status": "done", "summary": "fixture", "filesChanged": [],
        "artifacts": [{"path": str(artifact), "exists": True, "type": "fixture", "note": "",
                       "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "mediaType": "text/plain"}],
        "proof": [{"command": "fixture", "cwd": str(repo), "status": "pass", "exitCode": 0, "summary": "fixture"}],
        "selfReview": {"performed": True, "findings": [], "fixesApplied": []},
        "scopeDeviations": [], "forbiddenPatternHits": [], "remainingRisks": [], "questions": [], "errors": [],
        "stdoutSummary": "", "stderrSummary": "", "handoff": handoff.copy(),
    }
    (control / "order.json").write_bytes(encoded(order))
    return order, payload, control, artifact


def main():
    raw = b'{"value": 1}\n'
    for content, transport, inner in ((raw, "raw_json", raw), (b" \n```json\n" + raw + b"```\n", "json_fence", raw[:-1]),
                                      (b"```json\r\n{}\r\n```\r\n", "json_fence", b"{}")):
        parsed = parse_response_bytes(content)
        assert parsed.raw_bytes == content and parsed.normalized_bytes == inner and parsed.transport == transport
    for content in (b'prefix {}', b'{} suffix', b'{} {}', b'```json\n{}\n```\n```json\n{}\n```',
                    b'```JSON\n{}\n```', b'```\n{}\n```', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}',
                    b'{"a":', b'\xff', b'{"a":"\\ud800"}'):
        rejects(lambda: parse_response_bytes(content), "RESPONSE_FORMAT_ERROR")
    rejects(lambda: parse_response_bytes(b'```json\n{}\n```', allowed_transports=["raw_json"]), "RESPONSE_FORMAT_ERROR")
    print("PASS raw/fence/CRLF exact bytes and ambiguous, duplicate, nonfinite, UTF-8, surrogate, truncation rejection")

    with tempfile.TemporaryDirectory(prefix="response-envelope-regression-") as directory:
        root = Path(directory)
        order, payload, control, artifact = fixture(root, "binding")
        content = b'```json\n' + encoded(payload) + b'```\n'
        (control / "candidate.json").write_bytes(content)
        result = build_result(control / "order.json", control / "candidate.json", control / "result.json", control / "evidence")
        _, policy = validate_order(order)
        verify_result(control / "result.json", order, policy)
        assert Path(result["responseEnvelope"]["rawEvidencePath"]).read_bytes() == content
        original_result = (control / "result.json").read_bytes()
        rejects(lambda: build_result(control / "order.json", control / "candidate.json", control / "result.json", control / "evidence"), "collision")
        for key in ("rawEvidencePath", "normalizedCandidatePath"):
            evidence = Path(result["responseEnvelope"][key])
            original = evidence.read_bytes()
            evidence.write_bytes(original + b" ")
            rejects(lambda: verify_result(control / "result.json", order, policy), "mismatch")
            evidence.write_bytes(original)
        changed = copy.deepcopy(result)
        changed["summary"] = "substituted"
        (control / "result.json").write_bytes(encoded(changed))
        rejects(lambda: verify_result(control / "result.json", order, policy), "candidate-to-result")
        (control / "result.json").write_bytes(original_result)
        artifact.write_bytes(b"changed after acceptance\n")
        rejects(lambda: verify_result(control / "result.json", order, policy), "artifact SHA-256 mismatch")
        print("PASS handoff, raw/normalized/canonical/artifact hash binding and create-only collision")

        for name, mutation, error in (
            ("identity", lambda p: p["handoff"].update(senderRole="Boss"), "RESPONSE_IDENTITY_ERROR"),
            ("refusal", lambda p: p.update(refusal="refused"), "RESPONSE_REFUSED"),
            ("incomplete", lambda p: p.update(status="incomplete"), "RESPONSE_INCOMPLETE"),
            ("badstatus", lambda p: p.update(status={}), "RESPONSE_SCHEMA_ERROR"),
            ("schema", lambda p: p.update(filesChanged="wrong"), "RESPONSE_SCHEMA_ERROR"),
        ):
            order, payload, control, _ = fixture(root, name)
            mutation(payload)
            content = encoded(payload)
            (control / "candidate.json").write_bytes(content)
            result = build_result(control / "order.json", control / "candidate.json", control / "result.json", control / "evidence")
            assert result["status"] == "failed" and any(error in entry for entry in result["errors"]), result
            assert Path(result["artifacts"][0]["path"]).read_bytes() == content
        print("PASS failed identity/schema/refusal/incomplete responses retain original evidence and error codes")

        order, payload, _, _ = fixture(root, "roles")
        order["outputContract"].pop("handoff")
        payload["handoff"]["senderRole"] = "Aquila"
        assert validate_response_handoff(payload, order)
        order["outputContract"]["handoff"] = {**payload["handoff"], "senderRole": "CODER", "objectiveId": "wrong"}
        assert validate_handoff_order(order, {"objectiveId": "expected"})
        control = Path(order["launch"]["resultJsonPath"]).parent
        target = control / "nested"
        target.mkdir()
        (control / "redirect").symlink_to(target, target_is_directory=True)
        order["launch"]["candidateJsonPath"] = str(control / "redirect" / "raw.json")
        policy = PathPolicy(Path(order["workspace"]["repoPath"]), order["allowedPaths"], [], order["orderId"])
        rejects(lambda: direct_response_paths(order, policy, control / "result.json", control / "events.jsonl"), "symlink")
        terminal = {"type": "result", "subtype": "success", "is_error": False, "permission_denials": [], "result": "\ud800"}
        candidate, errors = extract_stdout_candidate(encoded(terminal), order, None, None)
        assert candidate is None and any("Unicode" in entry or "UTF-8" in entry for entry in errors)
        for value, code in (({"type": "refusal", "refusal": "no"}, "RESPONSE_REFUSED"), ({"status": "incomplete"}, "RESPONSE_INCOMPLETE")):
            candidate, errors = extract_stdout_candidate(encoded(value), order, None, None)
            assert candidate is None and any(code in entry for entry in errors)
        print("PASS unsolicited role elevation, objective mismatch, and Claude inner surrogate fail closed")

        for executor in ("hermes_delegate_task", "agy"):
            for mode in ("fenced", "malformed"):
                order, payload, control, _ = fixture(root, f"direct-{executor}-{mode}")
                order["executor"] = payload["executor"] = executor
                order["launch"]["command"] = executor
                (control / "order.json").write_bytes(encoded(order))
                content = b'```json\n' + encoded(payload) + b'```\n' if mode == "fenced" else b'prefix ' + encoded(payload)
                source = control / "source.bin"
                source.write_bytes(content)
                count = control / "count.txt"
                bin_dir = control / "bin"
                bin_dir.mkdir()
                fake = bin_dir / executor
                fake.write_text("#!/usr/bin/env python3\nfrom pathlib import Path\n"
                                f"with Path({str(count)!r}).open('a') as stream: stream.write('effect\\n')\n"
                                f"Path({order['launch']['candidateJsonPath']!r}).write_bytes(Path({str(source)!r}).read_bytes())\n")
                fake.chmod(0o755)
                env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")}
                argv = [sys.executable, str(SCRIPTS / "agent_contract_runner.py"), "--order", str(control / "order.json"),
                        "--mode", "run", "--events", str(control / "events.jsonl"), "--result", str(control / "result.json")]
                completed = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20)
                assert (completed.returncode == 0) == (mode == "fenced"), completed.stderr + completed.stdout
                result_bytes = (control / "result.json").read_bytes()
                replay = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20)
                assert replay.returncode != 0 and count.read_text() == "effect\n"
                assert (control / "result.json").read_bytes() == result_bytes
        print("PASS direct Hermes/AGY candidate adapters accept fences, reject prose, never replay or overwrite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
