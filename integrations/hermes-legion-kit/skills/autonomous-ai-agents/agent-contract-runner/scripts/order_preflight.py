#!/usr/bin/env python3
"""Deterministic, proof-oriented custody and dispatch preflight planner.

The runner remains the canonical schema/routing validator. This module plans
candidate-backed launch custody and emits stable, actionable diagnostics for
conditions that must be true before an executor process can start.
"""
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import Path
from typing import Any

from response_envelope import MAX_ORDER_BYTES, read_bounded_file, validate_handoff_order
from strict_json import strict_json_load_bytes

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PreflightError(ValueError):
    """The selected tunnel cannot safely deliver this order."""


def controller_context(order: dict[str, Any], *, required: bool = False) -> dict[str, Any] | None:
    """Read the one policy-bearing controller context; never infer authority."""
    values = order.get("context", [])
    contexts = [item for item in values if isinstance(item, dict) and
                any(key in item for key in ("policyVersion", "missionId", "intentId"))] if isinstance(values, list) else []
    if len(contexts) > 1:
        raise PreflightError("ambiguous controller policy context")
    if not contexts:
        if required or "policyVersion" in order:
            raise PreflightError("controller context policyVersion 3.0 is required")
        return None
    if contexts[0].get("policyVersion") != "3.0":
        raise PreflightError("unsupported controller policyVersion")
    return contexts[0]


def load_tunnel_order(path: Path) -> tuple[dict[str, Any], bytes]:
    content, complete = read_bounded_file(path, MAX_ORDER_BYTES)
    if not complete:
        raise PreflightError("order exceeds byte limit or changed while reading")
    order = strict_json_load_bytes(content, "order")
    if not isinstance(order, dict) or order.get("orderVersion") != "AGENT_ORDER_JSON_V1":
        raise PreflightError("ingress requires one AGENT_ORDER_JSON_V1 object")
    return order, content


def review_binding(order: dict[str, Any], routing: dict[str, Any] | None) -> dict[str, str] | None:
    context = controller_context(order)
    if context is None or not isinstance(routing, dict) or routing.get("executionProfile") != "terminal_review":
        return None
    binding = context.get("reviewBinding")
    keys = {"reviewedOrderId", "reviewedResultSha256", "productSnapshotSha256"}
    if not isinstance(binding, dict) or set(binding) != keys:
        raise PreflightError("3.0 reviewer requires controller reviewBinding")
    from agent_artifact_namespace import validate_order_id
    validate_order_id(binding["reviewedOrderId"])
    if any(not isinstance(binding[key], str) or not _SHA256.fullmatch(binding[key]) for key in keys - {"reviewedOrderId"}):
        raise PreflightError("reviewBinding requires SHA-256 result and product snapshot digests")
    # A terminal reviewer consumes a captured candidate, before product acceptance.
    # Ordinary inputResults still pass the accepted-input verifier unchanged.
    # Historical schema fixtures may exercise projection with no mission state;
    # active Gateway review orders must carry the controller candidate binding.
    if not context.get("candidateIntentId") and context.get("missionId"):
        raise PreflightError("reviewBinding requires controller candidateIntentId")
    return binding


def _option_values(argv: list[str], names: set[str]) -> list[str]:
    values = []
    for index, token in enumerate(argv):
        if token == "--":
            break
        name, separator, attached = token.partition("=")
        if name in names:
            if separator:
                values.append(attached)
            elif index + 1 < len(argv):
                values.append(argv[index + 1])
        elif not token.startswith("--") and len(token) > 2 and token[:2] in names:
            values.append(token[2:].removeprefix("="))
    return values


def executor_environment(executor: str, inherited: dict[str, str]) -> dict[str, str]:
    """Pass only the selected CLI's runtime environment; never serialize values."""
    common = {"PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "COLORTERM",
              "TMPDIR", "TMP", "TEMP", "SHELL", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
              "XDG_STATE_HOME", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy",
              "https_proxy", "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS"}
    selected = {"codex": {"CODEX_HOME", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID"},
                "claude": {"CLAUDE_CONFIG_DIR", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"}}
    return {key: value for key, value in inherited.items() if key in common | selected.get(executor, set())}


def validate_claude_proxy_environment(environment: dict[str, str]) -> None:
    """Require local transport; model selection is bound separately to order argv."""
    from urllib.parse import urlsplit
    try:
        raw_url = environment.get("ANTHROPIC_BASE_URL", "")
        endpoint = urlsplit(raw_url)
        local = endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
        valid = (endpoint.scheme in {"http", "https"} and local and endpoint.port is not None
                 and endpoint.username is None and endpoint.password is None and not endpoint.query
                 and not any(char.isspace() for char in raw_url)
                 and not endpoint.fragment and endpoint.path in {"", "/"})
    except ValueError:
        valid = False
    if not valid:
        raise PreflightError("Claude requires explicit local ANTHROPIC_BASE_URL (origin with port)")


def validate_tunnel_launch(order: dict[str, Any], policy: Any, candidate: Path, source: str,
                           schema_path: Path | None, routing: dict[str, Any] | None) -> list[dict[str, str]]:
    """3.0 admission only. Mission authority/reservation is checked by W3."""
    controller_context(order, required=True)
    if not isinstance(routing, dict):
        raise PreflightError("3.0 cannot activate legacy/missing routing metadata")
    if order.get("executor") not in {"codex", "claude"} or order.get("controller") != "Aquila":
        raise PreflightError("3.0 supports only Codex/Claude through controller Aquila")
    handoff_errors = validate_handoff_order(order, routing)
    if "handoff" not in order.get("outputContract", {}) or handoff_errors:
        raise PreflightError("3.0 requires exact AGENT_HANDOFF_V1: " + "; ".join(handoff_errors))
    plan = plan_order(order, policy, check_fresh_outputs=False)
    if not plan["valid"]:
        raise PreflightError("; ".join(f"{item['code']}: {item['message']}" for item in plan["diagnostics"] if item["severity"] == "error"))
    launch = order["launch"]
    timeout = launch.get("timeoutSeconds")
    if "timeoutSeconds" not in launch or (timeout is not None and (type(timeout) is not int or timeout < 1)):
        raise PreflightError("launch.timeoutSeconds must be a positive integer or explicit null for monitored execution")
    if not launch.get("candidateJsonPath") or policy.control_path(launch["candidateJsonPath"], "launch.candidateJsonPath") != candidate:
        raise PreflightError("launch.candidateJsonPath must match the single selected candidate")
    if any(key in launch for key in ("env", "environment", "stdin", "stdinPath", "input", "inputPath", "stdinProvided", "suppliedStdin")):
        raise PreflightError("unsupported launch env/stdin override; Gateway supplies argv and no stdin")
    argv = shlex.split(launch["command"])
    if any(token in {"--continue", "--last", "resume", "fork"} for token in argv[1:-1]):
        raise PreflightError("3.0 initial launch cannot resume an unbound session")
    from agent_result_builder import native_result_schema, resolve_schema_path, PACKAGED_SCHEMA
    if resolve_schema_path(schema_path).resolve() != PACKAGED_SCHEMA.resolve():
        raise PreflightError("3.0 requires the packaged canonical result schema")
    expected_schema = native_result_schema(order, routing)
    review_binding(order, routing)
    if order["executor"] == "codex":
        outputs = _option_values(argv, {"-o", "--output-last-message"})
        if source != "file" or len(outputs) != 1 or policy.control_path(outputs[0], "Codex output-last-message") != candidate:
            raise PreflightError("Codex requires one --output-last-message matching the file candidate")
        schemas = _option_values(argv, {"--output-schema"})
        if len(schemas) > 1:
            raise PreflightError("ambiguous Codex output schema")
        if schemas:
            schema_file = policy.control_path(schemas[0], "Codex output schema")
            raw, complete = read_bounded_file(schema_file, MAX_ORDER_BYTES)
            if not complete or strict_json_load_bytes(raw, "native schema") != expected_schema:
                raise PreflightError("Codex native schema is not the canonical order projection")
    else:
        formats = _option_values(argv, {"--output-format"})
        if source == "stdout" and formats not in (["json"], ["stream-json"]):
            raise PreflightError("Claude stdout requires one json/stream-json output format")
        schemas = _option_values(argv, {"--json-schema"})
        if len(schemas) > 1 or (schemas and strict_json_load_bytes(schemas[0].encode(), "Claude native schema") != expected_schema):
            raise PreflightError("Claude native schema is not the canonical order projection")
        if schemas and source != "stdout":
            raise PreflightError("Claude structured_output requires stdout candidate source")
    return [item for item in plan["diagnostics"] if item["severity"] == "warning"]


def _diagnostic(code: str, severity: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "path": path, "message": message}


def _resolve(value: str, repo: Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else repo / path).resolve(strict=False)


def _matches(path: Path, patterns: list[tuple[str, Path]]) -> bool:
    return any(path == root if mode == "exact" else path == root or root in path.parents
               for mode, root in patterns)


_CODEX_VALUE_OPTIONS = {
    "-C", "--cd", "-s", "--sandbox", "-o", "--output-last-message",
    "--output-schema", "--color", "--thread-source", "--add-dir",
    "-i", "--image", "--enable", "--disable", "--model", "-m",
    "--config", "-c",
}
_CODEX_BOOLEAN_OPTIONS = {
    "--strict-config", "--json", "--skip-git-repo-check", "--ephemeral",
    "--ignore-rules", "--worktree", "--approve-for-me",
    "--dangerously-bypass-approvals-and-sandbox", "--dangerously-bypass-hook-trust",
}
_CLAUDE_VALUE_OPTIONS = {
    "--agent", "--agents", "--append-system-prompt", "--append-system-prompt-file", "--autocompact",
    "--debug-file", "--effort", "--environment", "--fallback-model",
    "--input-format", "--json-schema", "--max-budget-usd", "--model", "-n", "--name",
    "--output-format", "--permission-mode", "--plugin-dir", "--plugin-url",
    "--remote-control-session-name-prefix", "--session-id", "--setting-sources",
    "--settings", "--system-prompt", "--system-prompt-file",
}
_CLAUDE_BOOLEAN_OPTIONS = {
    "--allow-dangerously-skip-permissions", "--ax-screen-reader", "--bg", "--background",
    "--bare", "--brief", "--chrome", "-c", "--continue", "--fork-session", "--ide",
    "--dangerously-skip-permissions", "--disable-slash-commands", "--forward-subagent-text",
    "--exclude-dynamic-system-prompt-sections",
    "--include-hook-events", "--include-partial-messages", "--no-chrome", "--no-session-persistence",
    "--replay-user-messages", "--safe-mode", "--strict-mcp-config", "--verbose", "-p", "--print",
}
_CLAUDE_VARIADIC_OPTIONS = {
    "--add-dir", "--allowedTools", "--allowed-tools", "--betas", "--disallowedTools",
    "--disallowed-tools", "--file", "--mcp-config", "--tools",
}
_CLAUDE_OPTIONAL_OPTIONS = {
    "--cloud", "-d", "--debug", "--from-pr", "--prompt-suggestions", "--remote-control",
    "-r", "--resume", "--teleport", "--tmux", "-w", "--worktree",
}
_AGY_VALUE_OPTIONS = {
    "--add-dir", "--agent", "--conversation", "--effort", "--input-format", "--json-schema",
    "--log-file", "--mode", "--model", "--output-format", "--print-timeout", "--project",
}
_AGY_BOOLEAN_OPTIONS = {
    "-c", "--continue", "--dangerously-skip-permissions", "--disable-slash-commands",
    "--new-project", "--remote-control", "--sandbox",
}


def _scan_prompt(argv: list[str], executor: str) -> tuple[list[str], bool]:
    """Parse supported CLI options and return prompt argv tokens and stdin use."""
    if Path(argv[0]).name != executor:
        raise ValueError(f"{executor} prompt transport requires a matching executable")
    optional_options: set[str] = set()
    variadic_options: set[str] = set()
    prompt_options: set[str] = set()
    if executor == "codex":
        exec_index = 2 if argv[1:2] == ["--no-daemon"] else 1
        if len(argv) <= exec_index or argv[exec_index] != "exec":
            raise ValueError("Codex prompt transport requires codex exec")
        start = exec_index + 1
        value_options, boolean_options = _CODEX_VALUE_OPTIONS, _CODEX_BOOLEAN_OPTIONS
        variadic_options = {"-i", "--image"}
        short_values = {"-C", "-s", "-o", "-i", "-m", "-c"}
    elif executor == "claude":
        start = 1
        value_options, boolean_options = _CLAUDE_VALUE_OPTIONS, _CLAUDE_BOOLEAN_OPTIONS
        optional_options, variadic_options = _CLAUDE_OPTIONAL_OPTIONS, _CLAUDE_VARIADIC_OPTIONS
        short_values = {"-n", "-d", "-r", "-w"}
    else:
        start = 1
        value_options, boolean_options = _AGY_VALUE_OPTIONS, _AGY_BOOLEAN_OPTIONS
        prompt_options = {"-p", "--print", "--prompt", "-i", "--prompt-interactive"}
        short_values = set()
    prompts: list[str] = []
    stdin_required = False
    index = start
    after_delimiter = False
    while index < len(argv):
        token = argv[index]
        if after_delimiter:
            if executor == "agy" and not prompts:
                raise ValueError("agy prompt text must be a -p/--print/--prompt option value")
            prompts.append(token)
            index += 1
            continue
        if token == "--":
            after_delimiter = True
            index += 1
            continue
        if not token.startswith("-") or token == "-":
            if executor == "agy" and not prompts:
                raise ValueError("agy prompt text must be a -p/--print/--prompt option value")
            if executor == "codex" and not prompts and token in {"resume", "fork", "review", "help"}:
                raise ValueError("Codex exec subcommands do not provide the required initial prompt")
            prompts.append(token)
            index += 1
            continue
        name, separator, attached = token.partition("=")
        if not token.startswith("--") and len(token) > 2 and token[:2] in short_values:
            name, separator, attached = token[:2], "=", token[2:].removeprefix("=")
        if name in prompt_options:
            if separator:
                prompts.append(attached)
                index += 1
            elif index + 1 < len(argv) and (argv[index + 1] == "-" or not argv[index + 1].startswith("-")):
                prompts.append(argv[index + 1])
                index += 2
            else:
                index += 1
            continue
        if name in value_options or name in variadic_options or name in optional_options:
            if separator:
                value = attached
                index += 1
            elif index + 1 < len(argv) and (argv[index + 1] == "-" or not argv[index + 1].startswith("-")):
                value = argv[index + 1]
                index += 2
            elif name in optional_options:
                index += 1
                continue
            else:
                raise ValueError(f"{name} requires an option value, not a prompt")
            if name in variadic_options:
                while index < len(argv) and (argv[index] == "-" or not argv[index].startswith("-")):
                    index += 1
            if name == "--input-format" and value == "stream-json":
                stdin_required = True
            continue
        if token in boolean_options:
            index += 1
            continue
        raise ValueError(f"unsupported {executor} prompt transport option: {token}")
    return prompts, stdin_required or "-" in prompts


def _prompt_present(argv: list[str], executor: str) -> bool:
    """Recognize supported CLI prompts while preserving generic fixture checks."""
    if executor in {"codex", "claude", "agy"}:
        try:
            prompts, _ = _scan_prompt(argv, executor)
        except ValueError:
            return False
        return any(token.strip() and token != "-" for token in prompts)
    if "--" in argv:
        index = argv.index("--")
        return any(token.strip() for token in argv[index + 1:])
    return any(token.strip() and not token.startswith("-") for token in argv[1:])


def _surface_supplies_stdin(launch: dict[str, Any]) -> bool:
    """Preserve legacy markers only for generic, unsupported command fixtures."""
    if launch.get("stdinProvided") is True or launch.get("suppliedStdin") is True:
        return True
    for key in ("stdin", "stdinPath", "input", "inputPath"):
        value = launch.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, (dict, list)) and value:
            return True
    return False


def plan_order(order: dict[str, Any], policy: Any, *, check_fresh_outputs: bool = True) -> dict[str, Any]:
    """Return a deterministic plan; errors are diagnostics, never side effects.

    ``policy`` is the runner's PathPolicy. It is intentionally injected so the
    planner reuses canonical repo resolution and exact/recursive path rules.
    """
    diagnostics: list[dict[str, str]] = []
    if order.get("riskLevel") in {"medium", "high"}:
        diagnostics.append(_diagnostic("USER_RISK_DECISION", "warning", "riskLevel",
            f"{order['riskLevel']} risk: explain the concrete consequences and recommended checks to the user; "
            "the recorded user authorization decides whether to proceed. Risk classification is not a veto "
            "and does not require a V3 verifier or repeated approval for the same authorized action."))
    if order.get("orderVersion") != "AGENT_ORDER_JSON_V1":
        diagnostics.append(_diagnostic("ORDER_VERSION_UNSUPPORTED", "error", "orderVersion",
            "new tunnel ingress requires AGENT_ORDER_JSON_V1"))
    if not isinstance(order_id := order.get("orderId"), str) or not order_id.strip():
        diagnostics.append(_diagnostic("ORDER_ID_INVALID", "error", "orderId",
            "orderId must be a non-empty string before child launch"))
    launch = order.get("launch", {})
    candidate_value = launch.get("candidateJsonPath")
    candidate_backed = isinstance(candidate_value, str) and bool(candidate_value.strip())
    repo = policy.repo_path
    order_id = order.get("orderId", "")
    namespace = policy.control_namespace
    planned: list[tuple[str, Path, bool]] = []

    def add(label: str, value: Any, control: bool = False) -> None:
        if not isinstance(value, str) or not value.strip():
            return
        path = _resolve(value, repo)
        planned.append((label, path, control))
        if _matches(path, policy.forbidden):
            diagnostics.append(_diagnostic("PLANNED_PATH_FORBIDDEN", "error", label,
                f"planned path resolves into forbiddenPaths: {path}"))
        elif not _matches(path, policy.allowed):
            diagnostics.append(_diagnostic("PLANNED_PATH_NOT_ALLOWED", "error", label,
                f"planned path is not covered by allowedPaths (exact paths cover only themselves; use trailing /** for descendants): {path}"))
        if control and namespace not in path.parents:
            diagnostics.append(_diagnostic("CONTROL_PATH_OUTSIDE_ORDER_NAMESPACE", "error", label,
                f"control path must be a strict descendant of {namespace}; resolved path: {path}"))

    for field in ("resultJsonPath", "candidateJsonPath", "stdoutPath", "stderrPath"):
        if field in launch:
            add(f"launch.{field}", launch[field], control=True)
    if candidate_backed and "scratchPath" in launch:
        if not isinstance(launch["scratchPath"], str) or not launch["scratchPath"].strip():
            diagnostics.append(_diagnostic("PLANNED_PATH_INVALID", "error", "launch.scratchPath",
                "declared scratchPath must be a nonempty path under the fresh order namespace"))
        else:
            add("launch.scratchPath", launch["scratchPath"], control=True)
    contract = order.get("outputContract", {})
    if not isinstance(contract, dict):
        diagnostics.append(_diagnostic("OUTPUT_CONTRACT_INVALID", "error", "outputContract",
            "outputContract must be an object"))
        contract = {}
    elif contract.get("resultVersion") != "AGENT_RESULT_JSON_V1":
        diagnostics.append(_diagnostic("OUTPUT_SCHEMA_UNSUPPORTED", "error", "outputContract.resultVersion",
            "tunnel output must declare AGENT_RESULT_JSON_V1"))
    transports = contract.get("acceptedTransports")
    if transports is not None and (
        not isinstance(transports, list) or not transports or
        any(not isinstance(item, str) or item not in {"raw_json", "json_fence"} for item in transports)
    ):
        diagnostics.append(_diagnostic("TRANSPORT_UNSUPPORTED", "error", "outputContract.acceptedTransports",
            "acceptedTransports must be a non-empty list of raw_json/json_fence"))
    if contract.get("proseAllowedAfterJson") is True:
        diagnostics.append(_diagnostic("PROSE_TRANSPORT_UNSUPPORTED", "error", "outputContract.proseAllowedAfterJson",
            "prose after a candidate is not an unambiguous tunnel transport"))
    add("outputContract.resultPath", contract.get("resultPath"), control=True)

    for index, artifact in enumerate(order.get("expectedArtifacts", [])):
        if isinstance(artifact, dict):
            add(f"expectedArtifacts[{index}].path", artifact.get("path"))
            digest, media = artifact.get("sha256"), artifact.get("mediaType")
            if digest is not None or media is not None:
                if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                    diagnostics.append(_diagnostic("ARTIFACT_PREVIEW_SHA256_INVALID", "error",
                        f"expectedArtifacts[{index}].sha256", "supplied preview digest must be 64 lowercase hexadecimal characters"))
                if not isinstance(media, str) or "/" not in media or any(c.isspace() for c in media):
                    diagnostics.append(_diagnostic("ARTIFACT_PREVIEW_MEDIA_TYPE_INVALID", "error",
                        f"expectedArtifacts[{index}].mediaType", "supplied preview mediaType must be a nonempty media type"))
                if isinstance(artifact.get("path"), str) and isinstance(digest, str) and _SHA256.fullmatch(digest):
                    artifact_path = _resolve(artifact["path"], repo)
                    if artifact_path.is_file() and hashlib.sha256(artifact_path.read_bytes()).hexdigest() != digest:
                        diagnostics.append(_diagnostic("ARTIFACT_PREVIEW_DIGEST_MISMATCH", "error",
                            f"expectedArtifacts[{index}]", "supplied preview digest does not match current bytes"))
    for index, proof in enumerate(order.get("proofCommands", [])):
        if isinstance(proof, dict) and controller_context(order) is None:
            add(f"proofCommands[{index}].cwd", proof.get("cwd"))

    if candidate_backed:
        candidate = _resolve(candidate_value, repo)
        canonical = _resolve(str(contract.get("resultPath", "")), repo)
        launch_result = _resolve(str(launch.get("resultJsonPath", "")), repo)
        if candidate in {canonical, launch_result}:
            diagnostics.append(_diagnostic("CANDIDATE_CANONICAL_ALIAS", "error", "launch.candidateJsonPath",
                "raw candidate and canonical result must be distinct files"))
        if check_fresh_outputs:
            for path, label in ((candidate, "candidate"), (canonical, "canonical result")):
                if path.exists():
                    diagnostics.append(_diagnostic("OUTPUT_PREEXISTS", "error", label,
                        f"{label} output already exists before dispatch: {path}; use a fresh order namespace"))
        other_outputs = [(_resolve(launch[field], repo), f"launch.{field}")
                         for field in ("stdoutPath", "stderrPath") if isinstance(launch.get(field), str)]
        for output, label in other_outputs:
            if output in {candidate, canonical}:
                diagnostics.append(_diagnostic("OUTPUT_PATH_ALIAS", "error", label,
                    f"{label} aliases candidate or canonical result: {output}"))
        try:
            argv = shlex.split(launch.get("command", ""))
        except (TypeError, ValueError) as exc:
            argv = []
            diagnostics.append(_diagnostic("PROMPT_ARGV_INVALID", "error", "launch.command",
                f"launch.command cannot be tokenized safely: {exc}"))
        if argv:
            # Direct runner and Gateway transports do not provide controlled child
            # stdin. Metadata cannot turn the '-' sentinel into a real prompt.
            executor = order.get("executor", "")
            if executor in {"codex", "claude", "agy"}:
                try:
                    prompts, stdin_required = _scan_prompt(argv, executor)
                except ValueError as exc:
                    diagnostics.append(_diagnostic("PROMPT_ARGV_INVALID", "error", "launch.command", str(exc)))
                else:
                    # Only the established bare fixture uses a file adapter
                    # without declaring a CLI prompt transport.
                    legacy_direct_file_adapter = (executor == "agy" and argv == ["agy"]
                        and launch.get("surface") == "fixture" and "promptRequired" not in launch)
                    if stdin_required:
                        diagnostics.append(_diagnostic("STDIN_SENTINEL_UNAVAILABLE", "error", "launch.command",
                            "prompt transport requires stdin, but Gateway/direct runner supplies no controlled child stdin; pass prompt text as one argv token with text input"))
                    if not legacy_direct_file_adapter and (not prompts or not any(token.strip() and token != "-" for token in prompts)):
                        diagnostics.append(_diagnostic("PROMPT_MISSING", "error", "launch.command",
                            "candidate-backed dispatch requires a nonempty prompt argument; promptRequired and stdin metadata cannot establish transport"))
                    if len(prompts) > 1:
                        diagnostics.append(_diagnostic("PROMPT_ARGV_ARITY", "error", "launch.command",
                            "supported CLI prompt must be one argv token; quote multiword prompts in launch.command"))
            elif launch.get("promptRequired") is True and not _surface_supplies_stdin(launch):
                if "-" in argv:
                    diagnostics.append(_diagnostic("STDIN_SENTINEL_UNAVAILABLE", "error", "launch.command",
                        "launch.command contains the '-' stdin sentinel without declared fixture stdin"))
                if not _prompt_present(argv, executor):
                    diagnostics.append(_diagnostic("PROMPT_MISSING", "error", "launch.command",
                        "candidate-backed fixture requires a nonempty prompt argument when no stdin is declared"))
        else:
            diagnostics.append(_diagnostic("PROMPT_ARGV_INVALID", "error", "launch.command",
                "candidate-backed dispatch requires a nonempty, safely tokenized command"))
        if "handoff" in contract:
            handoff = contract["handoff"]
            if not isinstance(handoff, dict) or handoff.get("inReplyTo") != order_id:
                diagnostics.append(_diagnostic("HANDOFF_IDENTITY_STALE", "error", "outputContract.handoff.inReplyTo",
                    f"handoff inReplyTo must equal current orderId {order_id!r}"))
            elif handoff.get("version") != "AGENT_HANDOFF_V1" or handoff.get("schemaId") != "AGENT_RESULT_JSON_V1":
                diagnostics.append(_diagnostic("HANDOFF_IDENTITY_STALE", "error", "outputContract.handoff",
                    "handoff version/schemaId must identify the current AGENT_HANDOFF_V1 result contract"))
    if order.get("expectedArtifacts"):
        diagnostics.append(_diagnostic("FUTURE_ARTIFACT_DIGESTS_UNAVAILABLE", "info", "expectedArtifacts",
            "preflight validates supplied preview/template digests only; it cannot predict future executor artifact bytes"))

    # Keep forbidden subtree logic scoped to concrete planned paths: forbidden
    # patterns alone never conflict with an otherwise valid allowed subtree.
    unique = {(item["severity"], item["code"], item["path"], item["message"]): item for item in diagnostics}
    ordered = [unique[key] for key in sorted(unique)]
    planned_paths = [
        {"label": label, "path": str(path), "control": control}
        for label, path, control in sorted(planned, key=lambda item: (item[0], str(item[1]), item[2]))
    ]
    return {"version": "ORDER_PREFLIGHT_V1", "orderId": order_id,
            "controlNamespace": str(namespace), "candidateBacked": candidate_backed,
            "plannedPaths": planned_paths,
            "valid": not any(item["severity"] == "error" for item in ordered),
            "diagnostics": ordered}

