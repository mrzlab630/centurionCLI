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
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from accepted_inputs import AcceptedInputError, verify_input_results
from agent_result_builder import native_result_schema
from response_envelope import MAX_CANDIDATE_BYTES, MAX_FRAME_BYTES, MAX_STDOUT_BYTES
from result_gateway import run_child
import result_gateway
import agent_result_builder
import agent_contract_runner
from regression_agent_result_builder import assert_native_api_subset
from agent_contract_runner import initialize_mission, _mission_digest, workspace_snapshot, verify_workspace_diff, PathPolicy, RunnerError, complete_mission, mission_snapshot, validate_order
import regression_result_gateway as fixture


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gateway-v3-") as directory:
        root = Path(directory)
        cli = root / "codex"
        cli.write_text('''#!/usr/bin/env python3
import hashlib, json, os, sys, time
from pathlib import Path
order = json.loads(Path(sys.argv[-1]).read_bytes())
control = Path(order["launch"]["candidateJsonPath"]).parent
with (control / "launch-count").open("a") as stream: stream.write("launch\\n")
mode = order["context"][0].get("fixtureMode", "valid")
if mode in ("silent", "eof-silent", "cancel-silent"):
    os.write(1, b"started\\n"); os.write(2, b"notice\\n")
    if mode == "eof-silent": os.close(1); os.close(2)
    time.sleep(20 if mode == "cancel-silent" else 1.3)
review = mode.startswith("review-")
product = control / "review.md" if review else Path(order["context"][0]["productPath"])
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
if mode == "disclosed-risk":
    payload["remainingRisks"] = ["User accepted the declared local fixture risk"]
if review:
    payload["filesChanged"] = []
    captured_product = Path(order["context"][0]["productPath"])
    if mode == "review-mutation": captured_product.write_text("unauthorized change")
    payload["artifacts"].append({"path":str(captured_product),"exists":True,"type":"reviewed-product",
        "note":"captured product","mediaType":"text/plain","sha256":hashlib.sha256(captured_product.read_bytes()).hexdigest()})
    if mode != "review-missing":
        verdict = mode.removeprefix("review-")
        if verdict == "mutation": verdict = "pass"
        binding = dict(order["context"][0]["reviewBinding"])
        if verdict == "stale": binding["productSnapshotSha256"] = "0" * 64; verdict = "pass"
        payload["executorExtensions"] = {"review":dict(binding, verdict=verdict,
            findings=[{"criterion":"fixture criterion", "evidence":"fixture evidence"}] if verdict == "fail" else [])}
if mode == "wrong-order": payload["orderId"] = "different-order"
if mode == "failed": payload["status"] = "failed"
if mode == "oversized": raw = b"x" * (4*1024*1024+1)
elif mode == "malformed": raw = b"prose {not-json SYNTHETIC_SECRET_MARKER"
else: raw = json.dumps(payload).encode()
if mode == "canonical-collision":
    Path(order["outputContract"]["resultPath"]).write_bytes(raw)
if order["executor"] == "claude":
    terminal = {"type":"result","subtype":"success","is_error":False,"permission_denials":[],
        "structured_output":payload,"result":"Native textual companion is not a candidate", "modelUsage":{"claude-opus-5-5":{"inputTokens":1}}}
    events = []
    if "tool-warnings" in mode:
        terminal["permission_denials"] = [{"tool_name":"Read","tool_input":{"file_path":"denied-fixture.txt"}}]
        for index in range(4):
            events.extend([
                {"message":{"content":[{"type":"tool_use","name":"Read","id":str(index),"input":{"path":"same.txt"}}]}},
                {"message":{"content":[{"type":"tool_result","tool_use_id":str(index),"content":"Wasted call: file unchanged since your last read"}]},"tool_use_result":{"type":"file_unchanged"}}])
    if mode == "buffered-tool-warnings": print(json.dumps(events + [terminal]))
    else:
        for event in events: print(json.dumps(event), flush=True)
        if events: time.sleep(.15)
        print(json.dumps(terminal))
else: Path(order["launch"]["candidateJsonPath"]).write_bytes(raw)
''')
        cli.chmod(0o755)

        def stage(name: str, mode: str = "valid", *, profile="V0", original=None, capability=None, monitored=False, launch_budget=8, risk="low") -> dict:
            paths = fixture.make_case("v3-" + name, "valid")
            order = fixture.read_json(Path(paths["order"]))
            order["riskLevel"] = risk
            if monitored:
                order["launch"]["timeoutSeconds"] = None
            Path(paths["order"]).unlink()  # controller-owned order belongs in custody, not product workspace
            control = Path(paths["result"]).parent
            paths["order"] = control / "order.json"
            product = Path(paths["case"]) / "product.txt"
            state_path = Path(paths["case"]) / "mission-state.json"
            order["context"] = [{"policyVersion": "3.0", "fixtureMode": mode,
                "missionId": "mission-" + name, "approvalRef": "fixture-approved", "taskId": "task",
                "intentId": "product-1", "action": "product", "strategyId": "initial", "dependencyRevisions": {},
                "productPath": str(product)}]
            order["allowedPaths"] = [str(product), str(control / "**")]
            order["loopContract"] = {"loopId": "mission-" + name, "statePath": str(state_path)}
            proof = [sys.executable, "-c", "from pathlib import Path; assert Path(" + repr(str(product)) + ").is_file()"]
            order["proofCommands"] = [{"command": shlex.join(proof), "argv": proof, "cwd": str(fixture.ROOT), "required": True}]
            route = fixture.routing_metadata(order["orderId"], "codex", verificationProfile=profile,
                risk=risk, model="gpt-6.1-sol" if risk == "high" else "gpt-6-luna",
                reasoningEffort="xhigh" if risk == "high" else "high",
                reviewer="none" if profile == "V0" else "claude-opus-5-5",
                reasons=["exact bounded oracle"] if profile == "V0" else ["promotion: independent verification required"],
                trustPredicates={key: True for key in ("localNarrowBlastRadius", "cheapReversal", "deterministicFailureOracle", "noSensitiveOrExternalSideEffects", "requiredArtifactsPass", "requiredProofsPass", "noUncertainty", "noScopeOrAssumptionIssues")})
            if risk == "high":
                route["trustPredicates"] = dict.fromkeys(route["trustPredicates"], False)
            fixture.set_routing(order, route)
            if original is not None:
                prior = fixture.read_json(Path(original["order"]))
                state = fixture.read_json(Path(prior["loopContract"]["statePath"]))
                candidate = state["intents"]["product-1"]
                product = Path(candidate["snapshot"]["files"][0]["path"])
                order["context"][0].update(prior["context"][0], fixtureMode=mode, action="review", intentId="review-1", candidateIntentId="product-1",
                    reviewBinding={"reviewedOrderId": prior["orderId"], "reviewedResultSha256": candidate["resultRef"]["sha256"],
                                   "productSnapshotSha256": candidate["snapshot"]["sha256"]})
                order["loopContract"] = prior["loopContract"]
                # A terminal reviewer is read-only, but it must be able to
                # inspect the exact captured product files it is reviewing.
                # Its own result/evidence remains confined to custody/**.
                order["allowedPaths"] = [str(product), str(control / "**")]
                order["proofCommands"] = []
            else:
                authority = {"approvalRef":"fixture-approved", "goal":order["objective"], "nonGoals":[], "criteria":order["acceptanceCriteria"],
                        "allowedActions":["product","review","report","advisory"], "allowedPaths":[str(product)], "forbiddenPaths":[]}
                if capability is not None:
                    authority["reportCapabilityRef"] = capability
                initialize_mission({"policyVersion":"3.0", "missionId":"mission-"+name, "workspace":str(fixture.ROOT), "strategyId":"initial",
                    "authority":authority,
                    "budget":{"maxModelLaunches":launch_budget, **({} if monitored else {"deadlineAt":(datetime.now(timezone.utc)+timedelta(seconds=300)).isoformat()})},
                    "tasks":{"task":{"objective":order["objective"], "acceptanceCriteria":order["acceptanceCriteria"], "allowedPaths":[str(product)],
                        "productPaths":[str(product)], "dependencies":[], "maxProductAttempts":3, "verificationProfile":profile,
                        "requiredProof":order["proofCommands"], "expectedArtifacts":[]}}}, state_path)
            order["launch"]["candidateJsonPath"] = str(paths["candidate"])
            order["launch"]["command"] = shlex.join([str(cli), "exec", "--model", route["model"], "-c",
                "model_reasoning_effort=" + route["reasoningEffort"], "--output-last-message", str(paths["candidate"]), str(paths["order"])])
            order["outputContract"]["handoff"] = {"version": "AGENT_HANDOFF_V1", "schemaId": "AGENT_RESULT_JSON_V1",
                "inReplyTo": order["orderId"], "senderRole": order["roleForTask"], "recipientRole": "Aquila"}
            fixture.write_json(Path(paths["order"]), order)
            return paths

        def monitored_command(paths):
            # Test-only observation clock acceleration; the real child lives
            # beyond the historical one-second launch timeout used below.
            command = fixture.gateway_command(paths)
            source = "import sys; sys.path.insert(0, " + repr(str(Path(result_gateway.__file__).parent)) + "); import result_gateway; result_gateway.CHILD_OBSERVATION_SECONDS=.05; raise SystemExit(result_gateway.main())"
            return [sys.executable, "-c", source, *command[2:]]

        for mode in ("silent", "eof-silent"):
            paths = stage("monitored-" + mode, mode, monitored=True)
            completed = subprocess.run(monitored_command(paths), env=fixture.environment(), capture_output=True, text=True, timeout=10)
            assert completed.returncode == 0, completed.stderr + completed.stdout
            events = [json.loads(line) for line in Path(paths["events"]).read_text().splitlines()]
            observations = [event for event in events if event["event"].endswith(".process_observed")]
            active = [event for event in observations if event["elapsedMs"] > 1050]
            assert len(observations) >= 3 and active and active[-1]["processAlive"] is True
            assert active[-1]["identityMatches"] is True and active[-1]["process"]["startTicks"]
            assert active[-1]["stdoutBytes"] == 8 and active[-1]["stderrBytes"] == 7
            assert active[-1]["lastOutputAt"] and active[-1]["silenceSeconds"] > 1
            assert all(event["productiveProgress"] == "unknown" and event["acceptance"] == "unverified" for event in observations)
            assert all(event["modelStatus"] == "unknown" and event["hangConfirmed"] is False for event in observations)
            assert any(event["diagnosis"] == "alive_active" for event in observations)
            assert any(event["diagnosis"] == "alive_waiting" for event in active)
            order = fixture.read_json(Path(paths["order"]))
            state = fixture.read_json(Path(order["loopContract"]["statePath"]))
            assert state["budget"]["deadlineAt"] is None and state["budget"]["modelLaunchesUsed"] == 1
            assert state["intents"]["product-1"]["processObservation"]
            assert fixture.run_gateway(paths).returncode == 0
            assert (Path(paths["result"]).parent / "launch-count").read_text() == "launch\n"
        print("PASS monitored real children survive one-second legacy timeout and EOF silence, emit periodic identity/activity evidence, and never replay")

        paths = stage("monitored-default-events", monitored=True)
        command = monitored_command(paths)
        offset = command.index("--events")
        del command[offset:offset+2]
        completed = subprocess.run(command, env=fixture.environment(), capture_output=True, text=True, timeout=10)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        derived_events = Path(paths["result"]).parent / "events.jsonl"
        assert any(json.loads(line)["event"].endswith(".process_observed") for line in derived_events.read_text().splitlines())
        print("PASS monitored Gateway derives existing controller events surface when --events is omitted")

        owner_selected = stage("owner-selected-risk", "disclosed-risk", monitored=True, risk="high")
        completed = fixture.run_gateway(owner_selected)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        owner_order = fixture.read_json(Path(owner_selected["order"]))
        owner_state = fixture.read_json(Path(owner_order["loopContract"]["statePath"]))
        assert owner_state["intents"]["product-1"]["status"] == "accepted"
        assert fixture.read_json(Path(owner_selected["result"]))["remainingRisks"]
        assert "USER_RISK_DECISION" in completed.stderr
        warnings = [json.loads(row) for row in Path(owner_selected["events"]).read_text().splitlines()
                    if json.loads(row)["event"].endswith(".risk_warning")]
        assert len(warnings) == 1 and warnings[0]["severity"] == "warning"
        assert fixture.run_gateway(owner_selected).returncode == 0
        assert sum(json.loads(row)["event"].endswith(".risk_warning")
                   for row in Path(owner_selected["events"]).read_text().splitlines()) == 1
        assert (Path(owner_selected["result"]).parent / "launch-count").read_text() == "launch\n"
        # Even for a high-risk label, authorization must remain the exact user's
        # mission authority; a worker cannot expand that authority itself.
        unauthorized = stage("owner-authority-mismatch", monitored=True, risk="high")
        denied_order = fixture.read_json(Path(unauthorized["order"]))
        denied_order["context"][0]["approvalRef"] = "different-owner-decision"
        fixture.write_json(Path(unauthorized["order"]), denied_order)
        rejected = fixture.run_gateway(unauthorized)
        assert rejected.returncode != 0
        assert not (Path(unauthorized["result"]).parent / "launch-count").exists()
        # Compatibility: old V3 tasks reach normal capture/review, rather than
        # failing because an unavailable approval-verifier service is absent.
        legacy_v3 = stage("owner-legacy-v3", profile="V3", monitored=True, risk="high")
        captured = fixture.run_gateway(legacy_v3)
        assert captured.returncode == 0 and '"status": "awaiting_review"' in captured.stdout, captured.stderr + captured.stdout
        print("PASS user-selected high-risk V0 accepts truthful risk disclosure; mismatched authority denies before launch; historical V3 reaches selected review")

        for stop_signal in (signal.SIGTERM, signal.SIGINT):
            paths = stage("monitored-cancel-" + stop_signal.name, "cancel-silent", monitored=True)
            process = subprocess.Popen(monitored_command(paths), env=fixture.environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            order = fixture.read_json(Path(paths["order"]))
            state_path = Path(order["loopContract"]["statePath"])
            try:
                until = time.monotonic() + 5
                while time.monotonic() < until:
                    state = fixture.read_json(state_path)
                    intent = state["intents"].get("product-1", {})
                    if intent.get("processObservation", {}).get("processAlive") and intent["processObservation"]["lastOutputAt"]:
                        break
                    assert process.poll() is None
                    time.sleep(.01)
                else:
                    raise AssertionError("real monitored child was not observed")
                child_identity = intent["process"]
                locked = fixture.run_gateway(paths)
                assert locked.returncode != 0 and "already held" in locked.stderr
                process.send_signal(stop_signal)
                stdout, stderr = process.communicate(timeout=5)
                assert process.returncode != 0, stdout + stderr
                state = fixture.read_json(state_path)
                assert state["cancelled"] is True and state["status"] == "stopped"
                assert result_gateway._mission_process_identity(child_identity["pid"]) is None
                assert state["budget"]["deadlineAt"] is None and state["budget"]["modelLaunchesUsed"] == 1
                assert not Path(paths["result"]).exists()
                assert fixture.run_gateway(paths).returncode != 0
                assert (Path(paths["result"]).parent / "launch-count").read_text() == "launch\n"
            finally:
                if process.poll() is None:
                    process.kill(); process.wait(timeout=3)
        print("PASS SIGTERM/SIGINT cancel active silent children while the transaction lock is held; bounded owned-process stop and no replay")

        for mode in ("launch-timeout", "mission-deadline"):
            paths = stage("finite-" + mode, "silent", monitored=mode == "mission-deadline")
            order = fixture.read_json(Path(paths["order"]))
            state_path = Path(order["loopContract"]["statePath"])
            state = fixture.read_json(state_path)
            if mode == "launch-timeout":
                order["launch"]["timeoutSeconds"] = 1
                fixture.write_json(Path(paths["order"]), order)
            else:
                state["budget"].update(deadlineAt=(datetime.now(timezone.utc) + timedelta(seconds=31.1)).isoformat(),
                                       startedAt=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
                fixture.write_json(state_path, state)
            deadline = state["budget"]["deadlineAt"]
            completed = subprocess.run(monitored_command(paths), env=fixture.environment(), capture_output=True, text=True, timeout=10)
            assert completed.returncode != 0 and not Path(paths["result"]).exists(), completed.stderr + completed.stdout
            state = fixture.read_json(state_path)
            assert state["budget"]["deadlineAt"] == deadline and state["budget"]["modelLaunchesUsed"] == 1, (mode, state, completed.stderr)
            assert state["intents"]["product-1"]["processStopped"] is True
            assert fixture.run_gateway(paths).returncode != 0
            assert (Path(paths["result"]).parent / "launch-count").read_text() == "launch\n"
        print("PASS explicit finite launch timeout and historical mission deadline still stop real children without changing authority or replaying")

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
            assert (replay.returncode == 0) == (mode == "valid"), replay.stderr
            assert (control / "launch-count").read_text() == "launch\n"
        print("PASS 3.0 valid/failed author output, malformed/identity/oversize protocol receipts, raw input binding and zero product replay")

        # Reproduce a worker following a stale file-output instruction: the
        # otherwise valid payload occupies the Gateway-owned canonical path.
        collision = stage("canonical-collision", "canonical-collision")
        completed = fixture.run_gateway(collision)
        assert completed.returncode != 0, completed.stdout
        control = Path(collision["result"]).parent
        canonical = Path(collision["result"])
        original_bytes = canonical.read_bytes()
        original_stat = canonical.stat()
        assert original_bytes == Path(collision["candidate"]).read_bytes()
        assert "responseEnvelope" not in json.loads(original_bytes)
        closure = fixture.read_json(Path(collision["closure"]))
        receipt = fixture.read_json(Path(collision["evidence"]) / "protocol-failure.json")
        assert any("result path collision" in error for error in closure["controllerErrors"])
        assert closure["canonicalFinalized"] is False and receipt["canonicalFinalized"] is False
        assert receipt["reportRecovery"]["productReplayAllowed"] is False
        order = fixture.read_json(Path(collision["order"]))
        state_path = Path(order["loopContract"]["statePath"])
        state = fixture.read_json(state_path)
        assert state["intents"]["product-1"]["status"] == "reportable"
        assert state["intents"]["product-1"]["processStopped"] is True
        assert state["tasks"]["task"]["status"] != "accepted"
        assert state["budget"]["modelLaunchesUsed"] == 1
        assert state["tasks"]["task"]["productAttemptsUsed"] == 1
        product = Path(order["context"][0]["productPath"])
        product_bytes = product.read_bytes()
        saved_state = state_path.read_bytes()
        assert fixture.run_gateway(collision).returncode != 0
        assert state_path.read_bytes() == saved_state
        assert canonical.read_bytes() == original_bytes and product.read_bytes() == product_bytes
        assert (canonical.stat().st_ino, canonical.stat().st_mtime_ns) == (original_stat.st_ino, original_stat.st_mtime_ns)
        assert not (control / "controller-acceptance.json").exists()
        assert (control / "launch-count").read_text() == "launch\n"
        print("PASS worker-written canonical result rejected and preserved, no acceptance or product replay on restart")

        native = stage("native-codex")
        order = fixture.read_json(Path(native["order"]))
        schema_path = Path(native["result"]).parent / "native-schema.json"
        projected_schema = native_result_schema(order)
        assert_native_api_subset(projected_schema)
        fixture.write_json(schema_path, projected_schema)
        order["launch"]["command"] += " --output-schema " + shlex.quote(str(schema_path))
        # Keep the one prompt last for this fake CLI, as in real initial exec.
        argv = shlex.split(order["launch"]["command"])
        argv[-3], argv[-2], argv[-1] = argv[-2], argv[-1], argv[-3]
        order["launch"]["command"] = shlex.join(argv)
        fixture.write_json(Path(native["order"]), order)
        completed = fixture.run_gateway(native)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        print("PASS Codex fake CLI accepts the bound --output-schema projection after explicit recursive API-subset validation")

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

        paths = stage("missing-evidence-directory")
        Path(paths["evidence"]).rmdir()
        completed = fixture.run_gateway(paths)
        assert completed.returncode != 0 and "evidence directory does not exist" in completed.stderr
        order = fixture.read_json(Path(paths["order"]))
        state = fixture.read_json(Path(order["loopContract"]["statePath"]))
        intent = state["intents"]["product-1"]
        assert intent["status"] == "rejected" and intent["effect"] == "not_started" and intent["processStopped"] is True
        assert state["budget"]["modelLaunchesUsed"] == 1
        assert not Path(paths["start_receipt"]).exists() and not (Path(paths["result"]).parent / "launch-count").exists()
        replay = fixture.run_gateway(paths)
        assert replay.returncode != 0 and fixture.read_json(Path(order["loopContract"]["statePath"]))["budget"]["modelLaunchesUsed"] == 1
        print("PASS pre-spawn custody error is known not-started, with spent budget retained and no implicit replay")

        claude = root / "claude"
        claude.write_bytes(cli.read_bytes())
        claude.chmod(0o755)
        for mode in ("tool-warnings", "buffered-tool-warnings"):
            paths = stage(mode, mode, monitored=True)
            order = fixture.read_json(Path(paths["order"]))
            order["executor"] = "claude"
            route = fixture.routing_metadata(order["orderId"], "claude", verificationProfile="V0",
                reviewer="none", reasoningEffort="high")
            fixture.set_routing(order, route)
            order["launch"]["command"] = shlex.join([str(claude), "-p", "--model", "claude-opus-5-5",
                "--effort", "high", "--json-schema", json.dumps(native_result_schema(order, route)),
                "--output-format", "stream-json" if mode == "tool-warnings" else "json", str(paths["order"])])
            paths["candidate_source"] = "stdout"
            fixture.write_json(Path(paths["order"]), order)
            completed = fixture.run_gateway(paths)
            assert completed.returncode == 0, completed.stderr + completed.stdout
            assert (Path(paths["result"]).parent / "controller-acceptance.json").exists()
            events_before = Path(paths["events"]).read_bytes()
            warnings = [json.loads(line) for line in events_before.splitlines() if b'"runtime_warning"' in line or b'.runtime_warning"' in line]
            assert {row["code"] for row in warnings} == {"CLAUDE_TOOL_PROGRESS", "CLAUDE_PERMISSION_DENIALS"}
            assert len(warnings) == 2 and all(row["approvalRef"] == "fixture-approved" for row in warnings)
            assert completed.stderr.count("WARNING CLAUDE_TOOL_PROGRESS:") == 1
            replay = fixture.run_gateway(paths)
            assert replay.returncode == 0 and "WARNING" not in replay.stderr
            assert Path(paths["events"]).read_bytes() == events_before
            assert (Path(paths["result"]).parent / "launch-count").read_text() == "launch\n"
        print("PASS streamed/buffered repeated reads and historical denied requests warn once, accept proven work and never replay")

        for verdict in ("pass", "fail", "blocked", "missing", "stale", "mutation"):
            original = stage("candidate-"+verdict, profile="V2")
            pending = fixture.run_gateway(original)
            assert pending.returncode == 0 and 'awaiting_review' in pending.stdout, pending.stderr + pending.stdout
            assert not (Path(original["result"]).parent / "controller-acceptance.json").exists()
            paths = stage("review-" + verdict, "review-" + verdict, original=original)
            order = fixture.read_json(Path(paths["order"]))
            order.update(executor="claude", roleForTask="REVIEWER", riskLevel="medium")
            order["outputContract"]["handoff"]["senderRole"] = "REVIEWER"
            route = fixture.routing_metadata(order["orderId"], "claude", risk="medium", reasoningEffort="high",
                executionProfile="terminal_review", verificationProfile="V2", reviewer="none", terminalGate=True)
            fixture.set_routing(order, route)
            schema = native_result_schema(order, route)
            assert_native_api_subset(schema)
            order["launch"]["command"] = shlex.join([str(claude), "-p", "--model", "claude-opus-5-5",
                "--effort", "high", "--json-schema", json.dumps(schema), "--output-format", "json", str(paths["order"])])
            paths["candidate_source"] = "stdout"
            fixture.write_json(Path(paths["order"]), order)
            completed = fixture.run_gateway(paths)
            control = Path(paths["result"]).parent
            assert (completed.returncode == 0) == (verdict == "pass"), completed.stderr + completed.stdout
            if verdict == "mutation":
                state = fixture.read_json(Path(order["loopContract"]["statePath"]))
                candidate = state["intents"]["product-1"]
                current = mission_snapshot(state, ["task"])
                assert current != candidate["snapshot"], "fixture must mutate the captured product"
                assert state["intents"]["review-1"]["status"] == "unknown_effect"
                assert state["tasks"]["task"]["status"] != "accepted"
            elif verdict in ("missing", "stale"):
                assert not Path(paths["result"]).exists()
                assert (Path(paths["evidence"]) / "protocol-failure.json").exists()
            else:
                result = fixture.read_json(Path(paths["result"]))
                assert result["status"] == "done" and result["executorExtensions"]["review"]["verdict"] == verdict
                if verdict in {"fail", "blocked"}:
                    review_order = fixture.read_json(Path(paths["order"]))
                    state = fixture.read_json(Path(review_order["loopContract"]["statePath"]))
                    assert state["intents"]["review-1"]["status"] == "rejected", state
                    assert state["intents"]["review-1"]["effect"] == "observed", state
                acceptance = fixture.read_json(control / "controller-acceptance.json")
                assert acceptance["status"] == ("passed" if verdict == "pass" else "rejected")
                extraction = fixture.read_json(Path(paths["closure"]))["candidate"]["extraction"]
                assert extraction["field"] == "structured_output" and extraction["eventIndex"] == 0
            if verdict == "pass":
                assert any(row["path"] == order["context"][0]["productPath"] for row in result["artifacts"])
                accepted = fixture.run_gateway(original)
                assert accepted.returncode == 0 and 'accepted' in accepted.stdout, accepted.stderr + accepted.stdout
                assert (Path(original["result"]).parent / "launch-count").read_text() == "launch\n"
                state = fixture.read_json(Path(order["loopContract"]["statePath"]))
                assert state["budget"]["modelLaunchesUsed"] == 2 and state["tasks"]["task"]["productAttemptsUsed"] == 1
                duplicate = fixture.run_gateway(paths)
                assert duplicate.returncode == 0, duplicate.stderr + duplicate.stdout
                assert (control / "launch-count").read_text() == "launch\n"
                assert fixture.read_json(Path(order["loopContract"]["statePath"])) == state
        print("PASS native Claude review pass/fail/blocked, missing verdict and stale snapshot binding; done alone cannot authorize acceptance")

        # Exact no-tools report adapter: only the controller's allowlisted projection
        # is visible to this deterministic fake CLI, including on restart collection.
        report_cli = root / "report" / "claude"
        report_cli.parent.mkdir()
        report_cli.write_text('''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
args=sys.argv[1:]
for flag,value in [("--tools",""),("--mcp-config",'{"mcpServers":{}}'),("--setting-sources","")]:
 assert args[args.index(flag)+1]==value
assert "--bare" in args and "--strict-mcp-config" in args
assert args[args.index("--model")+1]=="claude-opus-5-5"
assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in os.environ
assert "SYNTHETIC_SECRET_MARKER" not in sys.argv[-1]
scratch=Path(os.environ["CLAUDE_CONFIG_DIR"])
assert scratch==Path.cwd() and all(os.environ[key]==str(scratch) for key in ("HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_CACHE_HOME"))
(scratch/"debug").mkdir(); (scratch/"debug"/"native.log").write_text("native debug scratch\\n")
(scratch/".claude.json").write_text(json.dumps({"numStartups":1,"firstStartTime":"fixture","projects":{}}))
p=json.loads(sys.argv[-1]); row=p["productSnapshot"]["files"][0]
counter=Path(__file__).with_name("count"); counter.write_text(counter.read_text()+"report\\n" if counter.exists() else "report\\n")
time.sleep(.25)
result={"resultVersion":"AGENT_RESULT_JSON_V1","orderId":p["order"]["orderId"],"executor":p["order"]["executor"],"status":"done",
"summary":"saved product", "filesChanged":p["filesChanged"],
"artifacts":p["artifacts"],
"proof":p["controllerProof"],"selfReview":{"performed":True,"findings":[],"fixesApplied":[]},"scopeDeviations":[],"forbiddenPatternHits":[],
"remainingRisks":[],"questions":[],"errors":[],"stdoutSummary":"","stderrSummary":"","handoff":p["handoff"]}
for artifact in result["artifacts"]:
 if artifact["path"].endswith(".txt"): artifact["mediaType"]="text/plain"
scenario=Path(__file__).with_name("scenario.json")
rule=json.loads(scenario.read_text()).get(p["order"]["orderId"],{}) if scenario.exists() else {}
attempt_file=Path(__file__).with_name(p["order"]["orderId"]+".count")
attempt=int(attempt_file.read_text())+1 if attempt_file.exists() else 1
attempt_file.write_text(str(attempt))
if attempt<=rule.get("invalidAttempts",0):
 result.pop("proof")
 result["summary"]="same invalid report" if rule.get("repeatInvalid") else "invalid report "+str(attempt)
print(json.dumps({"type":"result","subtype":"success","is_error":False,"permission_denials":[],"structured_output":result,"modelUsage":{"claude-opus-5-5":{"outputTokens":attempt}}}))
''')
        report_cli.chmod(0o755)
        settings = root / "settings.json"
        fixture.write_json(settings, {"disableAllHooks":True})
        isolated = root / "empty-config"
        isolated.mkdir()
        from agent_contract_runner import _mission_file_ref
        cap_path = root / "report-capability.json"
        assert not cap_path.is_relative_to(fixture.ROOT), "exercise shared controller capability outside product repo"
        fixture.write_json(cap_path, {"version":"CENTURION_NO_TOOLS_REPORT_V1", "cliRef":_mission_file_ref(report_cli),
            "configRef":_mission_file_ref(settings), "scratchDir":str(isolated),
            "route":{"executor":"claude","model":"claude-opus-5-5","effort":"high"},
            "probe":{"status":"passed","toolsDenied":True,"mcpDisabled":True,"hooksDisabled":True,"isolatedConfig":True,"productUnchanged":True}})
        recovery = stage("report-recovery", "malformed", capability=_mission_file_ref(cap_path), monitored=True)
        malformed = fixture.run_gateway(recovery)
        assert malformed.returncode != 0 and not Path(recovery["result"]).exists(), malformed.stderr
        # Interrupt before observation, then after real durable observation.
        # Both restarts must collect this same report without another turn.
        first_report_errors = io.StringIO()
        real_projection = result_gateway.report_projection
        real_run_child = result_gateway.run_child
        report_timeouts = []
        def accelerated_old_report_limit(argv, cwd, timeout, *args, **kwargs):
            if kwargs.get("reservation") is not None and kwargs["reservation"].meta["action"] == "report":
                report_timeouts.append(timeout)
                # An accidentally retained 120s cap becomes 0.1s here; the
                # actual report process remains silent for 0.25s.
                if timeout == 120:
                    timeout = .1
            return real_run_child(argv, cwd, timeout, *args, **kwargs)
        def legacy_projection(reservation):
            saved = real_projection(reservation)
            for artifact in saved["artifacts"]:
                artifact["mediaType"] = "application/octet-stream"
            return saved
        with patch.object(sys,"argv",fixture.gateway_command(recovery)[1:]+["--recover-report"]), \
             patch.dict(os.environ,fixture.environment(),clear=True), \
             patch.object(result_gateway,"CHILD_OBSERVATION_SECONDS",.05), \
             patch.object(result_gateway,"run_child",accelerated_old_report_limit), \
             patch.object(result_gateway,"report_projection",legacy_projection), \
             patch.object(result_gateway.MissionReservation,"observe_result",side_effect=OSError("fixture interruption after report capture")), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(first_report_errors):
            assert result_gateway.main() != 0
        assert report_timeouts == [None], "monitored report must not inherit a hidden 120s lifetime"
        report_observations = [json.loads(line) for line in Path(recovery["events"]).read_text().splitlines()]
        assert any(row["event"].endswith(".process_observed") and row["elapsedMs"] >= 150 and row["processAlive"] for row in report_observations)
        assert (isolated/"debug"/"native.log").is_file() and (isolated/".claude.json").is_file()
        # Recovery revalidates binary/settings/route and rejects new executable
        # config in scratch, but leaves saved custody collectable after removal.
        for filename, content in (("settings.local.json", {"hooks":{"Stop":[]}}),
                                  (".claude.json", {"mcpServers":{"injected":{"command":"false"}}}),
                                  ("plugins/injected.json", {})):
            target = isolated/filename
            saved = target.read_bytes() if target.exists() else None
            fixture.write_json(target, content)
            denied = subprocess.run(fixture.gateway_command(recovery)+["--recover-report"],env=fixture.environment(),text=True,capture_output=True)
            assert denied.returncode != 0 and (report_cli.parent/"count").read_text() == "report\n", denied.stderr
            if saved is None: target.unlink()
            else: target.write_bytes(saved)
            if target.parent != isolated: target.parent.rmdir()
        for target in (settings, report_cli):
            saved = target.read_bytes()
            target.write_bytes(saved+b"\n")
            denied = subprocess.run(fixture.gateway_command(recovery)+["--recover-report"],env=fixture.environment(),text=True,capture_output=True)
            assert denied.returncode != 0 and "changed since capability probe" in denied.stderr, denied.stderr
            target.write_bytes(saved)
        canonical = Path(recovery["result"])
        canonical_bytes = canonical.read_bytes()
        canonical_stat = canonical.stat()
        real_observe_result = result_gateway.MissionReservation.observe_result
        class ReportCaptureInterruption(BaseException):
            pass
        def interrupt_after_observation(reservation, *args, **kwargs):
            real_observe_result(reservation, *args, **kwargs)
            raise ReportCaptureInterruption("after durable report observation")
        with patch.object(sys,"argv",fixture.gateway_command(recovery)[1:]+["--recover-report"]), \
             patch.dict(os.environ,fixture.environment(),clear=True), \
             patch.object(result_gateway.MissionReservation,"observe_result",interrupt_after_observation), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                result_gateway.main()
            except ReportCaptureInterruption:
                pass
            else:
                raise AssertionError("durable report observation interruption was not reached")
        order = fixture.read_json(Path(recovery["order"]))
        captured_state = fixture.read_json(Path(order["loopContract"]["statePath"]))
        captured = captured_state["intents"]["product-1"]
        assert captured["status"] == "captured" and "verification" not in captured and "terminalTemplate" not in captured
        reservation = SimpleNamespace(intent=captured, state=captured_state, meta={"intentId":"product-1"})
        assert result_gateway._report_capture_resumable(reservation)
        report_id = captured.pop("reportIntentId")
        assert not result_gateway._report_capture_resumable(reservation), "generic captured product must not enter report recovery"
        captured["reportIntentId"] = report_id
        captured["verification"] = {}
        assert not result_gateway._report_capture_resumable(reservation), "verified capture must use normal resume"
        captured.pop("verification")
        report_namespace = canonical.parent/"report-1"
        report_stdout = report_namespace/"stdout.bin"
        report_candidate = report_namespace/"candidate.json"
        saved_stdout, saved_candidate = report_stdout.read_bytes(), report_candidate.read_bytes()
        native_wrapper = json.loads(saved_stdout)
        native_wrapper["result"] = "Unselected companion text must never override the native object"
        selected, errors = result_gateway.extract_stdout_candidate(json.dumps(native_wrapper).encode(), order, None, {"model":"claude-opus-5-5"}, native_override=True)
        assert not errors and json.loads(selected) == native_wrapper["structured_output"]
        _, errors = result_gateway.extract_stdout_candidate(json.dumps(native_wrapper).encode(), order, None, {"model":"claude-opus-5-5"}, native_override=False)
        assert errors, "text mode must reject unselected structured output"
        native_wrapper["result"] = json.dumps(native_wrapper.pop("structured_output"))
        _, errors = result_gateway.extract_stdout_candidate(json.dumps(native_wrapper).encode(), order, None, {"model":"claude-opus-5-5"}, native_override=True)
        assert errors, "native mode must not fall back to a valid text result"
        altered = json.loads(saved_stdout)
        altered["structured_output"]["summary"] = "different saved report"
        altered_stdout = json.dumps(altered).encode()
        altered_candidate, errors = result_gateway.extract_stdout_candidate(altered_stdout, order, None, {"model":"claude-opus-5-5"}, native_override=True)
        assert not errors and altered_candidate is not None
        report_stdout.write_bytes(altered_stdout); report_candidate.write_bytes(altered_candidate)
        denied = subprocess.run(fixture.gateway_command(recovery)+["--recover-report"],env=fixture.environment(),text=True,capture_output=True)
        assert denied.returncode != 0 and "canonical result differs from saved report candidate" in denied.stderr, denied.stderr
        report_stdout.write_bytes(saved_stdout); report_candidate.write_bytes(saved_candidate)
        collected = subprocess.run(fixture.gateway_command(recovery)+["--recover-report"],env=fixture.environment(),text=True,capture_output=True)
        assert collected.returncode == 0, "first="+first_report_errors.getvalue()+" second="+collected.stderr+collected.stdout
        assert '"status": "accepted"' in collected.stdout, collected.stdout
        assert canonical.read_bytes() == canonical_bytes
        assert (canonical.stat().st_ino, canonical.stat().st_mtime_ns) == (canonical_stat.st_ino, canonical_stat.st_mtime_ns)
        assert (report_cli.parent/"count").read_text() == "report\n"
        assert (Path(recovery["result"]).parent/"launch-count").read_text() == "launch\n"
        order = fixture.read_json(Path(recovery["order"]))
        state = fixture.read_json(Path(order["loopContract"]["statePath"]))
        assert state["budget"]["modelLaunchesUsed"] == 2 and state["tasks"]["task"]["productAttemptsUsed"] == 1
        assert state["intents"]["product-1"]["reportAttemptsUsed"] == 1
        facts = state["intents"]["product-1:report:1"]["projection"]
        reported = fixture.read_json(Path(recovery["result"]))
        assert facts["artifacts"][0]["mediaType"] == "application/octet-stream"
        assert reported["artifacts"][0]["mediaType"] == "text/plain"
        assert json.loads(saved_stdout)["structured_output"]["artifacts"] == reported["artifacts"]
        unchanged_facts, unchanged_report = copy.deepcopy(facts), copy.deepcopy(reported)
        result_gateway.validate_report_facts(reported, facts)
        assert facts == unchanged_facts and reported == unchanged_report
        binary_report = copy.deepcopy(reported)
        binary_report["artifacts"][0]["mediaType"] = "application/octet-stream"
        result_gateway.validate_report_facts(binary_report, facts)
        typed_facts = copy.deepcopy(facts)
        typed_facts["artifacts"][0]["mediaType"] = "text/plain"
        for description, bad_report, bound_facts in (
            ("unrelated media type", copy.deepcopy(reported), facts),
            ("changed concrete media type", binary_report, typed_facts),
        ):
            if description == "unrelated media type": bad_report["artifacts"][0]["mediaType"] = "image/png"
            try: result_gateway.validate_report_facts(bad_report, bound_facts)
            except result_gateway.GatewayError: pass
            else: raise AssertionError("report must reject " + description)
        assert result_gateway._report_media_type(Path("effect.txt")) == "text/plain"
        assert result_gateway._report_media_type(Path("effect.unknown_extension")) == "application/octet-stream"
        for field in ("filesChanged", "proof", "artifacts"):
            invented = copy.deepcopy(reported)
            if field == "filesChanged": invented[field][0]["action"] = "deleted"
            elif field == "proof": invented[field][0]["command"] = "invented successful check"
            else: invented[field][0]["sha256"] = "0" * 64
            try: result_gateway.validate_report_facts(invented, facts)
            except result_gateway.GatewayError: pass
            else: raise AssertionError("report-only inference must not invent " + field)
        from hashlib import sha256
        acceptance = Path(recovery["result"]).parent/"controller-acceptance.json"
        downstream = {"orderId":"recovery-consumer", "inputResults":[{"orderId":order["orderId"],"resultPath":str(recovery["result"]),
            "resultSha256":sha256(Path(recovery["result"]).read_bytes()).hexdigest(),"acceptancePath":str(acceptance),
            "acceptanceSha256":sha256(acceptance.read_bytes()).hexdigest(),"closurePath":str(recovery["closure"]),"artifacts":[]}]}
        projection = verify_input_results(downstream, fixture.ROOT)
        assert "SYNTHETIC_SECRET_MARKER" not in json.dumps(projection)
        cap_bytes = cap_path.read_bytes()
        cap_path.write_bytes(cap_bytes + b" ")
        try: verify_input_results(downstream, fixture.ROOT)
        except AcceptedInputError: pass
        else: raise AssertionError("external capability digest and length must stay pinned")
        cap_path.write_bytes(cap_bytes)
        cap_copy = root / "capability-copy.json"
        cap_copy.write_bytes(cap_bytes)
        cap_path.unlink(); cap_path.symlink_to(cap_copy)
        try: verify_input_results(downstream, fixture.ROOT)
        except AcceptedInputError: pass
        else: raise AssertionError("external capability symlink must be rejected even for identical bytes")
        cap_path.unlink(); cap_path.write_bytes(cap_bytes)
        assert verify_input_results(downstream, fixture.ROOT) == projection
        raw = Path(recovery["candidate"]).read_bytes()
        assert b"SYNTHETIC_SECRET_MARKER" in raw and Path(recovery["candidate"]).stat().st_mode & 0o777 == 0o600
        Path(recovery["candidate"]).write_bytes(raw+b"tamper")
        try: verify_input_results(downstream, fixture.ROOT)
        except AcceptedInputError: pass
        else: raise AssertionError("recovery must retain original malformed raw binding")
        Path(recovery["candidate"]).write_bytes(raw)
        print("PASS report recovery before/after durable observation, canonical create-only/candidate equality, two launches/one product/one report, downstream binding and restricted synthetic secret marker")

        def report_case(name, *, invalid=0, repeat=False, budget=8, capability=True, profile="V0"):
            cap_ref = None
            if capability:
                fresh = root / name
                fresh.mkdir()
                fresh_scratch = fresh / "scratch"
                fresh_scratch.mkdir()
                fresh_cap = fresh / "capability.json"
                fixture.write_json(fresh_cap, dict(fixture.read_json(cap_path), scratchDir=str(fresh_scratch)))
                cap_ref = _mission_file_ref(fresh_cap)
            case = stage(name, "malformed", capability=cap_ref, monitored=True, launch_budget=budget, profile=profile)
            case_order = fixture.read_json(Path(case["order"]))
            scenario_path = report_cli.with_name("scenario.json")
            rules = fixture.read_json(scenario_path) if scenario_path.exists() else {}
            rules[case_order["orderId"]] = {"invalidAttempts": invalid, "repeatInvalid": repeat}
            fixture.write_json(scenario_path, rules)
            initial = fixture.run_gateway(case)
            assert initial.returncode != 0 and not Path(case["result"]).exists(), initial.stderr
            return case

        def recover(case, *extra):
            return subprocess.run(fixture.gateway_command(case) + list(extra or ["--recover-report"]),
                                  env=fixture.environment(), text=True, capture_output=True)

        def state_for(case):
            order = fixture.read_json(Path(case["order"]))
            return order, Path(order["loopContract"]["statePath"]), fixture.read_json(Path(order["loopContract"]["statePath"]))

        def continuation(case, **updates):
            order, state_path, state = state_for(case)
            decision = Path(case["result"]).parent / f"continuation-{len(state.get('continuations', [])) + 1}.json"
            fixture.write_json(decision, {"version": "CENTURION_MISSION_CONTINUATION_V1", "missionId": state["missionId"],
                "approvalRef": state["authority"]["approvalRef"], "stateSha256": _mission_file_ref(state_path)["sha256"],
                "reason": "explicit fixture owner continuation", **updates})
            result = subprocess.run([sys.executable, str(Path(agent_contract_runner.__file__)), "--order", str(case["order"]),
                "--continue-mission", str(decision)], env=fixture.environment(), text=True, capture_output=True)
            assert result.returncode == 0, result.stderr
            return decision

        def verify_downstream(case):
            order = fixture.read_json(Path(case["order"]))
            acceptance = Path(case["result"]).parent / "controller-acceptance.json"
            return verify_input_results({"orderId": "consumer-" + order["orderId"], "inputResults": [{
                "orderId": order["orderId"], "resultPath": str(case["result"]), "resultSha256": _mission_file_ref(Path(case["result"]))["sha256"],
                "acceptancePath": str(acceptance), "acceptanceSha256": _mission_file_ref(acceptance)["sha256"],
                "closurePath": str(case["closure"]), "artifacts": []}]}, fixture.ROOT)

        fresh = stage("recovery-never-starts-product", "malformed", monitored=True)
        denied = recover(fresh)
        assert denied.returncode != 0 and "existing saved product" in denied.stderr, denied.stderr
        assert state_for(fresh)[2]["budget"]["modelLaunchesUsed"] == 0
        assert not (Path(fresh["result"]).parent / "launch-count").exists()

        repeated = report_case("multiple-report-corrections", invalid=2)
        corrected = recover(repeated)
        assert corrected.returncode == 0, corrected.stderr
        _, _, repeated_state = state_for(repeated)
        assert repeated_state["budget"]["modelLaunchesUsed"] == 4
        assert repeated_state["tasks"]["task"]["productAttemptsUsed"] == 1
        assert repeated_state["intents"]["product-1"]["reportAttemptsUsed"] == 3
        assert (Path(repeated["result"]).parent / "launch-count").read_text() == "launch\n"
        assert len(verify_downstream(repeated)) == 1
        assert recover(repeated).returncode == 0
        assert state_for(repeated)[2]["budget"]["modelLaunchesUsed"] == 4
        print("PASS three report attempts, one product effect, automatic corrections, restart idempotency and ordinal-bound downstream")

        no_progress = report_case("report-no-progress", invalid=10, repeat=True)
        rejected = recover(no_progress)
        assert rejected.returncode != 0 and "no progress" in rejected.stderr, rejected.stderr
        assert state_for(no_progress)[2]["budget"]["modelLaunchesUsed"] == 3
        assert not Path(no_progress["result"]).exists()
        assert recover(no_progress).returncode != 0
        assert state_for(no_progress)[2]["budget"]["modelLaunchesUsed"] == 3
        print("PASS identical invalid reports stop without product replay or consuming more launches on status retries")

        exhausted = report_case("report-budget-continuation", invalid=2, budget=3)
        blocked = recover(exhausted)
        assert blocked.returncode != 0 and "budget exhausted" in blocked.stderr, blocked.stderr
        _, _, exhausted_state = state_for(exhausted)
        assert exhausted_state["status"] == "blocked" and exhausted_state["budget"]["modelLaunchesUsed"] == 3
        decision = continuation(exhausted, maxModelLaunches=4)
        replay = subprocess.run([sys.executable, str(Path(agent_contract_runner.__file__)), "--order", str(exhausted["order"]),
            "--continue-mission", str(decision)], env=fixture.environment(), text=True, capture_output=True)
        assert replay.returncode != 0 and "current mission" in replay.stderr
        resumed = recover(exhausted)
        assert resumed.returncode == 0, resumed.stderr
        assert state_for(exhausted)[2]["budget"]["modelLaunchesUsed"] == 4
        assert state_for(exhausted)[2]["tasks"]["task"]["productAttemptsUsed"] == 1
        print("PASS recorded budget continuation preserves counters, rejects stale decision replay and finishes saved product")

        try:
            report_case("insufficient-recovery-budget", budget=1)
        except RunnerError as error:
            assert "report recovery reserve" in str(error), error
        else:
            raise AssertionError("enabled model recovery must reserve budget before product launch")

        def manual_candidate(case):
            order, _, saved = state_for(case)
            policy = PathPolicy(fixture.ROOT, order["allowedPaths"], order["forbiddenPaths"], order["orderId"])
            facts = result_gateway.report_projection(SimpleNamespace(order=order, intent=saved["intents"]["product-1"], policy=policy))
            candidate = {"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": order["orderId"], "executor": order["executor"],
                "status": "done", "summary": "independently checked saved product", "filesChanged": facts["filesChanged"],
                "artifacts": facts["artifacts"], "proof": facts["controllerProof"], "handoff": facts["handoff"],
                "selfReview": {"performed": True, "findings": [], "fixesApplied": []}, "scopeDeviations": [],
                "forbiddenPatternHits": [], "remainingRisks": [], "questions": [], "errors": [], "stdoutSummary": "", "stderrSummary": ""}
            candidate_path = Path(case["result"]).parent / "manual-candidate.json"
            review_path = candidate_path.with_name("manual-review.json")
            fixture.write_json(candidate_path, candidate)
            fixture.write_json(review_path, {"version": "CENTURION_MANUAL_PRODUCT_REVIEW_V1", "missionId": saved["missionId"],
                "orderId": order["orderId"], "orderSha256": saved["intents"]["product-1"]["orderRef"]["sha256"],
                "productSnapshotSha256": facts["productSnapshot"]["sha256"], "rawSha256": facts["rawSha256"],
                "candidateRef": _mission_file_ref(candidate_path), "criteria": order["acceptanceCriteria"],
                "reviewer": "fixture independent human reviewer", "verdict": "pass"})
            return candidate_path, review_path

        manual = report_case("manual-without-model-budget", budget=1, capability=False)
        candidate_path, review_path = manual_candidate(manual)
        denied = recover(manual, "--recover-report-from", str(candidate_path))
        assert denied.returncode != 0 and not Path(manual["result"]).exists()
        continuation(manual, manualReportReviewRef=_mission_file_ref(review_path))
        accepted = recover(manual, "--recover-report-from", str(candidate_path))
        assert accepted.returncode == 0, accepted.stderr
        _, _, manual_state = state_for(manual)
        assert manual_state["budget"]["modelLaunchesUsed"] == 1 and manual_state["tasks"]["task"]["productAttemptsUsed"] == 1
        assert manual_state["intents"]["product-1:report:1"]["modelLaunch"] is False
        assert len(verify_downstream(manual)) == 1
        assert recover(manual, "--recover-report-from", str(candidate_path)).returncode == 0
        review_bytes = review_path.read_bytes()
        review_path.write_bytes(review_bytes + b" ")
        try:
            verify_downstream(manual)
        except AcceptedInputError:
            pass
        else:
            raise AssertionError("downstream must retain exact manual review bytes")
        review_path.write_bytes(review_bytes)
        assert len(verify_downstream(manual)) == 1
        print("PASS authorized manual report without model capability or extra model budget, exact evidence and downstream custody")

        legacy = report_case("legacy-budget-failure-continuation", budget=1, capability=False)
        _, state_path, saved = state_for(legacy)
        saved.update(status="failed", failure="mission model-launch budget exhausted")
        fixture.write_json(state_path, saved)
        candidate_path, review_path = manual_candidate(legacy)
        continuation(legacy, manualReportReviewRef=_mission_file_ref(review_path))
        assert recover(legacy, "--recover-report-from", str(candidate_path)).returncode == 0
        assert state_for(legacy)[2]["budget"]["modelLaunchesUsed"] == 1
        print("PASS explicit legacy budget-failure continuation restores reporting without reopening or replaying product")

        needs_review = report_case("manual-keeps-review-floor", budget=2, capability=False, profile="V2")
        candidate_path, review_path = manual_candidate(needs_review)
        continuation(needs_review, manualReportReviewRef=_mission_file_ref(review_path))
        waiting = recover(needs_review, "--recover-report-from", str(candidate_path))
        assert waiting.returncode == 0 and '"status": "awaiting_review"' in waiting.stdout, waiting.stderr
        assert not (Path(needs_review["result"]).parent / "controller-acceptance.json").exists()
        print("PASS manual reporting preserves mandatory independent review instead of self-approving product")

        # Exercise actual filesystem denial without a provider or real profile.
        sandbox = shutil.which("bwrap")
        assert sandbox, "native-profile-readonly verification requires bwrap"
        native_home = root / "native-home"
        native_home.mkdir()
        for name in (".claude", ".codex", ".agents"):
            (native_home / name).mkdir()
        (native_home / "AGENTS.md").write_text("unloaded fixture")
        profile = native_home / ".claude.json"
        profile.write_text('{"syntheticNativeProfile":true}\n')
        scratch = root / "native-report-scratch"
        scratch.mkdir()
        denied_product = root / "native-denied-product.txt"
        denied_product.write_text("unchanged")
        native_cli = root / "native-claude"
        native_cli.write_text('''#!/usr/bin/env python3
import errno,json,os,sys
from pathlib import Path
scratch=Path(os.environ["CLAUDE_CONFIG_DIR"])
assert "--bare" not in sys.argv
assert "ANTHROPIC_API_KEY" not in os.environ and "ANTHROPIC_AUTH_TOKEN" not in os.environ
assert json.loads((scratch/".claude.json").read_text())=={"syntheticNativeProfile":True}
assert sys.argv[sys.argv.index("--model")+1]=="claude-opus-5-5"
assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in os.environ
(scratch/"observed.txt").write_text("scratch permitted")
try: Path(sys.argv[-1]).write_text("unauthorized")
except OSError as error: assert error.errno in (errno.EROFS,errno.EACCES)
else: raise AssertionError("product was writable")
print("READONLY_NATIVE_PROFILE_OK")
''')
        native_cli.chmod(0o755)
        native_cap = dict(fixture.read_json(cap_path), launchMode="native-profile-readonly",
                          cliRef=_mission_file_ref(native_cli), sandboxRef=_mission_file_ref(Path(sandbox)),
                          profileRef=_mission_file_ref(profile), nativeHome=str(native_home),
                          scratchDir=str(scratch), baseUrl="http://127.0.0.1:8317")
        native_cap_path=root/"native-report-capability.json"
        fixture.write_json(native_cap_path,native_cap)
        native_reservation=SimpleNamespace(state={"authority":{"reportCapabilityRef":_mission_file_ref(native_cap_path)}})
        result_gateway.report_capability(native_reservation)
        native_cli.chmod(0o644)
        try: result_gateway.report_capability(native_reservation)
        except result_gateway.GatewayError as error: assert "not executable" in str(error)
        else: raise AssertionError("nonexecutable report CLI must fail before reservation")
        native_cli.chmod(0o755)
        with patch.dict(os.environ, dict(fixture.environment(), ANTHROPIC_API_KEY="synthetic", ANTHROPIC_AUTH_TOKEN="synthetic"), clear=True):
            argv, env = result_gateway.report_launch(native_cap, {}, str(denied_product))
        outcome=subprocess.run(argv,env=env,text=True,capture_output=True,timeout=15)
        assert outcome.returncode==0 and outcome.stdout.strip()=="READONLY_NATIVE_PROFILE_OK", outcome.stderr
        assert denied_product.read_text()=="unchanged"
        result_gateway.report_capability(native_reservation)
        profile.write_text('{}\n')
        try: result_gateway.report_capability(native_reservation)
        except result_gateway.GatewayError: pass
        else: raise AssertionError("changed native profile must invalidate capability")
        print("PASS native-profile report preserves route, excludes injected credentials, denies product writes and pins profile")

        snapshot_root = root / "snapshot-git"
        snapshot_root.mkdir()
        subprocess.run(["git","init","-q",str(snapshot_root)],check=True)
        tracked = snapshot_root/"build/source.py"
        tracked.parent.mkdir(); tracked.write_text("tracked baseline\n")
        deleted = snapshot_root/"deleted.py"; deleted.write_text("tracked delete\n")
        renamed = snapshot_root/"renamed.py"; renamed.write_text("tracked rename\n")
        subprocess.run(["git","-C",str(snapshot_root),"add","build/source.py","deleted.py","renamed.py"],check=True)
        tracked.write_text("dirty before dispatch\n")
        foreign = snapshot_root/"foreign.txt"; foreign.write_text("pre-existing untracked\n")
        approved = snapshot_root/"dist/generated/product.py"
        approved.parent.mkdir(parents=True); approved.write_text("approved untracked\n")
        control = snapshot_root/".centurion/agents_results/test"; control.mkdir(parents=True)
        (control/"result.json").write_text("control\n")
        ignored = snapshot_root/"vendor/ignored.txt"; ignored.parent.mkdir(); ignored.write_text("generated\n")
        snapshot_state = {"workspace":str(snapshot_root),"statePath":str(control/"state.json"),
                          "tasks":{"task":{"productPaths":[str(approved)]}}}
        before = workspace_snapshot(snapshot_state)
        assert str(tracked) in before and str(approved) in before
        assert str(ignored) not in before and not any(str(control) in value for value in before)
        policy = PathPolicy(snapshot_root,[str(snapshot_root/"**")],[],"snapshot-test")
        reservation = SimpleNamespace(state=snapshot_state,intent={"workspaceBaseline":before},policy=policy,meta={"action":"product"})
        mutation_paths = [tracked, approved, deleted, renamed, snapshot_root/"renamed-new.py", snapshot_root/"added.py"]
        tracked.write_text("unreported tracked edit\n"); approved.write_text("unreported approved edit\n")
        deleted.unlink(); renamed.rename(mutation_paths[4]); mutation_paths[5].write_text("unreported add\n")
        for path in mutation_paths:
            declaration = [{"path":str(other),"action":"modified"} for other in mutation_paths if other != path]
            try: verify_workspace_diff(reservation,{"filesChanged":declaration})
            except RunnerError as exc: assert "unreported workspace change" in str(exc) and str(path) in str(exc), str(exc)
            else: raise AssertionError("unreported dirty add/delete/rename/edit escaped actual scope")
        rows = verify_workspace_diff(reservation,{"filesChanged":[{"path":str(path),"action":"modified"} for path in mutation_paths]})
        assert {row["path"] for row in rows} == {str(path) for path in mutation_paths}
        assert foreign.read_text() == "pre-existing untracked\n"
        with patch("agent_contract_runner.subprocess.run",side_effect=OSError("Git inspection failure")):
            try: workspace_snapshot(snapshot_state)
            except RunnerError as exc: assert "scope snapshot unavailable" in str(exc)
            else: raise AssertionError("known Git workspace must fail closed")
        print("PASS tracked build/source.py, approved untracked dist product, dirty add/delete/rename and Git failure preserve actual scope and control exclusions")

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

        # Identity failures must use the exact Popen child as the emergency
        # boundary.  A process-group kill would be unsafe after identity
        # reads fail or a PID is no longer trusted.
        captured = {}
        real_popen = result_gateway.subprocess.Popen
        def capture_popen(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            captured["process"] = process
            return process
        reservation = SimpleNamespace(
            work_timeout=lambda requested: requested,
            before_spawn=lambda: None,
            state={"budget": {"deadlineAt": None}},
        )
        with patch.object(result_gateway.subprocess, "Popen", capture_popen), \
             patch.object(result_gateway, "_mission_process_identity", side_effect=OSError("identity unavailable")), \
             patch.object(result_gateway.os, "killpg", side_effect=AssertionError("identity failure must not use killpg")):
            try:
                result_gateway.run_child([sys.executable, "-c", "import time; time.sleep(20)"], root, None, .2,
                                         reservation=reservation)
            except OSError as exc:
                assert "identity unavailable" in str(exc)
            else:
                raise AssertionError("initial identity failure must propagate")
        assert captured["process"].poll() == -signal.SIGKILL
        assert captured["process"].stdout.closed and captured["process"].stderr.closed
        print("PASS initial identity failure uses exact Popen.kill plus bounded reap")

        # A diagnostic ping cannot revoke a running job's authority. A failed
        # probe is unknown, never a worker failure or an implicit cancellation.
        for error_type in (OSError, RunnerError):
            captured = {}
            identity_reads = []
            observations = []
            def fail_capture_identity(pid):
                identity_reads.append(pid)
                if len(identity_reads) in (3, 4):
                    raise error_type("identity read failed")
                return agent_contract_runner._mission_process_identity(pid)
            reservation = SimpleNamespace(
                work_timeout=lambda requested: requested,
                before_spawn=lambda: None,
                record_process=lambda pid, **kwargs: None,
                observe_process=observations.append,
                stop_requested=lambda: False,
                state={"cancelled": False, "budget": {"deadlineAt": None}},
            )
            with patch.object(result_gateway.subprocess, "Popen", capture_popen), \
                 patch.object(result_gateway, "CHILD_OBSERVATION_SECONDS", .02), \
                 patch.object(result_gateway, "_mission_process_identity", fail_capture_identity), \
                 patch.object(result_gateway.os, "killpg", side_effect=AssertionError("diagnostic probe must not kill")):
                observed = result_gateway.run_child(
                    [sys.executable, "-c", "import time; time.sleep(.25); print('completed once')"],
                    root, None, .2, reservation=reservation)
            assert observed["exitCode"] == 0 and observed["stdout"] == b"completed once\n"
            assert observed["error"] is None and observed["terminationSignal"] is None and not observed["timedOut"]
            assert observations[0]["diagnosis"] == "unknown" and observations[0]["probe"]["error"]
            assert observations[0]["processAlive"] is True and observations[0]["identityMatches"] is None
            assert any(row["probe"]["status"] == "alive" for row in observations[2:])
            assert captured["process"].stdout.closed and captured["process"].stderr.closed
        print("PASS failed diagnostic pings remain unknown, recover on later pings, and never kill or replay the child")

        # Eight hours on the controller observation clock are not eight hours
        # of load testing. This checks the absence of a hidden wall cutoff with
        # a real child, including silence after both streams close.
        for eof_silent in (False, True):
            clock_offset = [0.0]
            observations = []
            def observe_hours(row):
                observations.append(row)
                clock_offset[0] = 8 * 3600.0
            reservation = SimpleNamespace(
                work_timeout=lambda requested: requested,
                before_spawn=lambda: None,
                record_process=lambda pid, **kwargs: None,
                observe_process=observe_hours,
                stop_requested=lambda: False,
                state={"cancelled": False, "budget": {"deadlineAt": None}},
            )
            product_marker = root / ("hours-eof.txt" if eof_silent else "hours-silent.txt")
            child_code = ("import os,time; from pathlib import Path; "
                          + ("os.close(1); os.close(2); " if eof_silent else "")
                          + "time.sleep(.25); Path(" + repr(str(product_marker)) + ").write_text('once')")
            with patch.object(result_gateway, "time", SimpleNamespace(monotonic=lambda: time.monotonic() + clock_offset[0])), \
                 patch.object(result_gateway, "CHILD_OBSERVATION_SECONDS", .02):
                observed = result_gateway.run_child([sys.executable, "-c", child_code], root, None, .2,
                                                    reservation=reservation)
            after_hours = [row for row in observations if row["elapsedMs"] >= 8 * 3600 * 1000 and row["processAlive"]]
            assert after_hours and any(row["diagnosis"] == "alive_waiting" for row in after_hours)
            assert all(row["hangConfirmed"] is False and row["modelStatus"] == "unknown" for row in after_hours)
            assert product_marker.read_text() == "once" and observed["exitCode"] == 0
            assert observed["error"] is None and observed["terminationSignal"] is None and not observed["timedOut"]
        print("PASS eight simulated hours of silence/EOF preserve the real child until completion; no wall cutoff")

        observations = []
        with patch.object(result_gateway, "CHILD_OBSERVATION_SECONDS", .02):
            cpu_child = result_gateway.run_child([sys.executable, "-c",
                "import time; end=time.monotonic()+.3\nwhile time.monotonic()<end: pass"], root, None, .2,
                reservation=SimpleNamespace(work_timeout=lambda requested: requested, before_spawn=lambda: None,
                    record_process=lambda pid, **kwargs: None, observe_process=observations.append,
                    stop_requested=lambda: False, state={"cancelled": False, "budget": {"deadlineAt": None}}))
        assert cpu_child["exitCode"] == 0 and cpu_child["stdout"] == b""
        assert any(row["diagnosis"] == "alive_active" and (row["processActivity"]["cpuDeltaTicks"] or 0) > 0 for row in observations)
        assert all(row["modelStatus"] == "unknown" and row["productiveProgress"] == "unknown" for row in observations)
        print("PASS local CPU activity is visible without stdout and never claims remote model progress")

        class CleanupReservation(result_gateway.MissionReservation):
            def __init__(self):
                self.state = {"cancelled": False, "status": "running", "budget": {"deadlineAt": None}}
                self.intent = {"status": "reserved"}
                self.cancelled_at = None
                self.killed_at = None

            def save(self): pass
            def work_timeout(self, requested):
                if self.state["cancelled"]: raise RunnerError("cancelled")
                return requested
            def before_spawn(self): self.intent["status"] = "dispatching"
            def observe_process(self, observation):
                super().observe_process(observation)
                if observation["lastOutputAt"] and not self.state["cancelled"]:
                    self.cancelled_at = time.monotonic()
                    self.cancel("fixture cancellation")
            def force_owned_process_stop(self, identity):
                self.killed_at = time.monotonic()
                return super().force_owned_process_stop(identity)

        payload = b"x" * (256 * 1024) + b"\n"
        term_handler = '''import os, signal, sys, time
def stop(signum, frame):
    payload = b'x' * (256 * 1024) + b'\\n'
    sys.stdout.buffer.write(payload); sys.stdout.buffer.flush()
    sys.stderr.buffer.write(payload); sys.stderr.buffer.flush()
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
os.write(1, b'ready\\n')
time.sleep(20)
'''
        cleanup_reservation = CleanupReservation()
        with patch.object(result_gateway, "CHILD_OBSERVATION_SECONDS", .01), \
             patch.object(agent_contract_runner, "MISSION_RESERVE_SECONDS", .65):
            oversized = result_gateway.run_child([sys.executable, "-c", term_handler], root, None, .2,
                                                 reservation=cleanup_reservation)
        assert oversized["captureLimited"] is False and oversized["stdout"] == b"ready\n" + payload
        assert oversized["stderr"] == payload and oversized["terminationSignal"] == "SIGTERM"
        assert oversized["exitCode"] == 0 and oversized["processStopped"] is True and not oversized["drainTimedOut"]
        assert cleanup_reservation.killed_at is None
        print("PASS cancelled TERM handler writes more than pipe capacity and exits without KILL or output loss")

        cleanup_reservation = CleanupReservation()
        started = time.monotonic()
        with patch.object(result_gateway, "CHILD_OBSERVATION_SECONDS", .01), \
             patch.object(agent_contract_runner, "MISSION_RESERVE_SECONDS", .65):
            ignored_term = result_gateway.run_child(
                [sys.executable, "-c", "import os,signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); os.write(1,b'ready\\n'); time.sleep(20)"],
                root, None, .15, reservation=cleanup_reservation)
        elapsed = time.monotonic() - started
        assert ignored_term["terminationSignal"] == "SIGKILL" and ignored_term["processStopped"] is True
        assert ignored_term["drainTimedOut"] is False and elapsed < .8
        assert .1 <= cleanup_reservation.killed_at - cleanup_reservation.cancelled_at <= .3
        print("PASS TERM-ignoring child escalates to KILL within the original shared cleanup deadline")

        # A refused identity must not become an unbounded cleanup loop or a
        # reason to signal whichever PID now happens to exist.
        def mismatched_identity(pid):
            identity = agent_contract_runner._mission_process_identity(pid)
            return dict(identity, startTicks=str(identity["startTicks"]) + "-foreign") if identity else None
        captured = {}
        cleanup_reservation = CleanupReservation()
        started = time.monotonic()
        try:
            with patch.object(result_gateway.subprocess, "Popen", capture_popen), \
                 patch.object(result_gateway, "_mission_process_identity", mismatched_identity), \
                 patch.object(result_gateway, "CHILD_OBSERVATION_SECONDS", .01), \
                 patch.object(agent_contract_runner, "MISSION_RESERVE_SECONDS", .35):
                refused = result_gateway.run_child(
                    [sys.executable, "-c", "import os,time; os.write(1,b'ready\\n'); time.sleep(20)"],
                    root, None, .1, reservation=cleanup_reservation)
            assert time.monotonic() - started < .8
            assert refused["drainTimedOut"] and not refused["processStopped"]
            assert captured["process"].poll() is None
        finally:
            process = captured.get("process")
            if process is not None:
                if process.poll() is None: process.kill()
                process.wait(timeout=3)
        print("PASS refused identity remains untouched and streaming cleanup reaches its original hard deadline")

        foreign_child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"], cwd=root,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                          start_new_session=True)
        try:
            identity = agent_contract_runner._mission_process_identity(foreign_child.pid)
            foreign_identity = dict(identity, startTicks=str(identity["startTicks"]) + "-foreign")
            assert agent_contract_runner._terminate_mission_process(
                foreign_identity, (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(), wait=False) is False
            assert foreign_child.poll() is None
        finally:
            if foreign_child.poll() is None:
                foreign_child.kill()
            foreign_child.wait(timeout=3)
        print("PASS mismatched process identity leaves the foreign child untouched")

        # Residual pipe data can exceed capture limits after the exact child
        # was reaped. Reject incomplete capture without signalling its old PGID.
        stream_child = result_gateway._run_child_streaming
        for max_stdout, max_frame in ((32, 128), (128, 32)):
            def drain_after_reap(process, *args, **kwargs):
                process.wait(timeout=3)
                return stream_child(process, *args, max_stdout=max_stdout, max_frame=max_frame, **kwargs)

            with patch.object(result_gateway, "_run_child_streaming", drain_after_reap), \
                 patch.object(result_gateway.os, "killpg") as group_signal:
                drained = result_gateway.run_child(
                    [sys.executable, "-c", "import os; os.write(1,b'x'*64+b'\\n')"], root, None, .1)
            assert drained["captureLimited"] is True and drained["processStopped"] is True
            assert drained["exitCode"] == 0 and drained["error"] and not drained["timedOut"]
            group_signal.assert_not_called()
        print("PASS post-reap stream/frame overflow rejects capture without signalling the old process group")

        # Exercise bounded live reads without allocating an unbounded pipe buffer.
        child = run_child([sys.executable, "-c", "import os; [os.write(1,b'x'*65535+b'\\n') for _ in range(272)]"], root, None, .1)
        assert child["captureLimited"] is True and len(child["stdout"]) == MAX_STDOUT_BYTES, child
        child = run_child([sys.executable, "-c", "import os; os.write(1,b'x'*(5*1024*1024))"], root, None, .1,
                          detect_claude_tool_loop=True)
        assert child["captureLimited"] is True and len(child["stdout"]) <= MAX_FRAME_BYTES + 65536
        loop_code = '''import json,time
for index in range(4):
    print(json.dumps({"message":{"content":[{"type":"tool_use","name":"Read","id":str(index),"input":{"path":"same.txt"}}]}}),flush=True)
    print(json.dumps({"message":{"content":[{"type":"tool_result","tool_use_id":str(index),"content":"Wasted call: file unchanged since your last read"}]},"tool_use_result":{"type":"file_unchanged"}}),flush=True)
time.sleep(.15)
print("finished after warning", flush=True)
'''
        loop_events = root / "tool-warning-events.jsonl"
        child = run_child([sys.executable, "-c", loop_code], root, None, .1,
                          detect_claude_tool_loop=True, events_path=loop_events)
        assert child["error"] is None and child["exitCode"] == 0 and child["terminationSignal"] is None
        assert b"finished after warning" in child["stdout"] and len(child["warnings"]) == 1
        assert sum(json.loads(line)["event"].endswith(".runtime_warning") for line in loop_events.read_text().splitlines()) == 1
        print("PASS bounded capture remains enforced; repeated tool reads warn once without cancelling a living child")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
