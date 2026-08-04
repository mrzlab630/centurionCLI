#!/usr/bin/env python3
"""Regression checks for the local agent contract runner MVP gate."""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest import mock

from attempt_ledger import append_attempt

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "agent_contract_runner.py"
FIXTURE_ROOT = Path("/tmp/agent-contract-runner-regression")
BIN_DIR = FIXTURE_ROOT / "bin"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ambiguous_json_bytes(original: bytes, variant: str) -> bytes:
    text = original.decode("utf-8").rstrip()
    if variant == "duplicate-key":
        return ('{"orderId":"ambiguous",' + text[1:] + "\n").encode("utf-8")
    literal = {
        "nan": "NaN",
        "infinity": "Infinity",
        "negative-infinity": "-Infinity",
        "overflow": "1e999",
    }[variant]
    return (text[:-1] + ',"ambiguous":' + literal + "}\n").encode("utf-8")


def install_fake_executor() -> None:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    fake_source = (
        "#!/usr/bin/env python3\n"
        "import json, pathlib, sys, time\n"
        "executor_name = pathlib.Path(sys.argv[0]).name\n"
        "result_path = pathlib.Path(sys.argv[1])\n"
        "artifact_path = pathlib.Path(sys.argv[2])\n"
        "proof_status = sys.argv[3]\n"
        "order_id = sys.argv[4]\n"
        "sleep_seconds = float(sys.argv[5]) if len(sys.argv) > 5 else 0\n"
        "print('fake executor stdout', flush=True)\n"
        "print('fake executor stderr', file=sys.stderr, flush=True)\n"
        "launch_count = __import__('os').environ.get('FAKE_LAUNCH_COUNT')\n"
        "if launch_count:\n"
        "    pathlib.Path(launch_count).parent.mkdir(parents=True, exist_ok=True)\n"
        "    with pathlib.Path(launch_count).open('a', encoding='utf-8') as count_handle:\n"
        "        count_handle.write('launch\\n')\n"
        "skip_artifact = __import__('os').environ.get('FAKE_SKIP_ARTIFACT_WRITE') == '1'\n"
        "if str(artifact_path) != 'NONE' and not skip_artifact:\n"
        "    artifact_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    artifact_path.write_text('artifact created\\n', encoding='utf-8')\n"
        "artifact_exists_claim = __import__('os').environ.get('FAKE_ARTIFACT_EXISTS_CLAIM')\n"
        "reported_exists = artifact_path.exists() if artifact_exists_claim is None else artifact_exists_claim.lower() == 'true'\n"
        "payload = {\n"
        "    'resultVersion': 'AGENT_RESULT_JSON_V1',\n"
        "    'orderId': order_id,\n"
        "    'executor': executor_name,\n"
        "    'status': 'done',\n"
        "    'summary': 'fake executor completed',\n"
        "    'filesChanged': [{'path': str(artifact_path), 'action': 'added'}],\n"
        "    'artifacts': [{'path': str(artifact_path), 'exists': reported_exists, 'type': 'fixture', 'note': 'test artifact'}],\n"
        "    'proof': [{'command': 'fake executor reported proof', 'cwd': str(result_path.parent), 'status': proof_status, 'exitCode': 0, 'summary': 'reported by fake executor'}],\n"
        "    'scopeDeviations': [],\n"
        "    'forbiddenPatternHits': [],\n"
        "    'remainingRisks': [],\n"
        "    'questions': [],\n"
        "    'errors': [],\n"
        "    'selfReview': {'performed': True, 'findings': [], 'fixesApplied': []},\n"
        "    'stdoutSummary': 'fake stdout',\n"
        "    'stderrSummary': 'fake stderr',\n"
        "}\n"
        "loop_json = __import__('os').environ.get('FAKE_LOOP_METADATA')\n"
        "if loop_json:\n"
        "    payload.setdefault('executorExtensions', {})['aquilaLoop'] = json.loads(loop_json)\n"
        "result_mode = __import__('os').environ.get('FAKE_RESULT_MODE', 'valid')\n"
        "if result_mode == 'missing':\n"
        "    raise SystemExit(0)\n"
        "if result_mode == 'wrong_order':\n"
        "    payload['orderId'] = 'wrong-order-id'\n"
        "elif result_mode == 'wrong_executor':\n"
        "    payload['executor'] = 'codex' if executor_name != 'codex' else 'claude'\n"
        "elif result_mode == 'files_changed_string':\n"
        "    payload['filesChanged'] = 'artifact.txt'\n"
        "elif result_mode == 'self_review_string':\n"
        "    payload['selfReview'] = 'performed'\n"
        "result_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "if result_mode == 'empty':\n"
        "    result_path.write_bytes(b'')\n"
        "    raise SystemExit(0)\n"
        "if result_mode == 'unparseable':\n"
        "    result_path.write_text('{not-json', encoding='utf-8')\n"
        "    raise SystemExit(0)\n"
        "if result_mode in {'duplicate_key', 'non_finite', 'infinity', 'negative_infinity', 'overflow_non_finite'}:\n"
        "    raw = json.dumps(payload)\n"
        "    if result_mode == 'duplicate_key':\n"
        "        raw = '{\\\"orderId\\\":\\\"ambiguous\\\",' + raw[1:]\n"
        "    else:\n"
        "        literal = {'non_finite': 'NaN', 'infinity': 'Infinity', 'negative_infinity': '-Infinity', 'overflow_non_finite': '1e999'}[result_mode]\n"
        "        raw = raw[:-1] + ',\\\"ambiguous\\\":' + literal + '}'\n"
        "    result_path.write_text(raw, encoding='utf-8')\n"
        "    raise SystemExit(0)\n"
        "if result_mode == 'stdout_only':\n"
        "    print(json.dumps(payload, sort_keys=True), flush=True)\n"
        "    raise SystemExit(0)\n"
        "result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
        "if sleep_seconds:\n"
        "    time.sleep(sleep_seconds)\n"
    )
    for name in ["other", "codex", "claude", "agy", "hermes_delegate_task"]:
        fake = BIN_DIR / name
        fake.write_text(fake_source, encoding="utf-8")
        fake.chmod(0o755)


def make_order(
    case_dir: Path,
    name: str,
    proof_status: str,
    create_artifact: bool,
    proof_command: str,
    timeout_seconds: int = 10,
    executor_sleep_seconds: int = 0,
    allowed_paths: list[str] | None = None,
    forbidden_paths: list[str] | None = None,
    result_path: Path | None = None,
    cli_result_path: Path | None = None,
    launch_result_path: Path | None = None,
    output_result_path: Path | None = None,
    artifact_path: Path | None = None,
    proof_cwd: Path | None = None,
    expected_artifacts: list[dict[str, Any]] | None = None,
    proof_argv: list[str] | None = None,
    output_alias_only: bool = False,
    prose_allowed_after_json: Any = False,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    order_id = f"regression-{name}"
    actual_result_path = result_path or case_dir / "result.json"
    actual_artifact_path = artifact_path or case_dir / "artifact.txt"
    stdout_path = case_dir / "stdout.log"
    stderr_path = case_dir / "stderr.log"
    events_path = case_dir / "events.jsonl"
    executor_artifact_arg = actual_artifact_path if create_artifact else Path("NONE")
    proof_item = {"command": proof_command, "cwd": str(proof_cwd or case_dir), "required": True}
    if proof_argv is not None:
        proof_item["argv"] = proof_argv
    output_contract = {
        "resultVersion": "AGENT_RESULT_JSON_V1",
        "resultPath": str(output_result_path or actual_result_path),
        "stdoutAllowed": True,
    }
    if output_alias_only:
        output_contract["proseAfterJsonAllowed"] = False
    else:
        output_contract["proseAllowedAfterJson"] = prose_allowed_after_json
    order = {
        "orderVersion": "AGENT_ORDER_JSON_V1",
        "orderId": order_id,
        "createdAt": "2026-06-17T00:00:00Z",
        "controller": "Aquila",
        "executor": "other",
        "roleForTask": "regression fixture",
        "riskLevel": "low",
        "workspace": {
            "repoPath": str(case_dir),
            "branchOrWorktree": "tmp fixture",
            "projectName": "runner regression",
        },
        "launch": {
            "surface": "regression fake executor",
            "command": f"other {actual_result_path} {executor_artifact_arg} {proof_status} {order_id} {executor_sleep_seconds}",
            "timeoutSeconds": timeout_seconds,
            "resultJsonPath": str(launch_result_path or actual_result_path),
            "stdoutPath": str(stdout_path),
            "stderrPath": str(stderr_path),
        },
        "objective": "exercise runner regression gate",
        "context": ["local tmp fixture"],
        "allowedPaths": allowed_paths or [str(case_dir / "**")],
        "forbiddenPaths": forbidden_paths or [],
        "forbiddenActions": [],
        "nonGoals": [],
        "acceptanceCriteria": ["runner behavior matches expected outcome"],
        "expectedArtifacts": expected_artifacts
        or [{"path": str(actual_artifact_path), "type": "fixture", "required": True}],
        "proofCommands": [proof_item],
        "outputContract": output_contract,
        "stopConditions": ["stop on regression failure"],
        "notesForExecutor": ["fake executor only"],
    }
    order_path = case_dir / "order.json"
    write_json(order_path, order)
    return order_path, cli_result_path or actual_result_path, actual_artifact_path, stdout_path, stderr_path, events_path


def run_case(
    name: str,
    proof_status: str,
    create_artifact: bool,
    proof_command: str,
    timeout_seconds: int = 10,
    executor_sleep_seconds: int = 0,
    allow_other: bool = True,
    allowed_paths: list[str] | None = None,
    forbidden_paths: list[str] | None = None,
    result_path: Path | None = None,
    cli_result_path: Path | None = None,
    launch_result_path: Path | None = None,
    output_result_path: Path | None = None,
    artifact_path: Path | None = None,
    proof_cwd: Path | None = None,
    expected_artifacts: list[dict[str, Any]] | None = None,
    proof_argv: list[str] | None = None,
    output_alias_only: bool = False,
    prose_allowed_after_json: Any = False,
    result_mode: str = "valid",
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path, Path, Path]:
    case_dir = FIXTURE_ROOT / name
    case_dir.mkdir(parents=True, exist_ok=True)
    order_path, cli_result, actual_artifact_path, stdout_path, stderr_path, events_path = make_order(
        case_dir,
        name,
        proof_status,
        create_artifact,
        proof_command,
        timeout_seconds=timeout_seconds,
        executor_sleep_seconds=executor_sleep_seconds,
        allowed_paths=allowed_paths,
        forbidden_paths=forbidden_paths,
        result_path=result_path,
        cli_result_path=cli_result_path,
        launch_result_path=launch_result_path,
        output_result_path=output_result_path,
        artifact_path=artifact_path,
        proof_cwd=proof_cwd,
        expected_artifacts=expected_artifacts,
        proof_argv=proof_argv,
        output_alias_only=output_alias_only,
        prose_allowed_after_json=prose_allowed_after_json,
    )
    env = os.environ.copy()
    env["PATH"] = f"{BIN_DIR}:{env.get('PATH', '')}"
    env["FAKE_RESULT_MODE"] = result_mode
    if allow_other:
        env["AGENT_CONTRACT_RUNNER_ALLOW_OTHER"] = "1"
    else:
        env.pop("AGENT_CONTRACT_RUNNER_ALLOW_OTHER", None)
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--order",
            str(order_path),
            "--mode",
            "run",
            "--events",
            str(events_path),
            "--result",
            str(cli_result),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed, cli_result, actual_artifact_path, stdout_path, stderr_path, events_path


def assert_case(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def events_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_runner_module() -> Any:
    spec = importlib.util.spec_from_file_location("agent_contract_runner_regression_target", RUNNER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load runner module for lock regression")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_loop_fixture(name: str, executor: str, phase: str, state: dict[str, Any], metadata: dict[str, Any], *, allowed_state: bool = False, state_loop_id: str | None = None, executor_sleep_seconds: int = 0, structured_proof: bool = True) -> tuple[Path, Path, Path, Path, dict[str, str]]:
    case_dir = FIXTURE_ROOT / name
    case_dir.mkdir(parents=True, exist_ok=True)
    state_path = case_dir / "state.json"
    result_path = case_dir / "result.json"
    artifact_path = case_dir / "artifact.txt"
    events_path = case_dir / "events.jsonl"
    state_copy = dict(state)
    state_copy["statePath"] = str(state_path)
    contract_loop_id = state_copy["loopId"]
    if state_loop_id is not None:
        state_copy["loopId"] = state_loop_id
    write_json(state_path, state_copy)
    allowed = [str(case_dir), str(result_path), str(artifact_path), str(events_path), str(case_dir / "stdout.log"), str(case_dir / "stderr.log")]
    if allowed_state:
        allowed.append(str(state_path))
    order = {
        "orderVersion": "AGENT_ORDER_JSON_V1", "orderId": f"{name}-order", "createdAt": "2026-07-24T11:00:00Z", "controller": "Aquila", "executor": executor,
        "roleForTask": "loop fixture", "riskLevel": "low", "workspace": {"repoPath": str(case_dir), "branchOrWorktree": "fixture", "projectName": "loop-fixture"},
        "launch": {"surface": "fake", "command": f"{executor} {result_path} {artifact_path} pass {name}-order {executor_sleep_seconds}", "timeoutSeconds": 5, "resultJsonPath": str(result_path), "stdoutPath": str(case_dir / "stdout.log"), "stderrPath": str(case_dir / "stderr.log")},
        "objective": state_copy["workItem"]["objective"], "context": ["loop fixture"], "allowedPaths": allowed, "forbiddenPaths": [], "forbiddenActions": [], "nonGoals": [], "acceptanceCriteria": ["bounded phase"],
        "expectedArtifacts": [{"path": str(artifact_path), "type": "fixture", "required": True}], "proofCommands": [{"command": "python3 -c 'print(\"proof\")'", "argv": ["python3", "-c", "print(\"proof\")"], "cwd": str(case_dir), "required": True}],
        "outputContract": {"resultVersion": "AGENT_RESULT_JSON_V1", "resultPath": str(result_path), "stdoutAllowed": True, "proseAllowedAfterJson": False}, "stopConditions": ["stop"], "notesForExecutor": ["one phase"],
        "loopContract": {"version": "AQUILA_LOOP_V1", "loopId": contract_loop_id, "phase": phase, "statePath": str(state_path), "controller": "Aquila", "workItem": {"workItemId": state_copy["workItem"]["workItemId"], "project": state_copy["project"], "objective": state_copy["workItem"]["objective"]}, "iteration": state_copy["iteration"], "budgets": {"maxWallSeconds": state_copy["budgets"]["maxWallSeconds"]}, "executorStateWrites": False, "scheduleNextIteration": False, "selfApprove": False}
    }
    if not structured_proof:
        order["proofCommands"][0].pop("argv")
    if phase == "verify":
        order["loopContract"]["candidate"] = state_copy["candidate"]
        order["loopContract"]["verification"] = {"blind": True, "candidateOrderId": state_copy["candidate"]["orderId"], "candidateExecutor": state_copy["candidate"]["executor"]}
    order_path = case_dir / "order.json"
    write_json(order_path, order)
    env = os.environ.copy()
    env["PATH"] = f"{BIN_DIR}:{env.get('PATH', '')}"
    env["FAKE_LOOP_METADATA"] = json.dumps(metadata)
    return order_path, result_path, state_path, events_path, env


def run_loop_fixture(name: str, executor: str, phase: str, state: dict[str, Any], metadata: dict[str, Any], **kwargs: Any) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    order_path, result_path, state_path, events_path, env = make_loop_fixture(name, executor, phase, state, metadata, **kwargs)
    completed = subprocess.run([sys.executable, str(RUNNER), "--order", str(order_path), "--mode", "run", "--events", str(events_path), "--result", str(result_path)], cwd=ROOT, env=env, check=False, text=True, capture_output=True)
    return completed, result_path, state_path, events_path


def base_loop_state(
    status: str = "ready",
    *,
    current: int = 1,
    pending: list[str] | None = None,
    candidate: dict[str, str] | None = None,
    started_at: str | None = None,
    max_wall_seconds: int = 3600,
) -> dict[str, Any]:
    safe_started_at = started_at or (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return {"stateVersion": "AQUILA_LOOP_STATE_V1", "loopId": "loop-fixture", "controller": "Aquila", "project": "loop-fixture", "statePath": str(FIXTURE_ROOT / "placeholder" / "state.json"), "workItem": {"workItemId": "item-1", "objective": "bounded fixture", "status": status, "pendingWorkItems": pending or []}, "iteration": {"current": current, "max": 3}, "budgets": {"startedAt": safe_started_at, "maxWallSeconds": max_wall_seconds}, "candidate": candidate or {"orderId": "", "executor": "", "resultPath": ""}, "verification": {"status": "pending"}, "failures": [], "transitions": []}


def main() -> int:
    if FIXTURE_ROOT.exists():
        shutil.rmtree(FIXTURE_ROOT)
    FIXTURE_ROOT.mkdir(parents=True)
    install_fake_executor()

    for variant in ("duplicate-key", "nan", "infinity", "negative-infinity", "overflow"):
        case_dir = FIXTURE_ROOT / f"strict-order-{variant}"
        case_dir.mkdir(parents=True)
        order_path, result_path, _, _, _, events_path = make_order(
            case_dir,
            f"strict-order-{variant}",
            "pass",
            True,
            "python3 -c 'print(\"proof ok\")'",
        )
        order_path.write_bytes(ambiguous_json_bytes(order_path.read_bytes(), variant))
        strict_env = os.environ.copy()
        strict_env["AGENT_CONTRACT_RUNNER_ALLOW_OTHER"] = "1"
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--order", str(order_path), "--validate-only", "--events", str(events_path), "--result", str(result_path)],
            cwd=ROOT,
            env=strict_env,
            check=False,
            text=True,
            capture_output=True,
        )
        assert_case(completed.returncode != 0 and "strict JSON" in completed.stderr, f"runner must reject {variant} order JSON")
        assert_case("dispatch_started" not in events_text(events_path), "strict order rejection must precede dispatch")
    print("PASS runner rejects duplicate keys, NaN, Infinity, -Infinity, and 1e999 orders")

    for mode in ("duplicate_key", "non_finite", "infinity", "negative_infinity", "overflow_non_finite"):
        completed, _, _, _, _, events_path = run_case(
            f"strict-result-{mode}",
            "pass",
            True,
            "python3 -c 'print(\"proof ok\")'",
            result_mode=mode,
        )
        assert_case(completed.returncode != 0 and "strict JSON" in completed.stderr, f"runner must reject {mode} result JSON")
        assert_case("dispatch_started" in events_text(events_path), "strict result fixture must exercise post-dispatch result loading")
    print("PASS runner rejects duplicate keys, NaN, Infinity, -Infinity, and 1e999 results")

    post_cutover_dir = FIXTURE_ROOT / "post-cutover-routing"
    post_cutover_dir.mkdir(parents=True)
    missing_order, missing_result, _, _, _, missing_events = make_order(
        post_cutover_dir,
        "post-cutover-routing",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
    )
    missing_payload = json.loads(missing_order.read_text(encoding="utf-8"))
    missing_payload["createdAt"] = "2026-08-03T11:00:42Z"
    write_json(missing_order, missing_payload)
    routing_env = os.environ.copy()
    routing_env["PATH"] = f"{BIN_DIR}:{routing_env.get('PATH', '')}"
    routing_env["AGENT_CONTRACT_RUNNER_ALLOW_OTHER"] = "1"
    routing_env["HOME"] = str(FIXTURE_ROOT / "isolated-home")
    routing_env.pop("AQUILA_ATTEMPT_LEDGER", None)
    missing_route = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(missing_order), "--validate-only", "--events", str(missing_events), "--result", str(missing_result)],
        cwd=ROOT,
        env=routing_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(missing_route.returncode != 0 and "exactly one AQUILA_ROUTING_JSON_V1" in missing_route.stderr, "post-cutover missing routing must fail before dispatch")
    assert_case("dispatch_started" not in events_text(missing_events), "routing rejection must precede dispatch")
    routing_metadata = {
        "objectiveId": "runner-routing",
        "attempt": 1,
        "taskClass": "routine_implementation",
        "complexity": "medium",
        "risk": "low",
        "ambiguity": "low",
        "reversibility": "high",
        "evidenceNeed": "high",
        "executor": "other",
        "model": "other",
        "reasoningEffort": "medium",
        "executionProfile": "implementation",
        "verificationProfile": "V1",
        "reviewer": "gpt-5.6-sol",
        "confidence": "high",
        "reasons": ["deterministic proof is incomplete"],
    }
    missing_payload["notesForExecutor"] = ["AQUILA_ROUTING_JSON_V1:" + json.dumps(routing_metadata, separators=(",", ":"))]
    write_json(missing_order, missing_payload)
    valid_route = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(missing_order), "--validate-only", "--events", str(missing_events), "--result", str(missing_result)],
        cwd=ROOT,
        env=routing_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(valid_route.returncode == 0, f"valid post-cutover routing must pass: {valid_route.stderr}")
    assert_case("aquila_routing_validated:V1:gpt-5.6-sol:implementation" in events_text(missing_events), "runner must record the validated route")
    print("PASS runner enforces post-cutover routing before dispatch and accepts canonical V1")

    promotion_dir = FIXTURE_ROOT / "post-cutover-promotion"
    promotion_dir.mkdir(parents=True)
    promotion_order, promotion_result, promotion_artifact, _, _, promotion_events = make_order(
        promotion_dir,
        "post-cutover-promotion",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
    )
    promotion_payload = json.loads(promotion_order.read_text(encoding="utf-8"))
    promotion_payload["createdAt"] = "2026-08-03T11:00:42Z"
    promoted_task_class = "ledger-promoted-implementation"
    v0_metadata = {
        "objectiveId": "runner-promotion",
        "attempt": 1,
        "taskClass": promoted_task_class,
        "complexity": "low",
        "risk": "low",
        "ambiguity": "low",
        "reversibility": "high",
        "evidenceNeed": "low",
        "executor": "other",
        "model": "other",
        "reasoningEffort": "low",
        "executionProfile": "implementation",
        "verificationProfile": "V0",
        "reviewer": "none",
        "confidence": "high",
        "reasons": ["deterministic fixture"],
        "trustPredicates": {
            "localNarrowBlastRadius": True,
            "cheapReversal": True,
            "deterministicFailureOracle": True,
            "noSensitiveOrExternalSideEffects": True,
            "requiredArtifactsPass": True,
            "requiredProofsPass": True,
            "noUncertainty": True,
            "noScopeOrAssumptionIssues": True,
        },
    }
    promotion_payload["notesForExecutor"] = [
        "AQUILA_ROUTING_JSON_V1:" + json.dumps(v0_metadata, separators=(",", ":"))
    ]
    write_json(promotion_order, promotion_payload)
    ledger_path = promotion_dir / "attempts.jsonl"
    append_attempt(
        ledger_path,
        {
            "objectiveId": "prior-objective",
            "orderId": "prior-escaped-defect",
            "attempt": 1,
            "taskClass": promoted_task_class,
            "executor": "codex",
            "model": "gpt-5.6-terra",
            "reviewer": "none",
            "risk": "low",
            "status": "done",
            "failureClass": "escaped_defect",
            "severity": "high",
            "resultPath": str(promotion_dir / "prior-result.json"),
            "durationSeconds": 1.0,
        },
    )
    promotion_env = dict(routing_env)
    promotion_env["AQUILA_ATTEMPT_LEDGER"] = str(ledger_path)
    rejected_promotion = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(promotion_order), "--mode", "run", "--events", str(promotion_events), "--result", str(promotion_result)],
        cwd=ROOT,
        env=promotion_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(rejected_promotion.returncode != 0 and "hard floor V2" in rejected_promotion.stderr, "active ledger promotion must reject declared V0")
    assert_case("dispatch_started" not in events_text(promotion_events), "promotion rejection must precede executor launch")
    assert_case(not promotion_result.exists() and not promotion_artifact.exists(), "promotion rejection must not create executor outputs")

    promoted_metadata = dict(
        v0_metadata,
        verificationProfile="V2",
        reviewer="claude-opus-5",
        reasons=["promotion: medium/high escaped V0 defect promotes task class to V2"],
    )
    promotion_payload["notesForExecutor"] = [
        "AQUILA_ROUTING_JSON_V1:" + json.dumps(promoted_metadata, separators=(",", ":"))
    ]
    write_json(promotion_order, promotion_payload)
    promoted_events = promotion_dir / "promoted-events.jsonl"
    accepted_promotion = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(promotion_order), "--validate-only", "--events", str(promoted_events), "--result", str(promotion_result)],
        cwd=ROOT,
        env=promotion_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(accepted_promotion.returncode == 0, f"canonical promoted V2 route must pass: {accepted_promotion.stderr}")
    assert_case("aquila_routing_validated:V2:claude-opus-5:implementation" in events_text(promoted_events), "promoted route must retain the expected reviewer")

    malformed_ledger = promotion_dir / "malformed.jsonl"
    malformed_ledger.write_text("{not-json\n", encoding="utf-8")
    malformed_env = dict(promotion_env)
    malformed_env["AQUILA_ATTEMPT_LEDGER"] = str(malformed_ledger)
    malformed_events = promotion_dir / "malformed-events.jsonl"
    malformed_history = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(promotion_order), "--mode", "run", "--events", str(malformed_events), "--result", str(promotion_result)],
        cwd=ROOT,
        env=malformed_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(malformed_history.returncode != 0 and "attempt ledger load failed" in malformed_history.stderr, "explicit malformed ledger must fail closed")
    assert_case("dispatch_started" not in events_text(malformed_events), "malformed ledger rejection must precede dispatch")

    missing_ledger_env = dict(promotion_env)
    missing_ledger_env["AQUILA_ATTEMPT_LEDGER"] = str(promotion_dir / "missing.jsonl")
    missing_ledger_events = promotion_dir / "missing-ledger-events.jsonl"
    missing_history = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(promotion_order), "--mode", "run", "--events", str(missing_ledger_events), "--result", str(promotion_result)],
        cwd=ROOT,
        env=missing_ledger_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(missing_history.returncode != 0 and "attempt ledger load failed" in missing_history.stderr, "explicit missing ledger must fail closed")
    assert_case("dispatch_started" not in events_text(missing_ledger_events), "missing configured ledger rejection must precede dispatch")
    print("PASS runner consumes locked attempt history, enforces promotion before dispatch, and fails configured ledger errors closed")

    pre_cutover_dir = FIXTURE_ROOT / "pre-cutover-malformed-ledger"
    pre_cutover_dir.mkdir(parents=True)
    pre_cutover_order, pre_cutover_result, _, _, _, pre_cutover_events = make_order(
        pre_cutover_dir,
        "pre-cutover-malformed-ledger",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
    )
    pre_cutover_env = dict(routing_env)
    pre_cutover_env["AQUILA_ATTEMPT_LEDGER"] = str(malformed_ledger)
    pre_cutover = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(pre_cutover_order), "--validate-only", "--events", str(pre_cutover_events), "--result", str(pre_cutover_result)],
        cwd=ROOT,
        env=pre_cutover_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(pre_cutover.returncode == 0, f"pre-cutover order must not require attempt history: {pre_cutover.stderr}")
    assert_case("aquila_attempt_history_loaded" not in events_text(pre_cutover_events), "pre-cutover validation must not load attempt history")

    terminal_dir = FIXTURE_ROOT / "post-cutover-terminal-promotion"
    terminal_dir.mkdir(parents=True)
    terminal_order, terminal_result, terminal_artifact, terminal_stdout, terminal_stderr, terminal_events = make_order(
        terminal_dir,
        "post-cutover-terminal-promotion",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
    )
    terminal_payload = json.loads(terminal_order.read_text(encoding="utf-8"))
    terminal_payload["createdAt"] = "2026-08-03T11:00:42Z"
    terminal_payload["executor"] = "codex"
    terminal_command = shlex.split(terminal_payload["launch"]["command"])
    terminal_command[0] = "codex"
    terminal_payload["launch"]["command"] = shlex.join(terminal_command)
    terminal_metadata = {
        "objectiveId": "runner-terminal-promotion",
        "attempt": 1,
        "taskClass": promoted_task_class,
        "complexity": "low",
        "risk": "low",
        "ambiguity": "low",
        "reversibility": "high",
        "evidenceNeed": "low",
        "executor": "codex",
        "model": "gpt-5.6-sol",
        "reasoningEffort": "high",
        "executionProfile": "terminal_review",
        "verificationProfile": "V1",
        "reviewer": "none",
        "confidence": "high",
        "reasons": ["terminal review fixture"],
        "terminalGate": True,
    }
    terminal_payload["notesForExecutor"] = [
        "AQUILA_ROUTING_JSON_V1:" + json.dumps(terminal_metadata, separators=(",", ":"))
    ]
    write_json(terminal_order, terminal_payload)
    rejected_terminal = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(terminal_order), "--mode", "run", "--events", str(terminal_events), "--result", str(terminal_result)],
        cwd=ROOT,
        env=promotion_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(rejected_terminal.returncode != 0 and "hard floor V2" in rejected_terminal.stderr, "promoted terminal V1 route must fail against active history")
    assert_case("dispatch_started" not in events_text(terminal_events), "promoted terminal rejection must precede dispatch")
    assert_case(not terminal_result.exists() and not terminal_artifact.exists(), "promoted terminal rejection must not create executor outputs")
    assert_case(not terminal_stdout.exists() and not terminal_stderr.exists(), "promoted terminal rejection must not create executor logs")

    terminal_payload["executor"] = "claude"
    terminal_command[0] = "claude"
    terminal_payload["launch"]["command"] = shlex.join(terminal_command)
    promoted_terminal_metadata = dict(
        terminal_metadata,
        executor="claude",
        model="claude-opus-5",
        verificationProfile="V2",
        reasons=["promotion: medium/high escaped V0 defect promotes task class to V2"],
    )
    terminal_payload["notesForExecutor"] = [
        "AQUILA_ROUTING_JSON_V1:" + json.dumps(promoted_terminal_metadata, separators=(",", ":"))
    ]
    write_json(terminal_order, terminal_payload)
    promoted_terminal_events = terminal_dir / "promoted-events.jsonl"
    accepted_terminal = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(terminal_order), "--mode", "run", "--events", str(promoted_terminal_events), "--result", str(terminal_result)],
        cwd=ROOT,
        env=promotion_env,
        check=False,
        text=True,
        capture_output=True,
    )
    promoted_terminal_events_text = events_text(promoted_terminal_events)
    assert_case(accepted_terminal.returncode == 0, f"canonical promoted terminal V2 route must pass: {accepted_terminal.stderr}")
    assert_case("aquila_routing_validated:V2:none:terminal_review" in promoted_terminal_events_text, "promoted terminal route must not appoint a recursive reviewer")
    assert_case(sum("dispatch_started" in line for line in promoted_terminal_events_text.splitlines()) == 1, "promoted terminal V2 route must dispatch exactly once")
    assert_case(terminal_result.exists() and terminal_artifact.exists(), "promoted terminal V2 route must produce executor outputs")

    malformed_terminal_events = terminal_dir / "malformed-ledger-events.jsonl"
    malformed_terminal = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(terminal_order), "--mode", "run", "--events", str(malformed_terminal_events), "--result", str(terminal_result)],
        cwd=ROOT,
        env=malformed_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(malformed_terminal.returncode != 0 and "attempt ledger load failed" in malformed_terminal.stderr, "terminal review must fail closed on an explicit malformed ledger")
    assert_case("dispatch_started" not in events_text(malformed_terminal_events), "malformed terminal ledger rejection must precede dispatch")

    missing_terminal_events = terminal_dir / "missing-ledger-events.jsonl"
    missing_terminal = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(terminal_order), "--mode", "run", "--events", str(missing_terminal_events), "--result", str(terminal_result)],
        cwd=ROOT,
        env=missing_ledger_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(missing_terminal.returncode != 0 and "attempt ledger load failed" in missing_terminal.stderr, "terminal review must fail closed on an explicit missing ledger")
    assert_case("dispatch_started" not in events_text(missing_terminal_events), "missing terminal ledger rejection must precede dispatch")
    print("PASS terminal review consumes attempt history, rejects promoted V1 pre-dispatch, accepts canonical V2 without recursion, and preserves pre-cutover compatibility")

    runner_module = load_runner_module()
    for failure_point in ["chmod", "fdopen"]:
        case_dir = FIXTURE_ROOT / f"lock-{failure_point}-fd-close"
        case_dir.mkdir(parents=True)
        raw_fd = os.open(case_dir / "raw-fd.txt", os.O_RDWR | os.O_CREAT, 0o600)
        lock = runner_module.LoopStateLock(case_dir / "state.json.lock")
        failing_patch = mock.patch.object(runner_module.os, failure_point, side_effect=OSError(f"forced {failure_point} failure"))
        with mock.patch.object(runner_module.os, "open", return_value=raw_fd), failing_patch:
            try:
                lock.acquire()
            except runner_module.RunnerError:
                pass
            else:
                raise AssertionError(f"forced {failure_point} failure must reject lock acquisition")
        try:
            os.fstat(raw_fd)
        except OSError:
            pass
        else:
            os.close(raw_fd)
            raise AssertionError(f"raw fd must close after {failure_point} failure")
    print("PASS raw lock fd closed after chmod and fdopen acquisition failures")

    other_blocked, *_ = run_case(
        "other-executor-without-env",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        allow_other=False,
    )
    assert_case(other_blocked.returncode != 0, "executor other should require opt-in env flag")
    assert_case("AGENT_CONTRACT_RUNNER_ALLOW_OTHER=1" in other_blocked.stderr, "other rejection should cite env flag")
    print("PASS other executor rejected without env flag")

    alias_only, *_ = run_case(
        "output-contract-alias-only",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        output_alias_only=True,
    )
    assert_case(alias_only.returncode != 0, "obsolete output contract alias must be rejected")
    assert_case("must include proseAllowedAfterJson" in alias_only.stderr, "alias rejection should name canonical field")
    assert_case("dispatch_started" not in events_text(FIXTURE_ROOT / "output-contract-alias-only" / "events.jsonl"), "alias rejection must happen before executor launch")
    print("PASS proseAfterJsonAllowed alias-only order rejected")

    prose_type, *_ = run_case(
        "output-contract-prose-boolean",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        prose_allowed_after_json="false",
    )
    assert_case(prose_type.returncode != 0, "proseAllowedAfterJson non-boolean must be rejected")
    assert_case("proseAllowedAfterJson must be boolean" in prose_type.stderr, "proseAllowedAfterJson rejection should cite boolean semantics")
    assert_case("dispatch_started" not in events_text(FIXTURE_ROOT / "output-contract-prose-boolean" / "events.jsonl"), "proseAllowedAfterJson type rejection must happen before launch")
    print("PASS proseAllowedAfterJson semantic boolean enforced")

    structured_argv = ["python3", "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])", "literal-proof.txt", "$(touch shell-interpreted)"]
    structured, _, _, _, _, structured_events = run_case(
        "structured-argv-literal",
        "pass",
        True,
        shlex.join(structured_argv),
        proof_argv=structured_argv,
    )
    structured_dir = FIXTURE_ROOT / "structured-argv-literal"
    assert_case(structured.returncode == 0, f"structured argv proof should pass: {structured.stderr}")
    assert_case((structured_dir / "literal-proof.txt").read_text(encoding="utf-8") == "$(touch shell-interpreted)", "structured argv must pass metacharacters literally")
    assert_case(not (structured_dir / "shell-interpreted").exists(), "structured argv must not invoke a shell")
    assert_case("proof_commands_checked" in events_text(structured_events), "structured argv proof must be checked")
    print("PASS structured argv executes literal metacharacters without shell interpretation")

    argv_mismatch, *_ = run_case(
        "structured-argv-mismatch",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        proof_argv=["python3", "-c", "print(\"different\")"],
    )
    assert_case(argv_mismatch.returncode != 0, "command and argv mismatch must be rejected")
    assert_case("command and proofCommands[0].argv mismatch" in argv_mismatch.stderr, "argv mismatch should identify canonicalization")
    assert_case(not (FIXTURE_ROOT / "structured-argv-mismatch" / "artifact.txt").exists(), "argv mismatch must reject before executor launch")
    print("PASS structured argv mismatch rejected before launch")

    mismatch, *_ = run_case(
        "result-path-mismatch",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        cli_result_path=FIXTURE_ROOT / "result-path-mismatch" / "different-result.json",
    )
    assert_case(mismatch.returncode != 0, "result path mismatch should be rejected")
    assert_case("must resolve to the same path" in mismatch.stderr, "mismatch rejection should cite path equality")
    print("PASS result path mismatch rejected")

    out_artifact = Path("/tmp/agent-contract-runner-outside-artifact.txt")
    out_artifact_rejection, *_ = run_case(
        "out-of-allowed-artifact",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        artifact_path=out_artifact,
    )
    assert_case(out_artifact_rejection.returncode != 0, "out-of-allowed artifact path should be rejected")
    assert_case("expectedArtifacts[0].path is not covered by allowedPaths" in out_artifact_rejection.stderr, "artifact rejection should cite policy")
    print("PASS out-of-allowed artifact path rejected")

    proof_cwd_rejection, *_ = run_case(
        "proof-cwd-outside-workspace",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        proof_cwd=FIXTURE_ROOT,
    )
    assert_case(proof_cwd_rejection.returncode != 0, "proof cwd outside workspace should be rejected")
    assert_case("proofCommands[0].cwd is not covered by allowedPaths" in proof_cwd_rejection.stderr, "proof cwd rejection should cite policy")
    print("PASS proof cwd outside workspace rejected")

    near_miss, *_ = run_case("near-miss-proof-status", "pass_with_finding", True, "python3 -c 'print(\"proof ok\")'")
    assert_case(near_miss.returncode != 0, "near-miss invalid proof.status should be rejected")
    assert_case("proof[0].status" in near_miss.stderr, "near-miss rejection should cite proof status")
    print("PASS near-miss invalid proof.status rejected")

    for result_mode in ("missing", "empty", "unparseable", "stdout_only"):
        malformed, malformed_result, _, _, _, malformed_events = run_case(
            f"launcher-result-{result_mode}",
            "pass",
            True,
            "python3 -c 'print(\"proof ok\")'",
            result_mode=result_mode,
        )
        assert_case(malformed.returncode != 0, f"launcher {result_mode} result must fail")
        assert_case("verification_failed" in events_text(malformed_events), f"launcher {result_mode} failure must be recorded")
        if result_mode in {"missing", "stdout_only"}:
            assert_case(not malformed_result.exists(), "stdout must never substitute for a required result file")
    print("PASS exit 0 plus missing, empty, unparseable, or stdout-only result fails closed")

    malformed_result_modes = {
        "wrong_order": "result orderId does not match order",
        "wrong_executor": "result executor does not match order",
        "files_changed_string": "filesChanged must be a list",
        "self_review_string": "selfReview must be a JSON object",
    }
    for result_mode, expected_error in malformed_result_modes.items():
        malformed, *_ = run_case(
            f"malformed-result-{result_mode}",
            "pass",
            True,
            "python3 -c 'print(\"proof ok\")'",
            result_mode=result_mode,
        )
        assert_case(malformed.returncode != 0 and expected_error in malformed.stderr, f"{result_mode} must fail with a precise error")
    print("PASS wrong identity and malformed filesChanged/selfReview fail result validation")

    missing_artifact, *_ = run_case("missing-required-artifact", "pass", False, "python3 -c 'print(\"proof ok\")'")
    assert_case(missing_artifact.returncode != 0, "missing required artifact should be rejected")
    assert_case("required expectedArtifacts missing" in missing_artifact.stderr, "missing artifact rejection should cite gate")
    print("PASS missing required artifact rejected")

    edgecase_expected_artifacts = [
        {"path": str(FIXTURE_ROOT / "result-artifact-edgecase" / "result.json"), "type": "AGENT_RESULT_JSON_V1 result", "required": True},
        {"path": str(FIXTURE_ROOT / "result-artifact-edgecase" / "artifact.txt"), "type": "fixture", "required": True},
    ]
    result_artifact_edgecase, edgecase_result_path, edgecase_artifact_path, _, _, edgecase_events = run_case(
        "result-artifact-edgecase",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        expected_artifacts=edgecase_expected_artifacts,
    )
    assert_case(result_artifact_edgecase.returncode == 0, f"result-artifact edge case should be accepted: {result_artifact_edgecase.stderr}")
    assert_case(edgecase_result_path.exists(), "result-artifact edge case result should exist")
    assert_case(edgecase_artifact_path.exists(), "result-artifact edge case artifact should exist")
    edgecase_result = json.loads(edgecase_result_path.read_text(encoding="utf-8"))
    assert_case(len(edgecase_result["artifacts"]) == 1, "edge case result should report only artifact.txt")
    assert_case(edgecase_result["artifacts"][0]["path"] == str(edgecase_artifact_path), "edge case result should only report artifact.txt path")
    edgecase_checked = None
    for line in edgecase_events.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "expected_artifacts_checked":
            edgecase_checked = event
            break
    if edgecase_checked is None:
        raise AssertionError("edge case should emit expected_artifacts_checked event")
    result_check = next(item for item in edgecase_checked["artifacts"] if item["path"] == str(edgecase_result_path))
    artifact_check = next(item for item in edgecase_checked["artifacts"] if item["path"] == str(edgecase_artifact_path))
    assert_case(result_check["exists"] is True, "edge case result artifact check should confirm existence")
    assert_case(result_check["reportedByResult"] is False, "edge case result path should remain absent from result.artifacts")
    assert_case(result_check["resultArtifactMatchRequired"] is False, "edge case result path should skip result.artifacts match gate")
    assert_case(artifact_check["reportedByResult"] is True, "edge case non-result artifact should still require result.artifacts match")
    assert_case(artifact_check["resultArtifactMatchRequired"] is True, "edge case non-result artifact should still enforce result.artifacts match")
    print("PASS primary result path skipped for required artifact reporting")

    failing_proof, *_ = run_case(
        "failing-required-proof",
        "pass",
        True,
        "python3 -c 'import sys; print(\"proof failed\"); sys.exit(3)'",
    )
    assert_case(failing_proof.returncode != 0, "failing required proof should be rejected")
    assert_case("required proofCommands failed" in failing_proof.stderr, "failing proof rejection should cite gate")
    print("PASS failing required proof rejected")

    secret_text = "SECRET_TOKEN_SHOULD_NOT_APPEAR"
    secret_expr = "+".join(f"chr({ord(char)})" for char in secret_text)
    secret_case, _, _, _, _, secret_events = run_case(
        "secret-proof-output-redacted",
        "pass",
        True,
        f"python3 -c 'print({secret_expr})'",
    )
    assert_case(secret_case.returncode == 0, f"secret proof case should be accepted: {secret_case.stderr}")
    assert_case(secret_text not in events_text(secret_events), "raw secret-like proof output should not appear in events")
    assert_case('"argv0":"other"' in events_text(secret_events), "events should record argv0 summary")
    assert_case("SECRET" not in events_text(secret_events), "events should not retain secret marker")
    print("PASS proof output redacted from events")

    accepted, _, artifact_path, stdout_path, stderr_path, accepted_events = run_case(
        "canonical-accepted",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
    )
    assert_case(accepted.returncode == 0, f"canonical passing case should be accepted: {accepted.stderr}")
    assert_case(artifact_path.exists(), "canonical artifact should exist")
    assert_case(stdout_path.read_text(encoding="utf-8") == "fake executor stdout\n", "stdout capture should match")
    assert_case(stderr_path.read_text(encoding="utf-8") == "fake executor stderr\n", "stderr capture should match")
    accepted_text = events_text(accepted_events)
    assert_case("fake executor stdout" not in accepted_text, "events should not include raw executor stdout")
    assert_case('"argv":["other"' not in accepted_text, "events should not include full argv")
    print("PASS canonical result plus passing proof accepted")
    print("PASS stdout/stderr capture files written")
    print("PASS events redact raw argv and executor streams")

    salvage, _, salvage_artifact, salvage_stdout, salvage_stderr, salvage_events = run_case(
        "timeout-salvage-accepted",
        "pass",
        True,
        "python3 -c 'print(\"proof ok\")'",
        timeout_seconds=1,
        executor_sleep_seconds=3,
    )
    assert_case(salvage.returncode == 0, f"timeout salvage case should be accepted: {salvage.stderr}")
    assert_case(salvage_artifact.exists(), "timeout salvage artifact should exist")
    assert_case(salvage_stdout.read_text(encoding="utf-8") == "fake executor stdout\n", "salvage stdout capture should match")
    assert_case(salvage_stderr.read_text(encoding="utf-8") == "fake executor stderr\n", "salvage stderr capture should match")
    salvage_event_names = [json.loads(line)["event"] for line in salvage_events.read_text(encoding="utf-8").splitlines()]
    assert_case("dispatch_timed_out" in salvage_event_names, "timeout salvage should record dispatch_timed_out")
    assert_case("salvage_verification_passed" in salvage_event_names, "timeout salvage should record salvage pass")
    print("PASS timeout salvage accepted partial artifacts")

    execute_state = base_loop_state()
    execute_meta = {"loopId": "loop-fixture", "phase": "execute", "workItemId": "item-1", "iteration": 1}
    execute, execute_result, execute_state_path, execute_events = run_loop_fixture("loop-valid-execute", "codex", "execute", execute_state, execute_meta)
    assert_case(execute.returncode == 0, f"valid execute transition should pass: {execute.stderr}")
    written_execute_state = json.loads(execute_state_path.read_text(encoding="utf-8"))
    assert_case(written_execute_state["workItem"]["status"] == "awaiting_verification", "execute must stop at awaiting_verification")
    assert_case(written_execute_state["candidate"]["executor"] == "codex", "execute must record candidate executor")
    print("PASS valid execute transition recorded awaiting_verification")

    v0_order, v0_result, v0_state_path, v0_events, v0_env = make_loop_fixture(
        "loop-v0-deterministic-complete",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
    )
    v0_payload = json.loads(v0_order.read_text(encoding="utf-8"))
    v0_payload["createdAt"] = "2026-08-03T11:00:42Z"
    v0_routing = {
        "objectiveId": "loop-v0-objective",
        "attempt": 1,
        "taskClass": "narrow_regression_fix",
        "complexity": "high",
        "risk": "low",
        "ambiguity": "low",
        "reversibility": "high",
        "evidenceNeed": "low",
        "executor": "codex",
        "model": "gpt-5.6-sol",
        "reasoningEffort": "high",
        "executionProfile": "implementation",
        "verificationProfile": "V0",
        "reviewer": "none",
        "confidence": "high",
        "reasons": ["exact focused regression and local reversible scope"],
        "trustPredicates": {
            "localNarrowBlastRadius": True,
            "cheapReversal": True,
            "deterministicFailureOracle": True,
            "noSensitiveOrExternalSideEffects": True,
            "requiredArtifactsPass": True,
            "requiredProofsPass": True,
            "noUncertainty": True,
            "noScopeOrAssumptionIssues": True,
        },
    }
    v0_payload["notesForExecutor"] = ["AQUILA_ROUTING_JSON_V1:" + json.dumps(v0_routing, separators=(",", ":"))]
    write_json(v0_order, v0_payload)
    v0_completed = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(v0_order), "--mode", "run", "--events", str(v0_events), "--result", str(v0_result)],
        cwd=ROOT,
        env=v0_env,
        check=False,
        text=True,
        capture_output=True,
    )
    v0_state = json.loads(v0_state_path.read_text(encoding="utf-8"))
    assert_case(v0_completed.returncode == 0, f"V0 loop execute should complete deterministically: {v0_completed.stderr}")
    assert_case(v0_state["workItem"]["status"] == "completed", "V0 must complete without awaiting a reviewer")
    assert_case(v0_state["verification"]["verifierExecutor"] == "Aquila", "V0 verifier must be deterministic Aquila proof")
    assert_case(sum('dispatch_started' in line for line in v0_events.read_text(encoding="utf-8").splitlines()) == 1, "V0 must launch only the implementation executor")
    print("PASS V0 loop completes after deterministic proof with no reviewer launch")

    post_dispatch_order, post_dispatch_result, post_dispatch_state_path, post_dispatch_events, post_dispatch_env = make_loop_fixture(
        "loop-post-dispatch-proof-failure",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
    )
    post_dispatch_payload = json.loads(post_dispatch_order.read_text(encoding="utf-8"))
    post_dispatch_payload["proofCommands"][0] = {
        "command": "python3 -c 'import sys; sys.exit(7)'",
        "argv": ["python3", "-c", "import sys; sys.exit(7)"],
        "cwd": str(post_dispatch_state_path.parent),
        "required": True,
    }
    write_json(post_dispatch_order, post_dispatch_payload)
    post_dispatch_launch_count = post_dispatch_state_path.parent / "launch-count.txt"
    post_dispatch_env["FAKE_LAUNCH_COUNT"] = str(post_dispatch_launch_count)
    post_dispatch_cmd = [sys.executable, str(RUNNER), "--order", str(post_dispatch_order), "--mode", "run", "--events", str(post_dispatch_events), "--result", str(post_dispatch_result)]
    post_dispatch_first = subprocess.run(post_dispatch_cmd, cwd=ROOT, env=post_dispatch_env, check=False, text=True, capture_output=True)
    post_dispatch_second = subprocess.run(post_dispatch_cmd, cwd=ROOT, env=post_dispatch_env, check=False, text=True, capture_output=True)
    post_dispatch_state = json.loads(post_dispatch_state_path.read_text(encoding="utf-8"))
    assert_case(post_dispatch_first.returncode != 0, "post-dispatch required proof failure must reject")
    assert_case(post_dispatch_second.returncode != 0, "blocked post-dispatch item must reject redispatch")
    assert_case(post_dispatch_state["workItem"]["status"] == "blocked", "post-dispatch proof failure must atomically block the item")
    assert_case(post_dispatch_state["failures"][-1]["summary"].startswith("required proofCommands failed"), "blocked state must record the proof failure")
    assert_case(post_dispatch_state["transitions"][-1]["from"] == "ready" and post_dispatch_state["transitions"][-1]["to"] == "blocked", "blocked state must record ready-to-blocked transition")
    assert_case(post_dispatch_launch_count.read_text(encoding="utf-8").splitlines() == ["launch"], "post-dispatch proof failure must never auto-redispatch")
    assert_case("aquila_loop_state_blocked_after_dispatch_failure" in events_text(post_dispatch_events), "post-dispatch failure must emit explicit blocked event")
    print("PASS post-dispatch proof failure blocks state and prevents redispatch")

    false_claim_order, false_claim_result, false_claim_state_path, false_claim_events, false_claim_env = make_loop_fixture(
        "loop-artifact-false-for-existing",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
    )
    false_claim_count = false_claim_state_path.parent / "launch-count.txt"
    false_claim_env["FAKE_ARTIFACT_EXISTS_CLAIM"] = "false"
    false_claim_env["FAKE_LAUNCH_COUNT"] = str(false_claim_count)
    false_claim_cmd = [sys.executable, str(RUNNER), "--order", str(false_claim_order), "--mode", "run", "--events", str(false_claim_events), "--result", str(false_claim_result)]
    false_claim_first = subprocess.run(false_claim_cmd, cwd=ROOT, env=false_claim_env, check=False, text=True, capture_output=True)
    false_claim_second = subprocess.run(false_claim_cmd, cwd=ROOT, env=false_claim_env, check=False, text=True, capture_output=True)
    assert_case(false_claim_first.returncode != 0 and "artifact existence mismatch" in false_claim_first.stderr, "false-for-existing artifact claim must fail closed")
    assert_case(false_claim_second.returncode != 0, "artifact mismatch must prevent redispatch")
    assert_case(json.loads(false_claim_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "blocked", "false-for-existing artifact claim must block state")
    assert_case(false_claim_count.read_text(encoding="utf-8").splitlines() == ["launch"], "artifact mismatch must launch executor exactly once")
    print("PASS false-for-existing artifact claim rejected and blocked")

    true_claim_order, true_claim_result, true_claim_state_path, true_claim_events, true_claim_env = make_loop_fixture(
        "loop-artifact-true-for-missing",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
    )
    true_claim_env["FAKE_SKIP_ARTIFACT_WRITE"] = "1"
    true_claim_env["FAKE_ARTIFACT_EXISTS_CLAIM"] = "true"
    true_claim = subprocess.run(
        [sys.executable, str(RUNNER), "--order", str(true_claim_order), "--mode", "run", "--events", str(true_claim_events), "--result", str(true_claim_result)],
        cwd=ROOT,
        env=true_claim_env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert_case(true_claim.returncode != 0 and "artifact existence mismatch" in true_claim.stderr, "true-for-missing artifact claim must fail closed")
    assert_case(json.loads(true_claim_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "blocked", "true-for-missing artifact claim must block state")
    print("PASS true-for-missing artifact claim rejected and blocked")

    timeout_fail_order, timeout_fail_result, timeout_fail_state_path, timeout_fail_events, timeout_fail_env = make_loop_fixture(
        "loop-timeout-salvage-proof-failure",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
        executor_sleep_seconds=3,
    )
    timeout_fail_payload = json.loads(timeout_fail_order.read_text(encoding="utf-8"))
    timeout_fail_payload["launch"]["timeoutSeconds"] = 1
    timeout_fail_payload["proofCommands"][0] = {
        "command": "python3 -c 'import sys; sys.exit(7)'",
        "argv": ["python3", "-c", "import sys; sys.exit(7)"],
        "cwd": str(timeout_fail_state_path.parent),
        "required": True,
    }
    write_json(timeout_fail_order, timeout_fail_payload)
    timeout_fail_count = timeout_fail_state_path.parent / "launch-count.txt"
    timeout_fail_env["FAKE_LAUNCH_COUNT"] = str(timeout_fail_count)
    timeout_fail_cmd = [sys.executable, str(RUNNER), "--order", str(timeout_fail_order), "--mode", "run", "--events", str(timeout_fail_events), "--result", str(timeout_fail_result)]
    timeout_fail_first = subprocess.run(timeout_fail_cmd, cwd=ROOT, env=timeout_fail_env, check=False, text=True, capture_output=True)
    timeout_fail_second = subprocess.run(timeout_fail_cmd, cwd=ROOT, env=timeout_fail_env, check=False, text=True, capture_output=True)
    assert_case(timeout_fail_first.returncode != 0, "failed timeout salvage verification must reject")
    assert_case(timeout_fail_second.returncode != 0, "failed timeout salvage must prevent redispatch")
    assert_case(json.loads(timeout_fail_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "blocked", "failed timeout salvage must block state")
    assert_case(timeout_fail_count.read_text(encoding="utf-8").splitlines() == ["launch"], "failed timeout salvage must launch executor exactly once")
    assert_case("salvage_verification_failed" in events_text(timeout_fail_events), "failed timeout salvage event must be recorded")
    print("PASS failed timeout salvage blocks state and prevents redispatch")

    stream_capture_order, stream_capture_result, stream_capture_state_path, stream_capture_events, stream_capture_env = make_loop_fixture(
        "loop-stream-capture-permission-error",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
    )
    stream_capture_payload = json.loads(stream_capture_order.read_text(encoding="utf-8"))
    stream_capture_parent = stream_capture_state_path.parent / "captured-streams"
    stream_capture_stdout = stream_capture_parent / "stdout.log"
    stream_capture_parent.mkdir()
    stream_capture_payload["launch"]["stdoutPath"] = str(stream_capture_stdout)
    stream_capture_payload["allowedPaths"].append(str(stream_capture_stdout))
    write_json(stream_capture_order, stream_capture_payload)
    stream_capture_count = stream_capture_state_path.parent / "launch-count.txt"
    stream_capture_env["FAKE_LAUNCH_COUNT"] = str(stream_capture_count)
    stream_capture_cmd = [sys.executable, str(RUNNER), "--order", str(stream_capture_order), "--mode", "run", "--events", str(stream_capture_events), "--result", str(stream_capture_result)]
    stream_capture_parent.chmod(0o500)
    try:
        stream_capture_first = subprocess.run(stream_capture_cmd, cwd=ROOT, env=stream_capture_env, check=False, text=True, capture_output=True)
        stream_capture_second = subprocess.run(stream_capture_cmd, cwd=ROOT, env=stream_capture_env, check=False, text=True, capture_output=True)
    finally:
        stream_capture_parent.chmod(0o700)
    stream_capture_state = json.loads(stream_capture_state_path.read_text(encoding="utf-8"))
    stream_capture_event_text = events_text(stream_capture_events)
    expected_capture_error = f"stream capture failed for launch.stdoutPath at {stream_capture_stdout}: [Errno 13] {os.strerror(13)}"
    assert_case(stream_capture_first.returncode != 0 and expected_capture_error in stream_capture_first.stderr, "post-dispatch stream capture OSError must be reported as RunnerError")
    assert_case(stream_capture_second.returncode != 0, "stream capture failure must prevent redispatch")
    assert_case(stream_capture_state["workItem"]["status"] == "blocked", "stream capture failure must block state")
    assert_case(stream_capture_state["failures"][-1]["summary"] == expected_capture_error, "stream capture failure summary must be recorded")
    assert_case(stream_capture_state["transitions"][-1]["to"] == "blocked", "stream capture failure transition must be recorded")
    assert_case(stream_capture_count.read_text(encoding="utf-8").splitlines() == ["launch"], "stream capture failure must launch executor exactly once")
    assert_case("aquila_loop_state_blocked_after_dispatch_failure" in stream_capture_event_text, "stream capture failure must record explicit blocked event")
    assert_case("fake executor stdout" not in stream_capture_first.stderr and "fake executor stderr" not in stream_capture_first.stderr, "stream capture error must not disclose captured streams")
    assert_case("fake executor stdout" not in stream_capture_event_text and "fake executor stderr" not in stream_capture_event_text, "stream capture events must not disclose captured streams")
    print("PASS stream capture PermissionError blocks state and prevents redispatch")

    start_error_order, start_error_result, start_error_state_path, start_error_events, start_error_env = make_loop_fixture(
        "loop-launch-oserror-retryable",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
    )
    start_error_payload = json.loads(start_error_order.read_text(encoding="utf-8"))
    retry_command = start_error_payload["launch"]["command"]
    missing_argv = shlex.split(retry_command)
    missing_argv[0] = "/definitely/missing/codex"
    start_error_payload["launch"]["command"] = shlex.join(missing_argv)
    write_json(start_error_order, start_error_payload)
    start_error_count = start_error_state_path.parent / "launch-count.txt"
    start_error_env["FAKE_LAUNCH_COUNT"] = str(start_error_count)
    start_error_cmd = [sys.executable, str(RUNNER), "--order", str(start_error_order), "--mode", "run", "--events", str(start_error_events), "--result", str(start_error_result)]
    start_error_first = subprocess.run(start_error_cmd, cwd=ROOT, env=start_error_env, check=False, text=True, capture_output=True)
    start_error_state = json.loads(start_error_state_path.read_text(encoding="utf-8"))
    assert_case(start_error_first.returncode != 0 and "failed to start" in start_error_first.stderr, "pre-child OSError must be reported")
    assert_case(start_error_state["workItem"]["status"] == "ready", "pre-child OSError must leave state retryable")
    assert_case(not start_error_count.exists(), "pre-child OSError must not count as an executor launch")
    start_error_payload["launch"]["command"] = retry_command
    write_json(start_error_order, start_error_payload)
    start_error_retry = subprocess.run(start_error_cmd, cwd=ROOT, env=start_error_env, check=False, text=True, capture_output=True)
    assert_case(start_error_retry.returncode == 0, f"operator-controlled retry after pre-child OSError must succeed: {start_error_retry.stderr}")
    assert_case(json.loads(start_error_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "awaiting_verification", "successful retry must advance normally")
    assert_case(start_error_count.read_text(encoding="utf-8").splitlines() == ["launch"], "retry path must launch exactly one real child")
    print("PASS pre-child OSError leaves ready state and releases lock for retry")

    loop_command_only, _, _, loop_command_only_events = run_loop_fixture(
        "loop-command-only-proof",
        "codex",
        "execute",
        base_loop_state(),
        execute_meta,
        structured_proof=False,
    )
    assert_case(loop_command_only.returncode != 0, "Loop V1 command-only proof must be rejected")
    assert_case("argv is required for Loop V1 proof commands" in loop_command_only.stderr, "Loop command-only rejection should cite argv")
    assert_case("dispatch_started" not in events_text(loop_command_only_events), "Loop command-only rejection must precede dispatch")
    print("PASS Loop V1 command-only proof rejected before launch")

    verify_state = written_execute_state
    verify_meta = {"loopId": "loop-fixture", "phase": "verify", "workItemId": "item-1", "iteration": 1, "verdict": "pass"}
    verify, _, verify_state_path, verify_events = run_loop_fixture("loop-valid-verify", "claude", "verify", verify_state, verify_meta)
    assert_case(verify.returncode == 0, f"valid independent verify transition should pass: {verify.stderr}")
    verified_state = json.loads(verify_state_path.read_text(encoding="utf-8"))
    assert_case(verified_state["workItem"]["status"] == "completed", "verifier pass with no pending work must complete")
    assert_case(verified_state["verification"]["verdict"] == "pass", "verifier verdict must be controller-recorded")
    assert_case(sum('dispatch_started' in line for line in verify_events.read_text(encoding="utf-8").splitlines()) == 1, "verify must dispatch exactly once")
    print("PASS valid independent verify transition completed item")

    expired_verify_state = dict(written_execute_state)
    expired_verify_state["budgets"] = dict(expired_verify_state["budgets"])
    expired_verify_state["budgets"]["startedAt"] = "2020-01-01T00:00:00Z"
    expired_verify, _, expired_verify_state_path, _ = run_loop_fixture("loop-verify-after-wall-expiry", "claude", "verify", expired_verify_state, verify_meta)
    assert_case(expired_verify.returncode == 0, f"accepted candidate should still be verifiable after wall expiry: {expired_verify.stderr}")
    assert_case(json.loads(expired_verify_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "completed", "expired verify must preserve independent completion")
    print("PASS accepted candidate independently verified after wall-time expiry")

    pending_execute_state = base_loop_state(pending=["item-2"])
    pending_execute, _, pending_execute_state_path, _ = run_loop_fixture("loop-pending-execute", "codex", "execute", pending_execute_state, execute_meta)
    assert_case(pending_execute.returncode == 0, f"execute with pending work should pass: {pending_execute.stderr}")
    pending_awaiting_state = json.loads(pending_execute_state_path.read_text(encoding="utf-8"))
    pending_verify, _, pending_verify_state_path, _ = run_loop_fixture("loop-pending-verify", "claude", "verify", pending_awaiting_state, verify_meta)
    assert_case(pending_verify.returncode == 0, f"verify with pending work should pass: {pending_verify.stderr}")
    pending_verified_state = json.loads(pending_verify_state_path.read_text(encoding="utf-8"))
    assert_case(pending_verified_state["workItem"]["status"] == "completed", "verifier pass must complete the current item when pending work remains")
    assert_case(pending_verified_state["workItem"]["pendingWorkItems"] == ["item-2"], "verifier pass must preserve pending work")
    reexecute, reexecute_result_path, _, reexecute_events = run_loop_fixture("loop-completed-current-reexecute", "codex", "execute", pending_verified_state, execute_meta)
    assert_case(reexecute.returncode != 0, "completed current item must reject immediate execute before dispatch")
    assert_case("requires loop state ready" in reexecute.stderr, "completed-item rejection should require explicit Aquila ready selection")
    assert_case(not reexecute_result_path.exists(), "completed-item rejection must not produce a result")
    assert_case(not (FIXTURE_ROOT / "loop-completed-current-reexecute" / "artifact.txt").exists(), "completed-item rejection must not launch fake executor")
    assert_case("dispatch_started" not in events_text(reexecute_events), "completed-item rejection must not emit dispatch_started")
    print("PASS pending work preserved while current item completed and immediate execute rejected")

    same_state = dict(verify_state)
    same_state["workItem"] = dict(same_state["workItem"])
    same_state["workItem"]["status"] = "awaiting_verification"
    same, _, _, _ = run_loop_fixture("loop-same-executor", "codex", "verify", same_state, verify_meta)
    assert_case(same.returncode != 0, "same-executor verification must be rejected before dispatch")
    assert_case("different from candidate" in same.stderr or "same-executor" in same.stderr or "verifier executor" in same.stderr, "same-executor rejection should be explicit")
    print("PASS same-executor self-verification rejected")

    scope_state = base_loop_state()
    scoped, _, _, _ = run_loop_fixture("loop-state-write-scope", "codex", "execute", scope_state, execute_meta, allowed_state=True)
    assert_case(scoped.returncode != 0, "statePath in executor allowedPaths must be rejected")
    assert_case("outside executor allowedPaths" in scoped.stderr, "statePath scope rejection should be explicit")
    print("PASS statePath write-scope rejection")

    mismatch_state = base_loop_state()
    mismatch, _, _, _ = run_loop_fixture("loop-state-mismatch", "codex", "execute", mismatch_state, execute_meta, state_loop_id="other-loop")
    assert_case(mismatch.returncode != 0, "loop/state mismatch must be rejected")
    assert_case("loop/state loopId mismatch" in mismatch.stderr, "loop/state mismatch should identify loopId")
    print("PASS loop/state mismatch rejected")

    final_iteration_state = base_loop_state(current=3)
    final_iteration_meta = {"loopId": "loop-fixture", "phase": "execute", "workItemId": "item-1", "iteration": 3}
    final_iteration, _, final_iteration_state_path, final_iteration_events = run_loop_fixture("loop-final-iteration", "codex", "execute", final_iteration_state, final_iteration_meta)
    assert_case(final_iteration.returncode == 0, f"current == max must remain dispatchable: {final_iteration.stderr}")
    final_iteration_written = json.loads(final_iteration_state_path.read_text(encoding="utf-8"))
    assert_case(final_iteration_written["workItem"]["status"] == "awaiting_verification", "final allowed iteration must record awaiting_verification")
    assert_case(sum('dispatch_started' in line for line in final_iteration_events.read_text(encoding="utf-8").splitlines()) == 1, "final allowed iteration must dispatch exactly once")
    print("PASS inclusive final iteration dispatched")

    over_budget_state = base_loop_state(current=4)
    over_budget_meta = {"loopId": "loop-fixture", "phase": "execute", "workItemId": "item-1", "iteration": 4}
    over_budget, over_budget_result_path, _, over_budget_events = run_loop_fixture("loop-over-budget", "codex", "execute", over_budget_state, over_budget_meta)
    assert_case(over_budget.returncode != 0, "current == max + 1 must reject before launch")
    assert_case("cannot exceed max" in over_budget.stderr or "budget exhausted" in over_budget.stderr, "over-budget rejection should identify the iteration boundary")
    assert_case(not over_budget_result_path.exists(), "over-budget rejection must not produce a result")
    assert_case(not (FIXTURE_ROOT / "loop-over-budget" / "artifact.txt").exists(), "over-budget rejection must not launch fake executor")
    assert_case("dispatch_started" not in events_text(over_budget_events), "over-budget rejection must not emit dispatch_started")
    print("PASS iteration max plus one rejected before fake launch")

    expired_execute_state = base_loop_state(started_at="2000-01-01T00:00:00Z", max_wall_seconds=1)
    expired_execute, expired_execute_result, expired_execute_state_path, expired_execute_events = run_loop_fixture(
        "loop-execute-wall-time-expired",
        "codex",
        "execute",
        expired_execute_state,
        execute_meta,
    )
    assert_case(expired_execute.returncode != 0, "expired execute wall-time must reject before launch")
    assert_case("wall-time budget exhausted" in expired_execute.stderr, "expired execute rejection must identify wall-time")
    assert_case(json.loads(expired_execute_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "ready", "expired execute preflight must leave state unchanged")
    assert_case(not expired_execute_result.exists(), "expired execute preflight must not produce a result")
    assert_case("dispatch_started" not in events_text(expired_execute_events), "expired execute preflight must not dispatch")
    print("PASS expired execute wall-time rejected before launch")

    unexpired_started_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    unexpired_execute_state = base_loop_state(started_at=unexpired_started_at, max_wall_seconds=3600)
    unexpired_execute, _, unexpired_execute_state_path, unexpired_execute_events = run_loop_fixture(
        "loop-execute-wall-time-unexpired",
        "codex",
        "execute",
        unexpired_execute_state,
        execute_meta,
    )
    assert_case(unexpired_execute.returncode == 0, f"comfortably unexpired execute wall-time must remain accepted: {unexpired_execute.stderr}")
    assert_case(json.loads(unexpired_execute_state_path.read_text(encoding="utf-8"))["workItem"]["status"] == "awaiting_verification", "unexpired execute must advance normally")
    assert_case("dispatch_started" in events_text(unexpired_execute_events), "unexpired execute must dispatch")
    print("PASS comfortably unexpired execute wall-time accepted")

    malformed_state = written_execute_state
    malformed, _, _, _ = run_loop_fixture("loop-malformed-verifier", "claude", "verify", malformed_state, {"loopId": "loop-fixture", "phase": "verify", "workItemId": "item-1", "iteration": 1})
    assert_case(malformed.returncode != 0, "malformed verifier metadata must be rejected")
    assert_case("verdict" in malformed.stderr, "malformed verifier metadata should cite verdict")
    print("PASS malformed verifier metadata rejected")

    stale_order, stale_result, stale_state_path, stale_events, stale_env = make_loop_fixture("loop-stale-sidecar", "codex", "execute", base_loop_state(), execute_meta)
    stale_lock = stale_state_path.with_name(stale_state_path.name + ".lock")
    stale_lock.write_text("stale controller marker\n", encoding="utf-8")
    stale_completed = subprocess.run([sys.executable, str(RUNNER), "--order", str(stale_order), "--mode", "run", "--events", str(stale_events), "--result", str(stale_result)], cwd=ROOT, env=stale_env, check=False, text=True, capture_output=True)
    assert_case(stale_completed.returncode == 0, f"stale sidecar file must not block lock acquisition: {stale_completed.stderr}")
    print("PASS stale sidecar file recovered through OS lock acquisition")

    concurrent_order, concurrent_result, concurrent_state_path, concurrent_events, concurrent_env = make_loop_fixture("loop-concurrent-lock", "codex", "execute", base_loop_state(), execute_meta, executor_sleep_seconds=1)
    concurrent_case_dir = concurrent_state_path.parent
    launch_count = concurrent_case_dir / "launch-count.txt"
    concurrent_env["FAKE_LAUNCH_COUNT"] = str(launch_count)
    second_events = concurrent_case_dir / "events-second.jsonl"
    concurrent_order_payload = json.loads(concurrent_order.read_text(encoding="utf-8"))
    concurrent_order_payload["allowedPaths"].append(str(second_events))
    write_json(concurrent_order, concurrent_order_payload)
    concurrent_cmd = [sys.executable, str(RUNNER), "--order", str(concurrent_order), "--mode", "run", "--events", str(concurrent_events), "--result", str(concurrent_result)]
    first = subprocess.Popen(concurrent_cmd, cwd=ROOT, env=concurrent_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.2)
    second_cmd = list(concurrent_cmd)
    second_cmd[second_cmd.index("--events") + 1] = str(second_events)
    second = subprocess.run(second_cmd, cwd=ROOT, env=concurrent_env, check=False, text=True, capture_output=True)
    first_stdout, first_stderr = first.communicate(timeout=10)
    assert_case(first.returncode == 0, f"first concurrent controller should complete: {first_stderr}")
    assert_case(second.returncode != 0, "second concurrent controller must fail closed")
    assert_case("already held" in second.stderr, "second concurrent controller should report active lock")
    assert_case(launch_count.read_text(encoding="utf-8").splitlines() == ["launch"], "concurrent controllers must launch exactly one fake executor")
    assert_case("dispatch_started" not in events_text(second_events), "lock contention must happen before second dispatch")
    print("PASS concurrent same-state dispatch serialized to one executor launch")

    dry_order, dry_result, dry_state_path, dry_events, dry_env = make_loop_fixture("loop-dry-run-no-lock", "codex", "execute", base_loop_state(), execute_meta)
    dry_lock = dry_state_path.with_name(dry_state_path.name + ".lock")
    dry_completed = subprocess.run([sys.executable, str(RUNNER), "--order", str(dry_order), "--mode", "dry-run", "--events", str(dry_events), "--result", str(dry_result)], cwd=ROOT, env=dry_env, check=False, text=True, capture_output=True)
    assert_case(dry_completed.returncode == 0, f"dry-run should remain non-dispatching: {dry_completed.stderr}")
    assert_case(not dry_lock.exists(), "dry-run must not leave a lock file")
    print("PASS dry-run remains non-dispatching without a held lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
