#!/usr/bin/env python3
"""Focused 3.0 admission/capture/no-replay proof using local fake CLIs."""
from __future__ import annotations

import copy
import contextlib
import errno
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from accepted_inputs import AcceptedInputError, verify_input_results
from agent_result_builder import native_result_schema
from response_envelope import MAX_CANDIDATE_BYTES, MAX_FRAME_BYTES, MAX_STDOUT_BYTES
from result_gateway import run_child
import result_gateway
import agent_result_builder
import regression_result_gateway as fixture


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gateway-v3-") as directory:
        root = Path(directory)
        cli = root / "codex"
        cli.write_text('''#!/usr/bin/env python3
import hashlib, json, sys
from pathlib import Path
order = json.loads(Path(sys.argv[-1]).read_bytes())
control = Path(order["launch"]["candidateJsonPath"]).parent
with (control / "launch-count").open("a") as stream: stream.write("launch\\n")
mode = order["context"][0].get("fixtureMode", "valid")
review = mode.startswith("review-")
product = control / "review.md" if review else Path(order["workspace"]["repoPath"]) / "product.txt"
with product.open("a") as stream: stream.write("effect\\n")
payload = {
"resultVersion":"AGENT_RESULT_JSON_V1", "orderId":order["orderId"], "executor":order["executor"], "status":"done",
"summary":"local bounded fixture", "filesChanged":[{"path":str(product),"action":"modified"}],
"artifacts":[{"path":str(product), "exists":True,"type":"fixture","note":"product",
"mediaType":"text/plain","sha256":hashlib.sha256(product.read_bytes()).hexdigest()}],
"proof":[{"command":"fixture", "cwd":str(product.parent),"status":"pass","exitCode":0,"summary":"fixture"}],
"selfReview":{"performed":True,"findings":[],"fixesApplied":[]},"scopeDeviations":[],"forbiddenPatternHits":[],
"remainingRisks":[],"questions":[],"errors":[],"stdoutSummary":"","stderrSummary":"",
"handoff":order["outputContract"]["handoff"]}
if review:
    payload["filesChanged"] = []
    if mode != "review-missing":
        verdict = mode.removeprefix("review-")
        binding = dict(order["context"][0]["reviewBinding"])
        if verdict == "stale": binding["productSnapshotSha256"] = "0" * 64; verdict = "pass"
        payload["executorExtensions"] = {"review":dict(binding, verdict=verdict,
            findings=[{"criterion":"fixture criterion", "evidence":"fixture evidence"}] if verdict == "fail" else [])}
if mode == "wrong-order": payload["orderId"] = "different-order"
if mode == "failed": payload["status"] = "failed"
if mode == "oversized": raw = b"x" * (4*1024*1024+1)
elif mode == "malformed": raw = b"prose {not-json"
else: raw = json.dumps(payload).encode()
if order["executor"] == "claude":
    print(json.dumps({"type":"result","subtype":"success","is_error":False,"permission_denials":[],
        "structured_output":payload,"modelUsage":{"claude-opus-5-5":{"inputTokens":1}}}))
else: Path(order["launch"]["candidateJsonPath"]).write_bytes(raw)
''')
        cli.chmod(0o755)

        def stage(name: str, mode: str = "valid") -> dict:
            paths = fixture.make_case("v3-" + name, "valid")
            order = fixture.read_json(Path(paths["order"]))
            control = Path(paths["result"]).parent
            paths["order"] = control / "order.json"
            order["context"] = [{"policyVersion": "3.0", "fixtureMode": mode}]
            order["launch"]["candidateJsonPath"] = str(paths["candidate"])
            order["launch"]["command"] = shlex.join([str(cli), "exec", "--model", "gpt-6-luna", "-c",
                "model_reasoning_effort=medium", "--output-last-message", str(paths["candidate"]), str(paths["order"])])
            order["outputContract"]["handoff"] = {"version": "AGENT_HANDOFF_V1", "schemaId": "AGENT_RESULT_JSON_V1",
                "inReplyTo": order["orderId"], "senderRole": order["roleForTask"], "recipientRole": "Aquila"}
            fixture.write_json(Path(paths["order"]), order)
            return paths

        predecessor = None
        for mode in ("valid", "failed", "malformed", "wrong-order", "oversized"):
            paths = stage(mode, mode)
            completed = fixture.run_gateway(paths)
            control = Path(paths["result"]).parent
            if mode in ("valid", "failed"):
                assert Path(paths["result"]).exists(), completed.stderr + completed.stdout
                result = fixture.read_json(Path(paths["result"]))
                assert result["status"] == ("done" if mode == "valid" else "failed"), completed.stderr
                assert (completed.returncode == 0) == (mode == "valid"), completed.stderr + completed.stdout
                if mode == "valid":
                    acceptance = control / "controller-acceptance.json"
                    from hashlib import sha256
                    predecessor = {"orderId": result["orderId"], "resultPath": str(paths["result"]),
                        "resultSha256": sha256(Path(paths["result"]).read_bytes()).hexdigest(),
                        "acceptancePath": str(acceptance), "acceptanceSha256": sha256(acceptance.read_bytes()).hexdigest(),
                        "closurePath": str(paths["closure"]), "artifacts": []}
                    assert verify_input_results({"orderId": "successor-order", "inputResults": [predecessor]}, fixture.ROOT)
                    raw = Path(paths["stdout"])
                    original = raw.read_bytes()
                    raw.write_bytes(original + b"tampered")
                    try:
                        verify_input_results({"orderId": "successor-order", "inputResults": [predecessor]}, fixture.ROOT)
                    except AcceptedInputError as exc:
                        assert "capture digest" in str(exc)
                    else:
                        raise AssertionError("accepted input must retain original capture binding")
                    raw.write_bytes(original)
            else:
                assert completed.returncode != 0, completed.stdout
                assert not Path(paths["result"]).exists(), completed.stderr
                receipt = fixture.read_json(Path(paths["evidence"]) / "protocol-failure.json")
                closure = fixture.read_json(Path(paths["closure"]))
                assert receipt["canonicalFinalized"] is False and closure["canonicalFinalized"] is False
                assert receipt["launchBinding"]["runId"] == closure["runId"]
                assert not (control / "controller-acceptance.json").exists()
                assert receipt["reportRecovery"]["productReplayAllowed"] is False
                assert receipt["candidate"]["complete"] == (mode != "oversized")
                assert receipt["candidate"]["bytes"] <= MAX_CANDIDATE_BYTES
            replay = fixture.run_gateway(paths)
            assert replay.returncode != 0
            assert (control / "launch-count").read_text() == "launch\n"
        print("PASS 3.0 valid/failed author output, malformed/identity/oversize protocol receipts, raw input binding and zero product replay")

        native = stage("native-codex")
        order = fixture.read_json(Path(native["order"]))
        schema_path = Path(native["result"]).parent / "native-schema.json"
        fixture.write_json(schema_path, native_result_schema(order))
        order["launch"]["command"] += " --output-schema " + shlex.quote(str(schema_path))
        # Keep the one prompt last for this fake CLI, as in real initial exec.
        argv = shlex.split(order["launch"]["command"])
        argv[-3], argv[-2], argv[-1] = argv[-2], argv[-1], argv[-3]
        order["launch"]["command"] = shlex.join(argv)
        fixture.write_json(Path(native["order"]), order)
        completed = fixture.run_gateway(native)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        print("PASS Codex accepts the generated canonical --output-schema projection")

        for name, mutate in (
            ("prose-policy", lambda o: o["outputContract"].update(proseAllowedAfterJson=True)),
            ("wrong-ingress", lambda o: o.update(orderVersion="LEGION_ORDER_V1")),
            ("stale-handoff", lambda o: o["outputContract"]["handoff"].update(inReplyTo="stale-order")),
            ("unsupported-transport", lambda o: o["outputContract"].update(acceptedTransports=["xml"])),
            ("stdin", lambda o: o["launch"].update(stdinProvided=True)),
            ("env", lambda o: o["launch"].update(env={"SYNTHETIC_SECRET": "marker"})),
            ("missing-prompt", lambda o: o["launch"].update(command=shlex.join(shlex.split(o["launch"]["command"])[:-1]))),
            ("stale-schema", lambda o: o["launch"].update(command=o["launch"]["command"] + " --output-schema " + str(root / "stale-schema.json"))),
        ):
            (root / "stale-schema.json").write_text('{}')
            paths = stage(name)
            order = fixture.read_json(Path(paths["order"]))
            mutate(order)
            fixture.write_json(Path(paths["order"]), order)
            completed = fixture.run_gateway(paths)
            assert completed.returncode != 0, name
            assert not (Path(paths["result"]).parent / "launch-count").exists(), name
            assert not Path(paths["start_receipt"]).exists(), name
        print("PASS wrong ingress/identity/transport, missing prompt, env/stdin and stale native schema rejected before child")

        claude = root / "claude"
        claude.write_bytes(cli.read_bytes())
        claude.chmod(0o755)
        for verdict in ("pass", "fail", "blocked", "missing", "stale"):
            paths = stage("review-" + verdict, "review-" + verdict)
            order = fixture.read_json(Path(paths["order"]))
            order.update(executor="claude", roleForTask="REVIEWER", riskLevel="medium", inputResults=[copy.deepcopy(predecessor)])
            binding = {"reviewedOrderId": predecessor["orderId"], "reviewedResultSha256": predecessor["resultSha256"],
                       "productSnapshotSha256": "2" * 64}
            order["context"][0]["reviewBinding"] = binding
            order["outputContract"]["handoff"]["senderRole"] = "REVIEWER"
            route = fixture.routing_metadata(order["orderId"], "claude", risk="medium", reasoningEffort="high",
                executionProfile="terminal_review", verificationProfile="V2", reviewer="none", terminalGate=True)
            fixture.set_routing(order, route)
            schema = native_result_schema(order, route)
            order["launch"]["command"] = shlex.join([str(claude), "-p", "--model", "claude-opus-5-5",
                "--fallback-model", "claude-opus-5", "--json-schema", json.dumps(schema), "--output-format", "json", str(paths["order"])])
            paths["candidate_source"] = "stdout"
            fixture.write_json(Path(paths["order"]), order)
            completed = fixture.run_gateway(paths)
            control = Path(paths["result"]).parent
            assert (completed.returncode == 0) == (verdict == "pass"), completed.stderr + completed.stdout
            if verdict in ("missing", "stale"):
                assert not Path(paths["result"]).exists()
                assert (Path(paths["evidence"]) / "protocol-failure.json").exists()
            else:
                result = fixture.read_json(Path(paths["result"]))
                assert result["status"] == "done" and result["executorExtensions"]["review"]["verdict"] == verdict
                acceptance = fixture.read_json(control / "controller-acceptance.json")
                assert acceptance["status"] == ("passed" if verdict == "pass" else "rejected")
                extraction = fixture.read_json(Path(paths["closure"]))["candidate"]["extraction"]
                assert extraction["field"] == "structured_output" and extraction["eventIndex"] == 0
        print("PASS native Claude review pass/fail/blocked, missing verdict and stale snapshot binding; done alone cannot authorize acceptance")

        paths = stage("receipt-enospc", "malformed")
        original_finalize = agent_result_builder.create_only_finalize
        def fail_receipt(path, payload):
            if path.name == "protocol-failure.json":
                raise OSError(errno.ENOSPC, "fixture receipt disk full")
            return original_finalize(path, payload)
        with patch.object(sys, "argv", fixture.gateway_command(paths)[1:]), patch.dict(os.environ, fixture.environment(), clear=True), \
             patch.object(agent_result_builder, "create_only_finalize", side_effect=fail_receipt), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert result_gateway.main() != 0
        assert not Path(paths["result"]).exists()
        assert Path(paths["start_receipt"]).exists()
        assert list(Path(paths["evidence"]).glob("*.candidate-result.bin"))
        assert not (Path(paths["result"]).parent / "controller-acceptance.json").exists()
        assert fixture.run_gateway(paths).returncode != 0
        assert (Path(paths["result"]).parent / "launch-count").read_text() == "launch\n"
        print("PASS ENOSPC receipt failure preserves raw/start custody, rejects acceptance and restart replay")

        # Exercise bounded live reads without allocating an unbounded pipe buffer.
        child = run_child([sys.executable, "-c", "import os; [os.write(1,b'x'*65535+b'\\n') for _ in range(272)]"], root, 5, .1)
        assert child["captureLimited"] is True and len(child["stdout"]) == MAX_STDOUT_BYTES, child
        child = run_child([sys.executable, "-c", "import os; os.write(1,b'x'*(5*1024*1024))"], root, 5, .1,
                          detect_claude_tool_loop=True)
        assert child["captureLimited"] is True and len(child["stdout"]) <= MAX_FRAME_BYTES + 65536
        print("PASS streaming byte and newline-free JSONL frame limits terminate with partial capture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
