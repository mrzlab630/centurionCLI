#!/usr/bin/env python3
"""Regression checks for the controller-owned Codex and Claude Result Gateway."""

from __future__ import annotations

import atexit
import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCRIPT_ROOT = Path(__file__).resolve().parent
GATEWAY = SCRIPT_ROOT / "result_gateway.py"
SCHEMA = SCRIPT_ROOT.parent / "references" / "agent-result.schema.json"
ROOT = Path(tempfile.mkdtemp(prefix="result-gateway-regression-"))
atexit.register(shutil.rmtree, ROOT, ignore_errors=True)


def monitor_path() -> Path:
    kit_or_home = SCRIPT_ROOT.parents[3]
    candidates = [
        kit_or_home / "runtime" / "bin" / "monitor-delegation.sh",
        kit_or_home / "bin" / "monitor-delegation.sh",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("packaged monitor-delegation.sh was not found")


MONITOR = monitor_path()
BIN = ROOT / "bin"
COUNT = ROOT / "launch-count.txt"
ROUTING_PREFIX = "AQUILA_ROUTING_JSON_V1:"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def routing_metadata(order_id: str, executor: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "objectiveId": order_id,
        "attempt": 1,
        "taskClass": "result_gateway_regression",
        "complexity": "medium",
        "risk": "low",
        "ambiguity": "low",
        "reversibility": "high",
        "evidenceNeed": "high",
        "executor": executor,
        "model": "claude-opus-5" if executor == "claude" else "gpt-5.6-terra",
        "reasoningEffort": "medium",
        "executionProfile": "implementation",
        "verificationProfile": "V1",
        "reviewer": "gpt-5.6-sol",
        "confidence": "high",
        "reasons": ["deterministic gateway regression proof"],
    }
    payload.update(overrides)
    return payload


def set_routing(order: dict[str, Any], routing: dict[str, Any]) -> None:
    order["notesForExecutor"] = [ROUTING_PREFIX + json.dumps(routing, separators=(",", ":"))]


def routing_digest(routing: dict[str, Any]) -> str:
    canonical = json.dumps(routing, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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


def valid_result(order_id: str, executor: str, status: str = "done") -> dict[str, Any]:
    return {
        "resultVersion": "AGENT_RESULT_JSON_V1",
        "orderId": order_id,
        "executor": executor,
        "status": status,
        "summary": f"fixture result remains {status}",
        "filesChanged": [],
        "artifacts": [{"path": str(COUNT), "exists": True, "type": "fixture", "note": "launch count"}],
        "proof": [{"command": "fixture proof", "cwd": str(ROOT), "status": "pass", "exitCode": 0, "summary": "fixture"}],
        "selfReview": {"performed": True, "findings": [], "fixesApplied": []},
        "scopeDeviations": [],
        "forbiddenPatternHits": [],
        "remainingRisks": [],
        "questions": [],
        "errors": [],
        "stdoutSummary": "",
        "stderrSummary": "",
    }


def install_fake_executors() -> None:
    BIN.mkdir(parents=True)
    source = """#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

mode, candidate_value, order_id, executor, status, side_effect_value, sleep_value, exit_value = sys.argv[1:]
candidate = Path(candidate_value)
side_effect = Path(side_effect_value) if side_effect_value != "NONE" else None
count = Path(os.environ["RESULT_GATEWAY_TEST_COUNT"])
count.parent.mkdir(parents=True, exist_ok=True)
with count.open("a", encoding="utf-8") as handle:
    handle.write("launch\\n")
if mode == "escaped-grandchild":
    pid = os.fork()
    if pid == 0:
        os.setsid()
        time.sleep(4)
        os._exit(0)
if side_effect is not None:
    side_effect.parent.mkdir(parents=True, exist_ok=True)
    with side_effect.open("a", encoding="utf-8") as handle:
        handle.write("effect\\n")
payload = {
    "resultVersion": "AGENT_RESULT_JSON_V1", "orderId": order_id, "executor": executor,
    "status": status, "summary": f"fixture result remains {status}", "filesChanged": [],
    "artifacts": [{"path": str(count), "exists": True, "type": "fixture", "note": "launch count"}],
    "proof": [{"command": "fixture proof", "cwd": str(count.parent), "status": "pass", "exitCode": 0, "summary": "fixture"}],
    "selfReview": {"performed": True, "findings": [], "fixesApplied": []},
    "scopeDeviations": [], "forbiddenPatternHits": [], "remainingRisks": [], "questions": [], "errors": [],
    "stdoutSummary": "", "stderrSummary": ""
}
candidate.parent.mkdir(parents=True, exist_ok=True)
if mode.startswith("stdout-"):
    stdout_mode = mode.removeprefix("stdout-")
    if stdout_mode == "valid":
        output = json.dumps(payload, indent=2, sort_keys=True) + "\\n"
    elif stdout_mode == "malformed":
        output = "{not-json"
    elif stdout_mode == "fenced":
        output = "```json\\n" + json.dumps(payload) + "\\n```\\n"
    elif stdout_mode == "truncated":
        output = json.dumps(payload)[:41]
    elif stdout_mode == "partial":
        output = json.dumps({"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": order_id})
    elif stdout_mode == "wrong-order":
        payload["orderId"] = "wrong-order-id"
        output = json.dumps(payload)
    elif stdout_mode == "wrong-executor":
        payload["executor"] = "codex"
        output = json.dumps(payload)
    elif stdout_mode == "prose":
        output = "result follows\\n" + json.dumps(payload)
    elif stdout_mode == "envelope":
        output = json.dumps({"type": "result", "content": payload})
    elif stdout_mode == "multiple":
        output = json.dumps(payload) + "\\n" + json.dumps(payload)
    elif stdout_mode == "duplicate-key":
        output = json.dumps(payload).replace('"status": "' + status + '"', '"status": "failed", "status": "' + status + '"', 1)
    elif stdout_mode in {"non-finite", "infinity", "negative-infinity", "overflow-non-finite"}:
        literal = {
            "non-finite": "NaN",
            "infinity": "Infinity",
            "negative-infinity": "-Infinity",
            "overflow-non-finite": "1e999",
        }[stdout_mode]
        output = json.dumps(payload)[:-1] + ', "extra": ' + literal + '}'
    elif stdout_mode == "timeout-partial":
        output = "{\\\"resultVersion\\\":"
    else:
        raise SystemExit(f"unknown stdout mode: {stdout_mode}")
    print(output, end="", flush=True)
else:
    if mode in {"valid", "early", "capture-oserror", "event-failure"}:
        candidate.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    elif mode == "malformed":
        candidate.write_text("{not-json", encoding="utf-8")
    elif mode == "fenced":
        candidate.write_text("```json\\n" + json.dumps(payload) + "\\n```\\n", encoding="utf-8")
    elif mode == "truncated":
        candidate.write_text(json.dumps(payload)[:41], encoding="utf-8")
    elif mode == "partial":
        candidate.write_text(json.dumps({"resultVersion": "AGENT_RESULT_JSON_V1", "orderId": order_id}), encoding="utf-8")
    elif mode == "wrong-order":
        payload["orderId"] = "wrong-order-id"
        candidate.write_text(json.dumps(payload), encoding="utf-8")
    elif mode == "wrong-executor":
        payload["executor"] = "claude" if executor == "codex" else "codex"
        candidate.write_text(json.dumps(payload), encoding="utf-8")
    elif mode == "duplicate-key":
        output = json.dumps(payload).replace('"status": "' + status + '"', '"status": "failed", "status": "' + status + '"', 1)
        candidate.write_text(output, encoding="utf-8")
    elif mode in {"non-finite", "infinity", "negative-infinity", "overflow-non-finite"}:
        literal = {
            "non-finite": "NaN",
            "infinity": "Infinity",
            "negative-infinity": "-Infinity",
            "overflow-non-finite": "1e999",
        }[mode]
        candidate.write_text(json.dumps(payload)[:-1] + ', "extra": ' + literal + '}', encoding="utf-8")
    elif mode == "timeout-partial":
        candidate.write_text("{\\\"resultVersion\\\":", encoding="utf-8")
    print("fixture stdout", flush=True)
print("fixture stderr", file=sys.stderr, flush=True)
if mode == "capture-oserror":
    (candidate.parent / "capture").chmod(0o500)
    (candidate.parent / "evidence").chmod(0o500)
if mode == "event-failure":
    (candidate.parent / "events.jsonl").chmod(0o400)
time.sleep(float(sleep_value))
raise SystemExit(int(exit_value))
"""
    for name in ("codex", "claude"):
        path = BIN / name
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)


def make_case(
    name: str,
    mode: str,
    *,
    executor: str = "codex",
    status: str = "done",
    sleep_seconds: float = 0,
    exit_code: int = 0,
    timeout_seconds: int = 3,
    side_effect: bool = False,
    bad_stdout_parent: bool = False,
    separate_stdout_parent: bool = False,
    candidate_source: str = "file",
) -> dict[str, Path | dict[str, str]]:
    case = ROOT / name
    case.mkdir(parents=True)
    candidate = case / "candidate.json"
    result = case / "result.json"
    start_receipt = case / "start.json"
    closure = case / "closure.json"
    evidence = case / "evidence"
    events = case / "events.jsonl"
    stdout = case / "stdout.log"
    stderr = case / "stderr.log"
    if bad_stdout_parent:
        blocker = case / "not-a-directory"
        blocker.write_text("blocker\n", encoding="utf-8")
        stdout = blocker / "stdout.log"
    if separate_stdout_parent:
        capture = case / "capture"
        capture.mkdir()
        stdout = capture / "stdout.log"
    evidence.mkdir()
    side_effect_path = case / "side-effect.txt" if side_effect else Path("NONE")
    order_id = f"gateway-{name}"
    command = [executor, mode, str(candidate), order_id, executor, status, str(side_effect_path), str(sleep_seconds), str(exit_code)]
    order = {
        "orderVersion": "AGENT_ORDER_JSON_V1",
        "orderId": order_id,
        "createdAt": "2026-08-03T11:00:42Z",
        "controller": "Aquila",
        "executor": executor,
        "roleForTask": "result gateway regression fixture",
        "riskLevel": "low",
        "workspace": {"repoPath": str(ROOT), "branchOrWorktree": "fixture", "projectName": "gateway regression"},
        "launch": {
            "surface": "fixture",
            "command": " ".join(subprocess.list2cmdline([part]) for part in command),
            "timeoutSeconds": timeout_seconds,
            "resultJsonPath": str(result),
            "stdoutPath": str(stdout),
            "stderrPath": str(stderr),
        },
        "objective": "exercise the result gateway",
        "context": [],
        "allowedPaths": [str(ROOT / "**")],
        "forbiddenPaths": [],
        "forbiddenActions": [],
        "nonGoals": [],
        "acceptanceCriteria": ["gateway behavior is deterministic"],
        "expectedArtifacts": [],
        "proofCommands": [],
        "outputContract": {"resultVersion": "AGENT_RESULT_JSON_V1", "resultPath": str(result), "stdoutAllowed": True, "proseAllowedAfterJson": False},
        "stopConditions": [],
        "notesForExecutor": [],
    }
    set_routing(order, routing_metadata(order_id, executor))
    order_path = case / "order.json"
    write_json(order_path, order)
    return {
        "case": case,
        "order": order_path,
        "candidate": candidate,
        "result": result,
        "start_receipt": start_receipt,
        "closure": closure,
        "evidence": evidence,
        "events": events,
        "stdout": stdout,
        "stderr": stderr,
        "side_effect": side_effect_path,
        "candidate_source": candidate_source,
    }


def gateway_command(
    paths: dict[str, Path | dict[str, str]],
    *,
    explicit_schema: bool = True,
    grace_seconds: str = "0.2",
) -> list[str]:
    command = [
        sys.executable,
        str(GATEWAY),
        "--order", str(paths["order"]),
        "--candidate", str(paths["candidate"]),
        "--candidate-source", str(paths["candidate_source"]),
        "--start-receipt", str(paths["start_receipt"]),
        "--closure", str(paths["closure"]),
        "--evidence-dir", str(paths["evidence"]),
        "--events", str(paths["events"]),
        "--termination-grace-seconds", grace_seconds,
    ]
    if explicit_schema:
        command.extend(["--schema", str(SCHEMA)])
    return command


def environment() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = f"{BIN}{os.pathsep}{env.get('PATH', '')}"
    env["RESULT_GATEWAY_TEST_COUNT"] = str(COUNT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HOME"] = str(ROOT / "isolated-home")
    env.pop("AQUILA_ATTEMPT_LEDGER", None)
    return env


def run_gateway(
    paths: dict[str, Path | dict[str, str]],
    *,
    explicit_schema: bool = True,
    grace_seconds: str = "0.2",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        gateway_command(paths, explicit_schema=explicit_schema, grace_seconds=grace_seconds),
        cwd=ROOT,
        env=environment(),
        text=True,
        capture_output=True,
        check=False,
    )


def run_monitor(paths: dict[str, Path | dict[str, str]], *, explicit_schema: bool = True) -> subprocess.CompletedProcess[str]:
    command = [
        "bash", str(MONITOR),
        "--order", str(paths["order"]),
        "--result", str(paths["result"]),
        "--start-receipt", str(paths["start_receipt"]),
        "--closure", str(paths["closure"]),
    ]
    if explicit_schema:
        command.extend(["--schema", str(SCHEMA)])
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment(),
        text=True,
        capture_output=True,
        check=False,
    )


def load_valid_result(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(value)
    return value


def launch_count() -> int:
    return len(COUNT.read_text(encoding="utf-8").splitlines()) if COUNT.exists() else 0


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def rewrite_order(paths: dict[str, Path | dict[str, str]], mutator: Any) -> dict[str, Any]:
    order = read_json(Path(paths["order"]))
    mutator(order)
    write_json(Path(paths["order"]), order)
    return order


def assert_preflight_rejection(
    paths: dict[str, Path | dict[str, str]],
    *,
    grace_seconds: str = "0.2",
    preexisting_key: str | None = None,
) -> subprocess.CompletedProcess[str]:
    terminal_keys = ("candidate", "stdout", "stderr", "result", "start_receipt", "closure")
    assert preexisting_key is None or preexisting_key in terminal_keys
    preexisting_path = Path(paths[preexisting_key]) if preexisting_key is not None else None
    preexisting_bytes = preexisting_path.read_bytes() if preexisting_path is not None else None
    absent_before = {
        key: not Path(paths[key]).exists()
        for key in terminal_keys
        if key != preexisting_key
    }
    before = launch_count()
    completed = run_gateway(paths, grace_seconds=grace_seconds)
    assert completed.returncode != 0
    assert launch_count() == before
    if preexisting_path is not None:
        assert preexisting_path.read_bytes() == preexisting_bytes
    for key, was_absent in absent_before.items():
        if was_absent:
            assert not Path(paths[key]).exists(), f"preflight rejection created unexpected {key} artifact"
    return completed


def completed_case(name: str) -> dict[str, Path | dict[str, str]]:
    case = make_case(name, "valid")
    completed = run_gateway(case)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert run_monitor(case).returncode == 0
    return case


def main() -> int:
    if sys.flags.optimize:
        print("FAIL regression_result_gateway.py requires assertions; PYTHONOPTIMIZE is not allowed", file=sys.stderr)
        return 1
    install_fake_executors()

    missing = make_case("exit-zero-missing", "missing")
    completed = run_gateway(missing)
    assert completed.returncode != 0
    assert load_valid_result(missing["result"])["status"] == "failed"
    monitored = run_monitor(missing)
    assert monitored.returncode == 0
    assert "terminal-closure-verified" in monitored.stdout
    start = read_json(Path(missing["start_receipt"]))
    closure = read_json(Path(missing["closure"]))
    order = read_json(Path(missing["order"]))
    expected_routing = json.loads(order["notesForExecutor"][0][len(ROUTING_PREFIX):])
    expected_routing_digest = routing_digest(expected_routing)
    assert start["runId"] == closure["runId"]
    assert start["orderSha256"] == closure["orderSha256"] == hashlib.sha256(Path(missing["order"]).read_bytes()).hexdigest()
    assert start["routing"] == closure["routing"] == expected_routing
    assert start["routingSha256"] == closure["routingSha256"] == expected_routing_digest
    assert closure["startReceiptSha256"] == hashlib.sha256(Path(missing["start_receipt"]).read_bytes()).hexdigest()
    assert closure["canonicalResultSha256"] == hashlib.sha256(Path(missing["result"]).read_bytes()).hexdigest()
    print("PASS exit 0 with missing result creates route-bound canonical failed receipts")

    for status in ("done", "blocked", "failed"):
        case = make_case(f"nonzero-valid-{status}", "valid", status=status, exit_code=7)
        completed = run_gateway(case)
        assert completed.returncode != 0
        assert load_valid_result(case["result"])["status"] == status
        assert run_monitor(case).returncode == 0
    print("PASS nonzero launcher exit preserves valid done, blocked, and failed verdicts")

    for status in ("done", "blocked", "failed"):
        case = make_case(
            f"claude-stdout-valid-{status}",
            "stdout-valid",
            executor="claude",
            status=status,
            exit_code=7,
            candidate_source="stdout",
        )
        completed = run_gateway(case)
        assert completed.returncode != 0
        assert load_valid_result(case["result"])["status"] == status
        assert Path(case["candidate"]).read_bytes() == Path(case["case"], "stdout.log").read_bytes()
        closure = json.loads(Path(case["closure"]).read_text(encoding="utf-8"))
        assert closure["candidate"]["source"] == "stdout"
        assert closure["candidate"]["sha256"] == closure["stdout"]["sha256"]
        assert run_monitor(case).returncode == 0
    print("PASS Claude stdout candidates materialize only after closure and preserve valid verdicts")

    for mode in (
        "malformed",
        "fenced",
        "truncated",
        "partial",
        "wrong-order",
        "wrong-executor",
        "prose",
        "envelope",
        "multiple",
        "duplicate-key",
        "non-finite",
        "infinity",
        "negative-infinity",
        "overflow-non-finite",
    ):
        case = make_case(
            f"claude-stdout-{mode}",
            f"stdout-{mode}",
            executor="claude",
            candidate_source="stdout",
        )
        completed = run_gateway(case)
        assert completed.returncode != 0
        result = load_valid_result(case["result"])
        assert result["status"] == "failed"
        assert not Path(case["candidate"]).exists()
        closure = json.loads(Path(case["closure"]).read_text(encoding="utf-8"))
        assert closure["candidate"]["source"] == "stdout"
        assert closure["stdout"]["captured"] is True and closure["stdout"]["sha256"]
        assert run_monitor(case).returncode == 0
    print("PASS malformed, framed, duplicate-key, NaN, Infinity, -Infinity, overflow, and multiple Claude stdout fail closed")

    strict_file_modes = ("duplicate-key", "non-finite", "infinity", "negative-infinity", "overflow-non-finite")
    for mode in strict_file_modes:
        case = make_case(f"file-{mode}", mode)
        completed = run_gateway(case)
        assert completed.returncode != 0
        result = load_valid_result(Path(case["result"]))
        assert result["status"] == "failed"
        evidence_path = Path(result["artifacts"][0]["path"])
        assert result["artifacts"][0]["type"] == "malformed-result-evidence"
        assert evidence_path.read_bytes() == Path(case["candidate"]).read_bytes()
        closure = read_json(Path(case["closure"]))
        assert closure["candidate"]["source"] == "file"
        assert closure["candidate"]["sha256"] == hashlib.sha256(Path(case["candidate"]).read_bytes()).hexdigest()
        assert closure["canonicalStatus"] == "failed"
        monitored = run_monitor(case)
        assert monitored.returncode == 0, monitored.stderr or monitored.stdout
        assert "terminal-closure-verified" in monitored.stdout
    print("PASS duplicate keys, NaN, Infinity, -Infinity, and overflow-non-finite Codex file candidates fail closed with evidence")

    for mode in ("malformed", "fenced", "truncated", "partial", "wrong-order", "wrong-executor"):
        case = make_case(mode, mode)
        completed = run_gateway(case)
        assert completed.returncode != 0
        result = load_valid_result(case["result"])
        assert result["status"] == "failed"
        assert result["artifacts"][0]["type"] == "malformed-result-evidence"
        assert run_monitor(case).returncode == 0
    print("PASS malformed, fenced, truncated, partial, and wrong-identity candidates fail closed with evidence")

    early = make_case("early-before-exit", "early", sleep_seconds=1.2)
    process = subprocess.Popen(gateway_command(early), cwd=ROOT, env=environment(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + 2
    while not Path(early["candidate"]).exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert Path(early["candidate"]).exists()
    assert not Path(early["result"]).exists()
    assert run_monitor(early).returncode != 0
    stdout, stderr = process.communicate(timeout=3)
    assert process.returncode == 0, stderr or stdout
    assert run_monitor(early).returncode == 0
    print("PASS early candidate presence is not completion before launcher closure")

    early_stdout = make_case(
        "claude-stdout-early-before-exit",
        "stdout-valid",
        executor="claude",
        sleep_seconds=1.2,
        candidate_source="stdout",
    )
    process = subprocess.Popen(gateway_command(early_stdout), cwd=ROOT, env=environment(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.2)
    assert not Path(early_stdout["candidate"]).exists()
    assert not Path(early_stdout["result"]).exists()
    assert run_monitor(early_stdout).returncode != 0
    stdout, stderr = process.communicate(timeout=3)
    assert process.returncode == 0, stderr or stdout
    assert Path(early_stdout["candidate"]).exists()
    assert run_monitor(early_stdout).returncode == 0
    print("PASS early Claude stdout is not materialized or accepted before launcher closure")

    timeout = make_case("timeout-partial", "timeout-partial", sleep_seconds=5, timeout_seconds=1, side_effect=True)
    before = launch_count()
    completed = run_gateway(timeout)
    assert completed.returncode == 124
    assert load_valid_result(timeout["result"])["status"] == "failed"
    closure = json.loads(Path(timeout["closure"]).read_text(encoding="utf-8"))
    assert closure["timedOut"] is True and closure["launcherClosed"] is True
    assert launch_count() == before + 1
    assert Path(timeout["side_effect"]).read_text(encoding="utf-8").splitlines() == ["effect"]
    print("PASS timeout closes child, preserves partial evidence, and never replays side effects")

    escaped = make_case("escaped-grandchild", "escaped-grandchild", sleep_seconds=10, timeout_seconds=1, side_effect=True)
    before = launch_count()
    started = time.monotonic()
    completed = run_gateway(escaped)
    elapsed = time.monotonic() - started
    assert completed.returncode == 124
    assert elapsed < 3
    assert load_valid_result(escaped["result"])["status"] == "failed"
    closure = read_json(Path(escaped["closure"]))
    assert closure["timedOut"] is True and closure["drainTimedOut"] is True
    assert launch_count() == before + 1
    assert Path(escaped["side_effect"]).read_text(encoding="utf-8").splitlines() == ["effect"]
    assert run_monitor(escaped).returncode == 0
    print("PASS escaped descendant cannot hold post-SIGKILL pipe draining open or trigger replay")

    stdout_timeout = make_case(
        "claude-stdout-timeout-partial",
        "stdout-timeout-partial",
        executor="claude",
        sleep_seconds=5,
        timeout_seconds=1,
        candidate_source="stdout",
    )
    completed = run_gateway(stdout_timeout)
    assert completed.returncode == 124
    assert load_valid_result(stdout_timeout["result"])["status"] == "failed"
    assert not Path(stdout_timeout["candidate"]).exists()
    closure = json.loads(Path(stdout_timeout["closure"]).read_text(encoding="utf-8"))
    assert closure["timedOut"] is True and closure["stdout"]["bytes"] > 0
    assert run_monitor(stdout_timeout).returncode == 0
    print("PASS timeout after partial Claude stdout preserves raw evidence without materialization")

    capture_failure = make_case("capture-oserror", "capture-oserror", separate_stdout_parent=True)
    exact_paths = [
        str(ROOT),
        *(str(capture_failure[key]) for key in ("candidate", "result", "start_receipt", "closure", "evidence", "events", "stdout", "stderr")),
    ]
    rewrite_order(capture_failure, lambda order: order.update({"allowedPaths": exact_paths}))
    completed = run_gateway(capture_failure)
    Path(capture_failure["evidence"]).chmod(0o700)
    Path(capture_failure["stdout"]).parent.chmod(0o700)
    assert completed.returncode != 0
    assert load_valid_result(capture_failure["result"])["status"] == "failed"
    closure = read_json(Path(capture_failure["closure"]))
    assert closure["stdout"]["fallback"] is True and closure["stdout"]["captured"] is False
    assert closure["controllerErrors"]
    assert run_monitor(capture_failure).returncode == 0
    print("PASS OSError capture and fallback failures still produce a policy-valid canonical failed result and closure")

    event_failure = make_case("event-failure", "event-failure")
    completed = run_gateway(event_failure)
    Path(event_failure["events"]).chmod(0o600)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert load_valid_result(event_failure["result"])["status"] == "done"
    assert run_monitor(event_failure).returncode == 0
    assert "could not append controller event" in completed.stderr
    print("PASS event-log failure after start remains non-authoritative after terminal closure")

    collision = make_case("result-collision", "valid")
    Path(collision["result"]).write_bytes(b"existing result bytes\n")
    before = launch_count()
    completed = run_gateway(collision)
    assert completed.returncode != 0
    assert Path(collision["result"]).read_bytes() == b"existing result bytes\n"
    assert launch_count() == before
    assert not Path(collision["closure"]).exists()
    print("PASS result collision preserves existing bytes and rejects before launch")

    for key in ("candidate", "stdout", "stderr", "result", "start_receipt", "closure"):
        case = make_case(f"preexisting-{key}", "valid")
        target = Path(case[key])
        target.write_bytes(f"existing {key}\n".encode("utf-8"))
        completed = assert_preflight_rejection(case, preexisting_key=key)
        assert target.read_bytes() == f"existing {key}\n".encode("utf-8")
        assert "already exists before launch" in completed.stderr
    print("PASS every create-only candidate, stream, result, start, and closure path collision rejects before launch")

    missing_parent = make_case("missing-output-parent", "valid")
    missing_parent["candidate"] = Path(missing_parent["case"]) / "missing-parent" / "candidate.json"
    assert "does not exist" in assert_preflight_rejection(missing_parent).stderr

    nondirectory_parent = make_case("nondirectory-output-parent", "valid")
    blocker = Path(nondirectory_parent["case"]) / "parent-blocker"
    blocker.write_text("blocker\n", encoding="utf-8")
    nondirectory_parent["candidate"] = blocker / "candidate.json"
    assert "not a directory" in assert_preflight_rejection(nondirectory_parent).stderr

    unwritable_parent = make_case("unwritable-output-parent", "valid")
    locked = Path(unwritable_parent["case"]) / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    unwritable_parent["candidate"] = locked / "candidate.json"
    completed = assert_preflight_rejection(unwritable_parent)
    locked.chmod(0o700)
    assert "not writable" in completed.stderr

    missing_evidence = make_case("missing-evidence", "valid")
    Path(missing_evidence["evidence"]).rmdir()
    assert "evidence directory does not exist" in assert_preflight_rejection(missing_evidence).stderr

    file_evidence = make_case("file-evidence", "valid")
    Path(file_evidence["evidence"]).rmdir()
    Path(file_evidence["evidence"]).write_text("not a directory\n", encoding="utf-8")
    assert "evidence directory is not a directory" in assert_preflight_rejection(file_evidence).stderr

    unwritable_evidence = make_case("unwritable-evidence", "valid")
    Path(unwritable_evidence["evidence"]).chmod(0o500)
    completed = assert_preflight_rejection(unwritable_evidence)
    Path(unwritable_evidence["evidence"]).chmod(0o700)
    assert "not writable" in completed.stderr

    symlink_alias = make_case("symlink-alias", "valid")
    alias_root = Path(symlink_alias["case"]) / "alias-root"
    alias_root.symlink_to(Path(symlink_alias["case"]), target_is_directory=True)
    symlink_alias["candidate"] = alias_root / "result.json"
    assert "must be distinct" in assert_preflight_rejection(symlink_alias).stderr

    evidence_namespace = make_case("evidence-namespace-alias", "valid")
    evidence_namespace["candidate"] = Path(evidence_namespace["evidence"]) / "candidate.json"
    assert "evidence directory must not contain" in assert_preflight_rejection(evidence_namespace).stderr

    directory_alias = make_case("evidence-closure-alias", "valid")
    directory_alias["closure"] = Path(directory_alias["evidence"])
    assert "must be distinct" in assert_preflight_rejection(directory_alias).stderr
    print("PASS missing, non-directory, non-writable, symlink-alias, and evidence namespace preflight failures reject before launch")

    for index, timeout_value in enumerate((True, 0, 1.5, "1")):
        invalid_timeout = make_case(f"invalid-timeout-{index}", "valid")
        rewrite_order(invalid_timeout, lambda order, value=timeout_value: order["launch"].update({"timeoutSeconds": value}))
        assert "positive integer" in assert_preflight_rejection(invalid_timeout).stderr

    invalid_stream_type = make_case("invalid-stream-type", "valid")
    rewrite_order(invalid_stream_type, lambda order: order["launch"].update({"stdoutPath": 7}))
    assert "must be a non-empty string" in assert_preflight_rejection(invalid_stream_type).stderr

    argv_mismatch = make_case("argv-mismatch", "valid")
    rewrite_order(argv_mismatch, lambda order: order["launch"].update({"command": "claude valid"}))
    assert "launch.command starts with claude" in assert_preflight_rejection(argv_mismatch).stderr

    invalid_argv = make_case("invalid-argv", "valid")
    rewrite_order(invalid_argv, lambda order: order["launch"].update({"command": "codex '"}))
    assert "cannot be parsed safely" in assert_preflight_rejection(invalid_argv).stderr

    codex_stdout = make_case("codex-stdout-mode", "stdout-valid", candidate_source="stdout")
    assert "supported only for claude" in assert_preflight_rejection(codex_stdout).stderr

    invalid_grace = make_case("invalid-grace", "valid")
    assert "finite positive" in assert_preflight_rejection(invalid_grace, grace_seconds="nan").stderr

    routing_rejections: list[tuple[str, Any, str]] = [
        ("missing", lambda order: order.update({"notesForExecutor": []}), "exactly one"),
        (
            "duplicate",
            lambda order: order["notesForExecutor"].append(order["notesForExecutor"][0]),
            "exactly one",
        ),
        (
            "malformed",
            lambda order: order.update({"notesForExecutor": [ROUTING_PREFIX + "{"]}),
            "strict JSON",
        ),
        (
            "overflow",
            lambda order: order.update(
                {"notesForExecutor": [order["notesForExecutor"][0][:-1] + ',"overflow":1e999}']}
            ),
            "non-finite numeric literal",
        ),
        (
            "below-floor",
            lambda order: (
                order.update({"riskLevel": "medium"}),
                set_routing(
                    order,
                    routing_metadata(
                        order["orderId"],
                        order["executor"],
                        risk="medium",
                        verificationProfile="V1",
                    ),
                ),
            ),
            "hard floor V2",
        ),
        (
            "wrong-model",
            lambda order: set_routing(
                order,
                routing_metadata(order["orderId"], order["executor"], model="claude-opus-5"),
            ),
            "codex routing.model",
        ),
        (
            "wrong-reviewer",
            lambda order: set_routing(
                order,
                routing_metadata(order["orderId"], order["executor"], reviewer="none"),
            ),
            "requires reviewer",
        ),
        (
            "terminal-recursive",
            lambda order: set_routing(
                order,
                routing_metadata(
                    order["orderId"],
                    order["executor"],
                    executionProfile="terminal_review",
                    terminalGate=True,
                    model="gpt-5.6-sol",
                    reviewer="gpt-5.6-sol",
                ),
            ),
            "cannot select another reviewer",
        ),
    ]
    for name, mutate, expected_error in routing_rejections:
        case = make_case(f"routing-{name}", "valid")
        rewrite_order(case, mutate)
        completed = assert_preflight_rejection(case)
        assert expected_error in completed.stderr
        assert not Path(case["events"]).exists(), "routing rejection must precede event artifact creation"
    print("PASS invalid gateway routing fails before child launch or custody/stream artifacts")

    missing_order = make_case("missing-order", "valid")
    Path(missing_order["order"]).unlink()
    assert "could not load order" in assert_preflight_rejection(missing_order).stderr

    malformed_order = make_case("malformed-order", "valid")
    Path(malformed_order["order"]).write_text("{not-json", encoding="utf-8")
    assert "order is not strict JSON" in assert_preflight_rejection(malformed_order).stderr
    print("PASS invalid order types, timeout, grace, candidate mode, command parsing, and executor argv mismatch reject before launch")

    default_schema = make_case("default-schema", "valid")
    completed = run_gateway(default_schema, explicit_schema=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert run_monitor(default_schema, explicit_schema=False).returncode == 0
    print("PASS gateway and monitor resolve the packaged default result schema")

    replay = make_case("side-effect-no-replay", "missing", side_effect=True)
    before = launch_count()
    first = run_gateway(replay)
    second = run_gateway(replay)
    assert first.returncode != 0 and second.returncode != 0
    assert launch_count() == before + 1
    assert Path(replay["side_effect"]).read_text(encoding="utf-8").splitlines() == ["effect"]
    print("PASS missing result after a side effect does not automatically replay the child")

    missing_start = completed_case("monitor-missing-start")
    Path(missing_start["start_receipt"]).unlink()
    assert "start receipt" in run_monitor(missing_start).stderr

    missing_closure = completed_case("monitor-missing-closure")
    Path(missing_closure["closure"]).unlink()
    assert "closure" in run_monitor(missing_closure).stderr

    malformed_start = completed_case("monitor-malformed-start")
    Path(malformed_start["start_receipt"]).write_text("{not-json", encoding="utf-8")
    assert "strict JSON" in run_monitor(malformed_start).stderr

    malformed_closure = completed_case("monitor-malformed-closure")
    Path(malformed_closure["closure"]).write_text("{not-json", encoding="utf-8")
    assert "strict JSON" in run_monitor(malformed_closure).stderr
    print("PASS monitor rejects missing and malformed start and closure receipts")

    start_mutations = {
        "order-id": ("orderId", "wrong-order"),
        "executor": ("executor", "claude"),
        "state": ("state", "closed"),
        "run-id": ("runId", "0" * 63),
        "order-digest": ("orderSha256", "0" * 64),
        "order-path": ("orderPath", str(ROOT / "wrong-order.json")),
        "result-path": ("resultPath", str(ROOT / "wrong-result.json")),
        "start-path": ("startReceiptPath", str(ROOT / "wrong-start.json")),
        "closure-path": ("closurePath", str(ROOT / "wrong-closure.json")),
        "candidate-source": ("candidateSource", "pipe"),
        "routing": ("routing", {"objectiveId": "wrong-route"}),
        "routing-digest": ("routingSha256", "0" * 64),
    }
    for name, (key, value) in start_mutations.items():
        case = completed_case(f"monitor-start-{name}")
        payload = read_json(Path(case["start_receipt"]))
        payload[key] = value
        write_json(Path(case["start_receipt"]), payload)
        assert run_monitor(case).returncode != 0

    stale_start = completed_case("monitor-stale-start")
    start_payload = read_json(Path(stale_start["start_receipt"]))
    start_payload["startedAt"] = "2026-08-02T00:00:00Z"
    write_json(Path(stale_start["start_receipt"]), start_payload)
    closure_payload = read_json(Path(stale_start["closure"]))
    closure_payload["startedAt"] = start_payload["startedAt"]
    closure_payload["startReceiptSha256"] = hashlib.sha256(Path(stale_start["start_receipt"]).read_bytes()).hexdigest()
    write_json(Path(stale_start["closure"]), closure_payload)
    assert "stale" in run_monitor(stale_start).stderr

    changed_order = completed_case("monitor-order-digest")
    rewrite_order(changed_order, lambda order: order["context"].append("post-launch mutation"))
    assert "orderSha256 mismatch" in run_monitor(changed_order).stderr
    print("PASS monitor rejects start identity, run, state, path, order digest, and freshness mismatches")

    closure_mutations = {
        "order-id": ("orderId", "wrong-order"),
        "executor": ("executor", "claude"),
        "state": ("state", "started"),
        "launcher-state": ("launcherClosed", False),
        "canonical-state": ("canonicalFinalized", False),
        "run-id": ("runId", "f" * 64),
        "order-digest": ("orderSha256", "0" * 64),
        "start-digest": ("startReceiptSha256", "0" * 64),
        "order-path": ("orderPath", str(ROOT / "wrong-order.json")),
        "start-path": ("startReceiptPath", str(ROOT / "wrong-start.json")),
        "result-path": ("canonicalResultPath", str(ROOT / "wrong-result.json")),
        "status": ("canonicalStatus", "unknown"),
        "routing": ("routing", {"objectiveId": "wrong-route"}),
        "routing-digest": ("routingSha256", "0" * 64),
    }
    for name, (key, value) in closure_mutations.items():
        case = completed_case(f"monitor-closure-{name}")
        payload = read_json(Path(case["closure"]))
        payload[key] = value
        write_json(Path(case["closure"]), payload)
        assert run_monitor(case).returncode != 0

    start_digest = completed_case("monitor-start-digest")
    payload = read_json(Path(start_digest["start_receipt"]))
    payload["candidatePath"] = str(ROOT / "different-candidate.json")
    write_json(Path(start_digest["start_receipt"]), payload)
    assert "startReceiptSha256 mismatch" in run_monitor(start_digest).stderr

    result_digest = completed_case("monitor-result-digest")
    payload = read_json(Path(result_digest["result"]))
    payload["summary"] = "schema-valid mutation after closure"
    write_json(Path(result_digest["result"]), payload)
    assert "canonicalResultSha256 mismatch" in run_monitor(result_digest).stderr

    invalid_schema = completed_case("monitor-schema-invalid")
    payload = read_json(Path(invalid_schema["result"]))
    del payload["summary"]
    write_json(Path(invalid_schema["result"]), payload)
    assert "schema validation failed" in run_monitor(invalid_schema).stderr

    wrong_identity = completed_case("monitor-result-identity")
    payload = read_json(Path(wrong_identity["result"]))
    payload["orderId"] = "wrong-order"
    write_json(Path(wrong_identity["result"]), payload)
    assert "orderId does not match" in run_monitor(wrong_identity).stderr

    malformed_result = completed_case("monitor-non-json")
    Path(malformed_result["result"]).write_text("not json\n", encoding="utf-8")
    assert "strict JSON" in run_monitor(malformed_result).stderr
    print("PASS monitor rejects closure identity/state/path/status, start/result digest, schema, identity, and JSON failures")

    for target in ("order", "result", "start_receipt", "closure"):
        case = completed_case(f"monitor-strict-{target}")
        path = Path(case[target])
        original = path.read_bytes()
        for variant in ("duplicate-key", "nan", "infinity", "negative-infinity", "overflow"):
            path.write_bytes(ambiguous_json_bytes(original, variant))
            monitored = run_monitor(case)
            assert monitored.returncode != 0
            assert "strict JSON" in monitored.stderr, monitored.stderr or monitored.stdout
            path.write_bytes(original)
    print("PASS monitor rejects duplicate keys, NaN, Infinity, -Infinity, and 1e999 in order/result/start/closure JSON")

    event_text = Path(missing["events"]).read_text(encoding="utf-8")
    assert "aquila.result_gateway.v1.launch_closed" in event_text
    assert "aquila.result_gateway.v1.canonical_finalized" in event_text
    print("PASS controller event namespace remains best-effort evidence and is not the terminal authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
