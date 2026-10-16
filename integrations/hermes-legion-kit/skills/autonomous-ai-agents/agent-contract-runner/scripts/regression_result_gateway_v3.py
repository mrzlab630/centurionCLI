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
from agent_contract_runner import initialize_mission, _mission_digest, workspace_snapshot, verify_workspace_diff, PathPolicy, RunnerError, complete_mission, mission_snapshot, validate_order
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
elif mode == "malformed": raw = b"prose {not-json SYNTHETIC_SECRET_MARKER"
else: raw = json.dumps(payload).encode()
if order["executor"] == "claude":
    print(json.dumps({"type":"result","subtype":"success","is_error":False,"permission_denials":[],
        "structured_output":payload,"modelUsage":{"claude-opus-5-5":{"inputTokens":1}}}))
else: Path(order["launch"]["candidateJsonPath"]).write_bytes(raw)
''')
        cli.chmod(0o755)

        def stage(name: str, mode: str = "valid", *, profile="V0", original=None, capability=None) -> dict:
            paths = fixture.make_case("v3-" + name, "valid")
            order = fixture.read_json(Path(paths["order"]))
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
                reviewer="none" if profile == "V0" else "claude-opus-5-5",
                reasons=["exact bounded oracle"] if profile == "V0" else ["promotion: independent verification required"],
                trustPredicates={key: True for key in ("localNarrowBlastRadius", "cheapReversal", "deterministicFailureOracle", "noSensitiveOrExternalSideEffects", "requiredArtifactsPass", "requiredProofsPass", "noUncertainty", "noScopeOrAssumptionIssues")})
            fixture.set_routing(order, route)
            if original is not None:
                prior = fixture.read_json(Path(original["order"]))
                state = fixture.read_json(Path(prior["loopContract"]["statePath"]))
                candidate = state["intents"]["product-1"]
                order["context"][0].update(prior["context"][0], fixtureMode=mode, action="review", intentId="review-1", candidateIntentId="product-1",
                    reviewBinding={"reviewedOrderId": prior["orderId"], "reviewedResultSha256": candidate["resultRef"]["sha256"],
                                   "productSnapshotSha256": candidate["snapshot"]["sha256"]})
                order["loopContract"] = prior["loopContract"]
                order["allowedPaths"] = [str(control / "**")]
                order["proofCommands"] = []
            else:
                authority = {"approvalRef":"fixture-approved", "goal":order["objective"], "nonGoals":[], "criteria":order["acceptanceCriteria"],
                        "allowedActions":["product","review","report","advisory"], "allowedPaths":[str(product)], "forbiddenPaths":[]}
                if capability is not None:
                    authority["reportCapabilityRef"] = capability
                initialize_mission({"policyVersion":"3.0", "missionId":"mission-"+name, "workspace":str(fixture.ROOT), "strategyId":"initial",
                    "authority":authority,
                    "budget":{"maxModelLaunches":8, "deadlineAt":(datetime.now(timezone.utc)+timedelta(seconds=300)).isoformat()},
                    "tasks":{"task":{"objective":order["objective"], "acceptanceCriteria":order["acceptanceCriteria"], "allowedPaths":[str(product)],
                        "productPaths":[str(product)], "dependencies":[], "maxProductAttempts":3, "verificationProfile":profile,
                        "requiredProof":order["proofCommands"], "expectedArtifacts":[]}}}, state_path)
            order["launch"]["candidateJsonPath"] = str(paths["candidate"])
            order["launch"]["command"] = shlex.join([str(cli), "exec", "--model", "gpt-6-luna", "-c",
                "model_reasoning_effort=high", "--output-last-message", str(paths["candidate"]), str(paths["order"])])
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
            assert (replay.returncode == 0) == (mode == "valid"), replay.stderr
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
            order["launch"]["command"] = shlex.join([str(claude), "-p", "--model", "claude-opus-5-5",
                "--effort", "high", "--json-schema", json.dumps(schema), "--output-format", "json", str(paths["order"])])
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
                accepted = fixture.run_gateway(original)
                assert accepted.returncode == 0 and 'accepted' in accepted.stdout, accepted.stderr + accepted.stdout
                assert (Path(original["result"]).parent / "launch-count").read_text() == "launch\n"
                state = fixture.read_json(Path(order["loopContract"]["statePath"]))
                assert state["budget"]["modelLaunchesUsed"] == 2 and state["tasks"]["task"]["productAttemptsUsed"] == 1
        print("PASS native Claude review pass/fail/blocked, missing verdict and stale snapshot binding; done alone cannot authorize acceptance")

        # Exact no-tools report adapter: only the controller's allowlisted projection
        # is visible to this deterministic fake CLI, including on restart collection.
        report_cli = root / "report" / "claude"
        report_cli.parent.mkdir()
        report_cli.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
for flag,value in [("--tools",""),("--mcp-config",'{"mcpServers":{}}'),("--setting-sources","")]:
 assert args[args.index(flag)+1]==value
assert "--bare" in args and "--strict-mcp-config" in args
assert "SYNTHETIC_SECRET_MARKER" not in sys.argv[-1]
scratch=Path(os.environ["CLAUDE_CONFIG_DIR"])
assert scratch==Path.cwd() and all(os.environ[key]==str(scratch) for key in ("HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_CACHE_HOME"))
(scratch/"debug").mkdir(); (scratch/"debug"/"native.log").write_text("native debug scratch\\n")
(scratch/".claude.json").write_text(json.dumps({"numStartups":1,"firstStartTime":"fixture","projects":{}}))
p=json.loads(sys.argv[-1]); row=p["productSnapshot"]["files"][0]
counter=Path(__file__).with_name("count"); counter.write_text(counter.read_text()+"report\\n" if counter.exists() else "report\\n")
result={"resultVersion":"AGENT_RESULT_JSON_V1","orderId":p["order"]["orderId"],"executor":p["order"]["executor"],"status":"done",
"summary":"saved product", "filesChanged":p["filesChanged"],
"artifacts":p["artifacts"],
"proof":p["controllerProof"],"selfReview":{"performed":True,"findings":[],"fixesApplied":[]},"scopeDeviations":[],"forbiddenPatternHits":[],
"remainingRisks":[],"questions":[],"errors":[],"stdoutSummary":"","stderrSummary":"","handoff":p["handoff"]}
print(json.dumps({"type":"result","subtype":"success","is_error":False,"permission_denials":[],"structured_output":result,"modelUsage":{"claude-opus-5-5":{}}}))
''')
        report_cli.chmod(0o755)
        settings = root / "settings.json"
        fixture.write_json(settings, {"disableAllHooks":True})
        isolated = root / "empty-config"
        isolated.mkdir()
        from agent_contract_runner import _mission_file_ref
        cap_path = fixture.ROOT / ".centurion" / "report-capability.json"
        fixture.write_json(cap_path, {"version":"CENTURION_NO_TOOLS_REPORT_V1", "cliRef":_mission_file_ref(report_cli),
            "configRef":_mission_file_ref(settings), "scratchDir":str(isolated),
            "route":{"executor":"claude","model":"claude-opus-5-5","effort":"high"},
            "probe":{"status":"passed","toolsDenied":True,"mcpDisabled":True,"hooksDisabled":True,"isolatedConfig":True,"productUnchanged":True}})
        recovery = stage("report-recovery", "malformed", capability=_mission_file_ref(cap_path))
        malformed = fixture.run_gateway(recovery)
        assert malformed.returncode != 0 and not Path(recovery["result"]).exists(), malformed.stderr
        # Interrupt before observation, then after real durable observation.
        # Both restarts must collect this same report without another turn.
        first_report_errors = io.StringIO()
        with patch.object(sys,"argv",fixture.gateway_command(recovery)[1:]+["--recover-report"]), \
             patch.dict(os.environ,fixture.environment(),clear=True), \
             patch.object(result_gateway.MissionReservation,"observe_result",side_effect=OSError("fixture interruption after report capture")), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(first_report_errors):
            assert result_gateway.main() != 0
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
        raw = Path(recovery["candidate"]).read_bytes()
        assert b"SYNTHETIC_SECRET_MARKER" in raw and Path(recovery["candidate"]).stat().st_mode & 0o777 == 0o600
        Path(recovery["candidate"]).write_bytes(raw+b"tamper")
        try: verify_input_results(downstream, fixture.ROOT)
        except AcceptedInputError: pass
        else: raise AssertionError("recovery must retain original malformed raw binding")
        Path(recovery["candidate"]).write_bytes(raw)
        print("PASS report recovery before/after durable observation, canonical create-only/candidate equality, two launches/one product/one report, downstream binding and restricted synthetic secret marker")

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
