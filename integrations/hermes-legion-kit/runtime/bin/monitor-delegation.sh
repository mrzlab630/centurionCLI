#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: monitor-delegation.sh --order <order.json> --result <result.json> --start-receipt <start.json> --closure <closure.json> [--schema <schema.json>]" >&2
}

order_path=""
result_path=""
start_receipt_path=""
closure_path=""
schema_path=""

while (($# > 0)); do
  case "$1" in
    --order) order_path=${2-}; shift 2 ;;
    --result) result_path=${2-}; shift 2 ;;
    --start-receipt) start_receipt_path=${2-}; shift 2 ;;
    --closure) closure_path=${2-}; shift 2 ;;
    --schema) schema_path=${2-}; shift 2 ;;
    --help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$order_path" || -z "$result_path" || -z "$start_receipt_path" || -z "$closure_path" ]]; then
  usage
  exit 2
fi

if [[ -z "$schema_path" ]]; then
  runtime_or_home=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
  schema_path="$runtime_or_home/skills/autonomous-ai-agents/agent-contract-runner/references/agent-result.schema.json"
  if [[ ! -f "$schema_path" && "$(basename -- "$runtime_or_home")" == "runtime" ]]; then
    kit_root=$(cd -- "$runtime_or_home/.." && pwd -P)
    schema_path="$kit_root/skills/autonomous-ai-agents/agent-contract-runner/references/agent-result.schema.json"
  fi
fi

python3 - "$order_path" "$result_path" "$start_receipt_path" "$closure_path" "$schema_path" <<'PY'
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROUTING_PREFIX = "AQUILA_ROUTING_JSON_V1:"
ROUTING_CUTOVER = datetime(2026, 8, 3, 11, 0, 42, tzinfo=timezone.utc)

def fail(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


try:
    from jsonschema import Draft202012Validator
except ImportError as exc:
    fail(f"jsonschema prerequisite is unavailable: {exc}")


def strict_json_loads(text, label):
    def reject_constant(value):
        raise ValueError(f"non-finite constant {value}")

    def reject_duplicate_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate key {key!r}")
            value[key] = item
        return value

    def reject_non_finite_float(literal):
        parsed = float(literal)
        if not math.isfinite(parsed):
            raise ValueError(f"non-finite numeric literal {literal}")
        return parsed

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_float=reject_non_finite_float,
        )
    except (json.JSONDecodeError, TypeError, ValueError, OverflowError) as exc:
        fail(f"{label} is not strict JSON: {exc}")


def load_object(path, label):
    if path.is_symlink():
        fail(f"{label} must not be a symlink: {path}")
    if not path.is_file():
        fail(f"{label} missing or not a regular file: {path}")
    try:
        content = path.read_bytes()
        decoded = content.decode("utf-8")
    except FileNotFoundError:
        fail(f"{label} missing: {path}")
    except (OSError, UnicodeDecodeError) as exc:
        fail(f"{label} is not valid JSON: {exc}")
    value = strict_json_loads(decoded, label)
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value, content


def parse_timestamp(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} is missing")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        fail(f"{label} is not an ISO-8601 timestamp")
    if parsed.tzinfo is None:
        fail(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def resolved_field(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} is missing")
    return Path(value).expanduser().resolve(strict=False)


def routing_binding(order, created_at):
    if created_at < ROUTING_CUTOVER:
        return None, None
    notes = order.get("notesForExecutor")
    if not isinstance(notes, list):
        fail("post-cutover order notesForExecutor must be an array")
    entries = [item for item in notes if isinstance(item, str) and item.startswith(ROUTING_PREFIX)]
    if len(entries) != 1:
        fail("post-cutover order must contain exactly one routing entry")
    entry = entries[0]
    routing = strict_json_loads(entry[len(ROUTING_PREFIX):], "order routing metadata")
    if not isinstance(routing, dict):
        fail("order routing metadata must be a JSON object")
    canonical_entry = ROUTING_PREFIX + json.dumps(routing, ensure_ascii=False, separators=(",", ":"))
    if entry != canonical_entry:
        fail("order routing metadata must be compact canonical JSON")
    canonical = json.dumps(routing, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return routing, hashlib.sha256(canonical).hexdigest()


order_path, result_path, start_receipt_path, closure_path, schema_path = map(Path, sys.argv[1:])
resolved_paths = [path.expanduser().resolve(strict=False) for path in (order_path, result_path, start_receipt_path, closure_path)]
if len(set(resolved_paths)) != len(resolved_paths):
    fail("order, result, start receipt, and closure paths must be distinct")
order, order_bytes = load_object(order_path, "order")
result, result_bytes = load_object(result_path, "canonical result")
schema, _ = load_object(schema_path, "result schema")
errors = sorted(Draft202012Validator(schema).iter_errors(result), key=lambda item: (list(item.absolute_path), item.message))
if errors:
    first = errors[0]
    field = ".".join(str(part) for part in first.absolute_path) or "<root>"
    fail(f"canonical result schema validation failed at {field}: {first.message}")
if result.get("orderId") != order.get("orderId"):
    fail("canonical result orderId does not match order")
if result.get("executor") != order.get("executor"):
    fail("canonical result executor does not match order")
if result.get("status") not in {"done", "blocked", "failed"}:
    fail("canonical result status is not allowed")

order_digest = hashlib.sha256(order_bytes).hexdigest()
order_created_at = parse_timestamp(order.get("createdAt"), "order.createdAt")
routing, routing_sha256 = routing_binding(order, order_created_at)
start, start_bytes = load_object(start_receipt_path, "launcher start receipt")
expected_start = {
    "startReceiptVersion": "RESULT_GATEWAY_START_V1",
    "eventNamespace": "aquila.result_gateway.v1",
    "state": "started",
    "orderId": order.get("orderId"),
    "executor": order.get("executor"),
    "orderSha256": order_digest,
    "routing": routing,
    "routingSha256": routing_sha256,
}
for key, value in expected_start.items():
    if start.get(key) != value:
        fail(f"launcher start receipt {key} mismatch")
run_id = start.get("runId")
if not isinstance(run_id, str) or re.fullmatch(r"[0-9a-f]{64}", run_id) is None:
    fail("launcher start receipt runId is invalid")
started_at = parse_timestamp(start.get("startedAt"), "launcher start receipt startedAt")
now = datetime.now(timezone.utc)
if started_at < order_created_at:
    fail("launcher start receipt is stale relative to order.createdAt")
if started_at > now + timedelta(minutes=5):
    fail("launcher start receipt startedAt is implausibly in the future")
if resolved_field(start.get("orderPath"), "launcher start receipt orderPath") != order_path.resolve(strict=False):
    fail("launcher start receipt orderPath mismatch")
if resolved_field(start.get("resultPath"), "launcher start receipt resultPath") != result_path.resolve(strict=False):
    fail("launcher start receipt resultPath mismatch")
if resolved_field(start.get("startReceiptPath"), "launcher start receipt startReceiptPath") != start_receipt_path.resolve(strict=False):
    fail("launcher start receipt startReceiptPath mismatch")
if resolved_field(start.get("closurePath"), "launcher start receipt closurePath") != closure_path.resolve(strict=False):
    fail("launcher start receipt closurePath mismatch")
if start.get("candidateSource") not in {"file", "stdout"}:
    fail("launcher start receipt candidateSource is invalid")
for key in ("candidatePath", "evidenceDirectory"):
    resolved_field(start.get(key), f"launcher start receipt {key}")
for key in ("stdoutPath", "stderrPath"):
    if start.get(key) is not None:
        resolved_field(start[key], f"launcher start receipt {key}")

closure, _ = load_object(closure_path, "launcher closure")
expected = {
    "closureVersion": "RESULT_GATEWAY_CLOSURE_V2",
    "eventNamespace": "aquila.result_gateway.v1",
    "orderId": order.get("orderId"),
    "executor": order.get("executor"),
    "orderSha256": order_digest,
    "runId": run_id,
    "startedAt": start.get("startedAt"),
    "startReceiptSha256": hashlib.sha256(start_bytes).hexdigest(),
    "state": "closed",
    "launcherClosed": True,
    "canonicalFinalized": True,
    "canonicalStatus": result.get("status"),
    "routing": routing,
    "routingSha256": routing_sha256,
}
for key, value in expected.items():
    if closure.get(key) != value:
        fail(f"launcher closure {key} mismatch")
if resolved_field(closure.get("orderPath"), "launcher closure orderPath") != order_path.resolve(strict=False):
    fail("launcher closure orderPath mismatch")
if resolved_field(closure.get("startReceiptPath"), "launcher closure startReceiptPath") != start_receipt_path.resolve(strict=False):
    fail("launcher closure startReceiptPath mismatch")
if resolved_field(closure.get("canonicalResultPath"), "launcher closure canonicalResultPath") != result_path.resolve(strict=False):
    fail("launcher closure canonicalResultPath mismatch")
digest = hashlib.sha256(result_bytes).hexdigest()
if closure.get("canonicalResultSha256") != digest:
    fail("launcher closure canonicalResultSha256 mismatch")
closed_at = parse_timestamp(closure.get("closedAt"), "launcher closure closedAt")
if closed_at < started_at:
    fail("launcher closure closedAt precedes startedAt")
if closed_at > now + timedelta(minutes=5):
    fail("launcher closure closedAt is implausibly in the future")
if not isinstance(closure.get("childStarted"), bool):
    fail("launcher closure childStarted is invalid")
if not isinstance(closure.get("timedOut"), bool) or not isinstance(closure.get("drainTimedOut"), bool):
    fail("launcher closure timeout state is invalid")

print(json.dumps({"status": "terminal-closure-verified", "resultStatus": result["status"], "orderId": result["orderId"], "runId": run_id, "routingSha256": routing_sha256}, sort_keys=True))
PY
