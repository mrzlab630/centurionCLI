#!/usr/bin/env python3
"""Focused regressions for ORDER_PREFLIGHT_V1 and its no-child boundary."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from agent_artifact_namespace import artifact_namespace
from agent_contract_runner import PathPolicy, RunnerError, validate_order, validate_codex_launch
from order_preflight import controller_context, executor_environment, plan_order, validate_claude_proxy_environment

def assert_case(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def base_order(repo: Path, order_id: str = "preflight-regression") -> dict:
    control = artifact_namespace(repo, order_id)
    control.mkdir(parents=True)
    return {
        "orderVersion": "AGENT_ORDER_JSON_V1", "orderId": order_id,
        "createdAt": "2026-06-17T00:00:00Z", "controller": "Aquila",
        "executor": "other", "roleForTask": "CODER", "riskLevel": "low",
        "workspace": {"repoPath": str(repo), "branchOrWorktree": "fixture", "projectName": "preflight"},
        "launch": {"surface": "fixture", "command": "other", "timeoutSeconds": 2,
                   "resultJsonPath": str(control / "result.json"),
                   "candidateJsonPath": str(control / "candidate.json")},
        "objective": "preflight regression", "context": [],
        "allowedPaths": [str(repo / "**")], "forbiddenPaths": [], "forbiddenActions": [],
        "nonGoals": [], "acceptanceCriteria": ["preflight is deterministic"],
        "expectedArtifacts": [], "proofCommands": [], "outputContract": {
            "resultVersion": "AGENT_RESULT_JSON_V1", "resultPath": str(control / "result.json"),
            "stdoutAllowed": False, "proseAllowedAfterJson": False,
        }, "stopConditions": [], "notesForExecutor": [],
    }


def diagnostics(order: dict, policy: PathPolicy) -> list[dict]:
    return plan_order(order, policy)["diagnostics"]


def codes(order: dict, policy: PathPolicy) -> set[str]:
    return {item["code"] for item in diagnostics(order, policy) if item["severity"] == "error"}


def main() -> int:
    fixture = Path(tempfile.mkdtemp(prefix="order-preflight-regression-"))
    try:
        repo = fixture / "repo"
        repo.mkdir()
        order = base_order(repo)
        policy = PathPolicy(repo, order["allowedPaths"], order["forbiddenPaths"], order["orderId"])
        planned = plan_order(order, policy)
        assert_case(planned["valid"], "ordinary candidate-backed order without prompt requirement should remain valid")
        assert_case(planned["diagnostics"] == sorted(planned["diagnostics"], key=lambda item: (item["severity"], item["code"], item["path"], item["message"])), "diagnostics must be deterministically ordered")
        print("PASS deterministic positive plan preserves compatible candidate surface")

        alias = json.loads(json.dumps(order))
        alias["launch"]["candidateJsonPath"] = alias["outputContract"]["resultPath"]
        alias_policy = PathPolicy(repo, alias["allowedPaths"], alias["forbiddenPaths"], alias["orderId"])
        assert_case("CANDIDATE_CANONICAL_ALIAS" in codes(alias, alias_policy), "candidate/canonical alias must fail")
        print("PASS candidate/canonical alias rejected")

        preexisting = json.loads(json.dumps(order))
        Path(preexisting["outputContract"]["resultPath"]).write_text("old\n", encoding="utf-8")
        pre_policy = PathPolicy(repo, preexisting["allowedPaths"], preexisting["forbiddenPaths"], preexisting["orderId"])
        assert_case("OUTPUT_PREEXISTS" in codes(preexisting, pre_policy), "pre-existing canonical result must fail")
        Path(preexisting["outputContract"]["resultPath"]).unlink()
        print("PASS pre-existing canonical result rejected")

        prompt = json.loads(json.dumps(order))
        prompt["launch"].update(command="other -", promptRequired=True)
        prompt_policy = PathPolicy(repo, prompt["allowedPaths"], prompt["forbiddenPaths"], prompt["orderId"])
        prompt_codes = codes(prompt, prompt_policy)
        assert_case({"STDIN_SENTINEL_UNAVAILABLE", "PROMPT_MISSING"} <= prompt_codes, "missing prompt and unavailable stdin sentinel must fail")
        supplied = json.loads(json.dumps(prompt))
        supplied["launch"]["stdinProvided"] = True
        supplied_policy = PathPolicy(repo, supplied["allowedPaths"], supplied["forbiddenPaths"], supplied["orderId"])
        assert_case(not ({"STDIN_SENTINEL_UNAVAILABLE", "PROMPT_MISSING"} & codes(supplied, supplied_policy)), "generic fixture stdin declarations retain compatibility")

        legacy_agy = json.loads(json.dumps(order))
        legacy_agy["executor"] = "agy"
        legacy_agy["launch"]["command"] = "agy"
        legacy_agy_policy = PathPolicy(repo, legacy_agy["allowedPaths"], legacy_agy["forbiddenPaths"], legacy_agy["orderId"])
        assert_case(plan_order(legacy_agy, legacy_agy_policy)["valid"], "bare AGY file adapter retains legacy compatibility")
        for override in ({"surface": "agy-cli"}, {"promptRequired": True}, {"promptRequired": False},
                         {"command": str(repo / "agy")}, {"command": "agy --"}):
            strict_agy = json.loads(json.dumps(legacy_agy))
            strict_agy["launch"].update(override)
            assert_case("PROMPT_MISSING" in codes(strict_agy, legacy_agy_policy), "bare AGY exception must stay limited to the undeclared legacy fixture transport")
        strict_agy = json.loads(json.dumps(legacy_agy))
        strict_agy["launch"].update(command="agy --print -", stdinProvided=True)
        assert_case({"STDIN_SENTINEL_UNAVAILABLE", "PROMPT_MISSING"} <= codes(strict_agy, legacy_agy_policy), "AGY fixture stdin sentinel must remain strict")
        aliased_agy = json.loads(json.dumps(legacy_agy))
        aliased_agy["launch"]["candidateJsonPath"] = aliased_agy["outputContract"]["resultPath"]
        assert_case("CANDIDATE_CANONICAL_ALIAS" in codes(aliased_agy, legacy_agy_policy), "legacy adapter must retain candidate custody checks")
        print("PASS bare AGY file adapter compatibility stays bounded; real CLI and custody checks remain strict")

        commands = {
            "codex": "codex exec --json --model gpt-6.1-sol -c model_reasoning_effort=xhigh",
            "claude": "claude -p --output-format json --model claude-opus-5-5 --fallback-model claude-opus-5",
            "agy": "agy --model gemini-3.8-flash --effort high --print",
        }
        for executor, command in commands.items():
            target = json.loads(json.dumps(order))
            target["executor"] = executor
            target["launch"]["command"] = command
            target_policy = PathPolicy(repo, target["allowedPaths"], target["forbiddenPaths"], target["orderId"])
            for marker in (None, False, True):
                if marker is not None:
                    target["launch"]["promptRequired"] = marker
                assert_case("PROMPT_MISSING" in codes(target, target_policy), f"{executor} option values must not satisfy the default prompt requirement")
            for key, value in {"stdinProvided": True, "suppliedStdin": True, "stdin": "instructions",
                               "stdinPath": str(repo / "input"), "input": {"text": "instructions"}, "inputPath": str(repo / "input")}.items():
                spoofed = json.loads(json.dumps(target))
                spoofed["launch"][key] = value
                assert_case("PROMPT_MISSING" in codes(spoofed, target_policy), f"{executor} must not trust {key} as runtime stdin")
                spoofed["launch"]["command"] += " -"
                assert_case({"STDIN_SENTINEL_UNAVAILABLE", "PROMPT_MISSING"} <= codes(spoofed, target_policy), f"{executor} stdin sentinel must fail despite {key}")
            target["launch"]["command"] = command + " 'hello world'"
            assert_case(plan_order(target, target_policy)["valid"], f"quoted {executor} prompt must be one argv token")
            target["launch"]["command"] = command + " hello world"
            assert_case("PROMPT_ARGV_ARITY" in codes(target, target_policy), f"unquoted multiword {executor} prompt must fail")
            target["launch"]["command"] = command + " '   '"
            assert_case("PROMPT_MISSING" in codes(target, target_policy), f"blank {executor} prompt must fail")
            target["launch"].pop("candidateJsonPath")
            target["launch"]["command"] = command + " -"
            assert_case(plan_order(target, target_policy)["valid"], f"legacy non-candidate {executor} orders retain behavior")
        for executor, command in (
            ("codex", "codex --no-daemon exec --model gpt-6.1-sol -c model_reasoning_effort=high 'quoted prompt'"),
            ("codex", "codex exec -mgpt-6.1-sol -cmodel_reasoning_effort=xhigh -C. -sworkspace-write -o- -- '--quoted prompt'"),
            ("codex", "codex exec --model=gpt-6.1-sol --config=model_reasoning_effort=xhigh --image a.png b.png -- 'quoted prompt'"),
            ("claude", "claude --model=claude-opus-5-5 -p --tools Read Edit -- 'quoted prompt'"),
            ("claude", "claude -p 'quoted prompt' --debug hooks --effort xhigh --output-format=json"),
            ("agy", "agy --model=gemini-3.8-flash --effort=high --prompt='quoted prompt'"),
            ("agy", "agy -p='quoted prompt' --model gemini-3.8-flash --effort high --sandbox"),
        ):
            target = json.loads(json.dumps(order))
            target["executor"] = executor
            target["launch"]["command"] = command
            assert_case(plan_order(target, policy)["valid"], f"attached options, delimiter, and option values must parse: {command}")
        for executor, command, expected in (
            ("codex", "codex --no-daemon --profile foreign exec 'quoted prompt'", "PROMPT_ARGV_INVALID"),
            ("codex", "codex --no-daemon --no-daemon exec 'quoted prompt'", "PROMPT_ARGV_INVALID"),
            ("codex", "codex exec --model", "PROMPT_ARGV_INVALID"),
            ("codex", "codex exec --unknown value", "PROMPT_ARGV_INVALID"),
            ("codex", "codex exec --model=gpt-6.1-sol --color=never --output-schema=schema.json", "PROMPT_MISSING"),
            ("codex", "codex exec -- -", "STDIN_SENTINEL_UNAVAILABLE"),
            ("claude", "claude -p --debug hooks --tools Read Edit", "PROMPT_MISSING"),
            ("claude", "claude -p --tools=Read Edit", "PROMPT_MISSING"),
            ("claude", "claude -p --input-format=stream-json 'quoted prompt'", "STDIN_SENTINEL_UNAVAILABLE"),
            ("agy", "agy --print= --model gemini-3.8-flash", "PROMPT_MISSING"),
            ("agy", "agy 'quoted prompt'", "PROMPT_ARGV_INVALID"),
            ("agy", "agy --print='quoted prompt' --input-format stream-json", "STDIN_SENTINEL_UNAVAILABLE"),
        ):
            target = json.loads(json.dumps(order))
            target["executor"] = executor
            target["launch"]["command"] = command
            assert_case(expected in codes(target, policy), f"invalid prompt transport must reject: {command}")
        print("PASS Codex/Claude/agy default prompts, stdin metadata, delimiters, option values and one-token arity; legacy fixtures preserved")

        for prefix in ("codex exec", "codex --no-daemon exec"):
            validate_codex_launch(prefix + ' --model gpt-6-astra -c model_reasoning_effort=high --sandbox read-only -C /tmp -o /tmp/candidate.json "bounded advice"', "gpt-6-astra", "high", advisory=True)
            for suffix in (' --profile foreign', ' --sandbox workspace-write', ' -c model_reasoning_effort=low'):
                try:
                    validate_codex_launch(prefix + ' --model gpt-6-astra -c model_reasoning_effort=high --sandbox read-only -C /tmp -o /tmp/candidate.json "bounded advice"' + suffix, "gpt-6-astra", "high", advisory=True)
                except RunnerError:
                    pass
                else:
                    raise AssertionError("isolated Astra launch must retain route/sandbox floors: " + suffix)
        print("PASS optional global no-daemon preserves strict Codex/Astra route and read-only floors")

        scratch = json.loads(json.dumps(order))
        scratch["launch"]["scratchPath"] = "/tmp/preflight-scratch"
        scratch_policy = PathPolicy(repo, scratch["allowedPaths"], scratch["forbiddenPaths"], scratch["orderId"])
        assert_case({"PLANNED_PATH_NOT_ALLOWED", "CONTROL_PATH_OUTSIDE_ORDER_NAMESPACE"} <= codes(scratch, scratch_policy), "scratch path outside policy and fresh namespace must fail")
        scratch["launch"]["scratchPath"] = str(artifact_namespace(repo, scratch["orderId"]) / "scratch")
        assert_case(plan_order(scratch, scratch_policy)["valid"], "scratch path inside the fresh control namespace must pass")
        for value in ("", " ", None, 42):
            scratch["launch"]["scratchPath"] = value
            assert_case("PLANNED_PATH_INVALID" in codes(scratch, scratch_policy), "malformed declared scratch paths must not disappear from planning")
        scratch["launch"]["scratchPath"] = str(repo / "scratch")
        assert_case("CONTROL_PATH_OUTSIDE_ORDER_NAMESPACE" in codes(scratch, scratch_policy), "allowed scratch outside current namespace must fail")
        scratch["launch"]["scratchPath"] = str(artifact_namespace(repo, "previous-order") / "scratch")
        assert_case("CONTROL_PATH_OUTSIDE_ORDER_NAMESPACE" in codes(scratch, scratch_policy), "previous order scratch must fail")
        namespace = artifact_namespace(repo, scratch["orderId"])
        scratch["launch"]["scratchPath"] = str(namespace / "scratch")
        exact_policy = PathPolicy(repo, [str(namespace)], [], scratch["orderId"])
        assert_case("PLANNED_PATH_NOT_ALLOWED" in codes(scratch, exact_policy), "exact namespace grant does not cover scratch descendants")
        forbidden_policy = PathPolicy(repo, scratch["allowedPaths"], [str(namespace / "scratch" / "**")], scratch["orderId"])
        assert_case("PLANNED_PATH_FORBIDDEN" in codes(scratch, forbidden_policy), "forbidden scratch subtree overrides allowed coverage")
        scratch_link = namespace / "scratch-link"
        scratch_link.symlink_to(repo)
        scratch["launch"]["scratchPath"] = str(scratch_link / "escaped")
        assert_case("CONTROL_PATH_OUTSIDE_ORDER_NAMESPACE" in codes(scratch, scratch_policy), "scratch symlink escapes must fail")
        scratch["launch"].pop("candidateJsonPath")
        assert_case(plan_order(scratch, scratch_policy)["valid"], "legacy non-candidate scratch metadata retains behavior")
        print("PASS declared scratch path is bounded by allowed paths and fresh order namespace")

        typed = json.loads(json.dumps(order))
        preview = repo / "preview.txt"
        preview.write_text("preview\n", encoding="utf-8")
        digest = hashlib.sha256(preview.read_bytes()).hexdigest()
        typed["expectedArtifacts"] = [{"path": str(preview), "type": "preview", "required": False, "sha256": digest, "mediaType": "text/plain"}]
        typed_policy = PathPolicy(repo, typed["allowedPaths"], typed["forbiddenPaths"], typed["orderId"])
        assert_case(plan_order(typed, typed_policy)["valid"], "complete supplied typed preview must pass")
        incomplete = json.loads(json.dumps(typed))
        incomplete["expectedArtifacts"][0].pop("mediaType")
        incomplete_policy = PathPolicy(repo, incomplete["allowedPaths"], incomplete["forbiddenPaths"], incomplete["orderId"])
        assert_case("ARTIFACT_PREVIEW_MEDIA_TYPE_INVALID" in codes(incomplete, incomplete_policy), "incomplete typed preview must fail")
        wrong = json.loads(json.dumps(typed))
        wrong["expectedArtifacts"][0]["sha256"] = "0" * 64
        wrong_policy = PathPolicy(repo, wrong["allowedPaths"], wrong["forbiddenPaths"], wrong["orderId"])
        assert_case("ARTIFACT_PREVIEW_DIGEST_MISMATCH" in codes(wrong, wrong_policy), "wrong supplied preview digest must fail")
        print("PASS typed artifact preview requires and checks supplied digest/media type")

        stale = json.loads(json.dumps(order))
        stale["outputContract"]["handoff"] = {"version": "AGENT_HANDOFF_V1", "schemaId": "AGENT_RESULT_JSON_V1", "inReplyTo": "old-order", "senderRole": "CODER", "recipientRole": "Aquila"}
        stale_policy = PathPolicy(repo, stale["allowedPaths"], stale["forbiddenPaths"], stale["orderId"])
        assert_case("HANDOFF_IDENTITY_STALE" in codes(stale, stale_policy), "stale handoff identity must fail")
        print("PASS stale handoff identity rejected")

        path_order = json.loads(json.dumps(order))
        product = repo / "product.txt"
        forbidden = repo / "secret"
        forbidden.mkdir()
        path_order["expectedArtifacts"] = [{"path": str(product), "type": "product", "required": False}]
        path_order["proofCommands"] = [{"command": "true", "cwd": str(repo), "required": True}]
        path_order["allowedPaths"] = [str(product)]
        path_order["forbiddenPaths"] = [str(forbidden / "**"), str(repo / "unplanned" / "**")]
        path_policy = PathPolicy(repo, path_order["allowedPaths"], path_order["forbiddenPaths"], path_order["orderId"])
        assert_case("PLANNED_PATH_NOT_ALLOWED" in codes(path_order, path_policy), "exact allowed path must not cover proof cwd")
        unrelated = json.loads(json.dumps(order))
        unrelated["forbiddenPaths"] = [str(repo / "unplanned" / "**")]
        unrelated_policy = PathPolicy(repo, unrelated["allowedPaths"], unrelated["forbiddenPaths"], unrelated["orderId"])
        assert_case(plan_order(unrelated, unrelated_policy)["valid"], "unplanned forbidden subtree must not conflict globally")
        path_order["expectedArtifacts"][0]["path"] = str(forbidden / "blocked.txt")
        forbidden_policy = PathPolicy(repo, path_order["allowedPaths"] + [str(forbidden / "**")], path_order["forbiddenPaths"], path_order["orderId"])
        assert_case("PLANNED_PATH_FORBIDDEN" in codes(path_order, forbidden_policy), "planned forbidden artifact must fail")
        print("PASS exact/recursive path coverage and planned-only forbidden conflicts")

        control_outside = json.loads(json.dumps(order))
        control_outside["launch"]["resultJsonPath"] = str(repo / "result.json")
        control_outside["outputContract"]["resultPath"] = str(repo / "result.json")
        previous_allow_other = os.environ.get("AGENT_CONTRACT_RUNNER_ALLOW_OTHER")
        try:
            os.environ["AGENT_CONTRACT_RUNNER_ALLOW_OTHER"] = "1"
            validate_order(control_outside)
        except RunnerError as exc:
            assert_case("expected control artifact namespace" in str(exc), "outside control path must identify namespace")
        else:
            raise AssertionError("outside control path was accepted")
        finally:
            if previous_allow_other is None:
                os.environ.pop("AGENT_CONTRACT_RUNNER_ALLOW_OTHER", None)
            else:
                os.environ["AGENT_CONTRACT_RUNNER_ALLOW_OTHER"] = previous_allow_other
        print("PASS control paths outside fresh order namespace rejected before dispatch")

        for version, expected in (("LEGION_ORDER_V1", "ORDER_VERSION_UNSUPPORTED"),):
            target = json.loads(json.dumps(order))
            target["orderVersion"] = version
            assert_case(expected in codes(target, policy), "non-V1 ingress must fail")
        for transports in (["unsupported"], [], [{"raw_json": True}]):
            target = json.loads(json.dumps(order))
            target["outputContract"]["acceptedTransports"] = transports
            assert_case("TRANSPORT_UNSUPPORTED" in codes(target, policy), "unsupported transport must fail")
        print("PASS strict order version and transport configuration fail before launch")
        assert executor_environment("codex", {"PATH": "/runtime", "OPENAI_API_KEY": "synthetic-credential", "UNRELATED_SECRET": "synthetic-marker"}) == {
            "PATH": "/runtime", "OPENAI_API_KEY": "synthetic-credential"}
        claude_env = {"ANTHROPIC_BASE_URL": "http://127.0.0.1:8317", "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5-5"}
        assert executor_environment("claude", dict(claude_env, UNRELATED_SECRET="synthetic-marker")) == claude_env
        validate_claude_proxy_environment(claude_env, "claude-opus-5-5")
        for bad in ({}, dict(claude_env, ANTHROPIC_DEFAULT_OPUS_MODEL="wrong"),
                    dict(claude_env, ANTHROPIC_BASE_URL="https://api.anthropic.com"),
                    dict(claude_env, ANTHROPIC_BASE_URL="http://@localhost:8317"),
                    dict(claude_env, ANTHROPIC_BASE_URL="http://user:pass@localhost:8317"),
                    dict(claude_env, ANTHROPIC_BASE_URL="http://localhost:8317@attacker.example"),
                    dict(claude_env, ANTHROPIC_BASE_URL="http://local\nhost:8317")):
            try:
                validate_claude_proxy_environment(bad, "claude-opus-5-5")
            except ValueError:
                pass
            else:
                raise AssertionError("missing/mismatched/nonlocal Claude route must fail before launch")
        for context in ([{"policyVersion": "3.0"}, {"policyVersion": "3.0"}], [{"policyVersion": "2.6"}]):
            try:
                controller_context({"context": context})
            except ValueError:
                pass
            else:
                raise AssertionError("ambiguous/unknown controller context must fail closed")
        print("PASS selected-runtime environment excludes unrelated values and duplicate/unknown policy contexts fail closed")
        return 0
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
