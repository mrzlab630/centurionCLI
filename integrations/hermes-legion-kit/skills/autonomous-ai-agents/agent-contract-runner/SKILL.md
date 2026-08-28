---
name: agent-contract-runner
description: Validate Aquila AGENT_ORDER_JSON_V1 handoffs, enforce V0-V3 review routing, build canonical results, and verify bounded executor artifacts. Use when Aquila dispatches or accepts a contract-runner order.
version: 0.4.0
author: Aquila
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [aquila, agent-contracts, delegation, routing, verification]
    related_skills: [aquila-team-orchestration]
---

# Agent Contract Runner

Use this portable skill for bounded `AGENT_ORDER_JSON_V1` dispatch and result acceptance. It ships the runner, controller-owned Result Gateway, builder, fail-closed monitor, ledger, review ladder, and their offline regressions.

## Cutover and routing metadata

For orders created at or after `2026-08-03T11:00:42Z`, provide exactly one compact `AQUILA_ROUTING_JSON_V1:` item in `notesForExecutor`. It identifies the objective and attempt; task class; complexity, risk, ambiguity, reversibility, and evidence need; executor, model, and reasoning effort; execution and verification profiles; reviewer; confidence; and reasons. Missing, duplicate, malformed, unknown, or incompatible metadata fails closed before dispatch.

Use `scripts/review_ladder.py` to select V3, V2, V1, or V0 deterministically:

| Profile | Terminal route |
| --- | --- |
| V0 | Deterministic controller proof only, with every trust predicate true. |
| V1 | `gpt-5.6-sol` review for recoverable proof gaps. |
| V2 | `claude-opus-5` for medium consequence, ambiguity, shared contracts, or hidden failure modes. |
| V3 | `claude-opus-5` plus an approved specialist/Boss gate for security, auth, secrets, money, production, dependencies, public endpoints, or infrastructure. |

Evaluate V3 first. V2/V3 never downgrade to `none` or Sol. A terminal reviewer uses `executionProfile:"terminal_review"`, `terminalGate:true`, and `reviewer:"none"`; it cannot appoint another reviewer. After that terminal gate, only deterministic identity, schema, hash, path, artifact, and proof checks remain—never review-of-review recursion.

## Ledger and history promotions

`scripts/attempt_ledger.py` appends immutable JSONL attempt history. Missing token or cost telemetry is `unmeasured`, never zero. For post-cutover routing, an explicit unavailable, unreadable, or malformed ledger fails closed; the default absent ledger is empty only for first-run compatibility. Record escaped V0 defects and Sol misses so the review ladder can promote future task classes: one medium/high V0 escape raises to V2, repeated low V0 escapes temporarily raise a class, and serious/repeated Sol misses promote to Claude.

All packaged Python control-plane reads use `scripts/strict_json.py`. Orders, candidates, canonical results, result schemas, attempt-ledger rows, loop state, and nested routing metadata reject duplicate object keys, `NaN`, `Infinity`, `-Infinity`, and float literals such as `1e999` that parse to a non-finite value. The independently installed monitor embeds equivalent strict semantics for order, result, schema, start-receipt, and closure JSON.

## Commands and shipped proof

Run the dispatcher or validator with `scripts/agent_contract_runner.py`. All external Codex or Claude candidate finalization goes through `scripts/result_gateway.py`; `scripts/agent_result_builder.py` is an internal canonicalization stage used by the gateway after strict order/routing preflight and launcher closure. It never invents proof, promotes malformed/blocked/failed input to `done`, or overwrites the result path.

## Control artifact namespace

For every new `AGENT_ORDER_JSON_V1`, derive the controller-owned namespace from
the resolved `workspace.repoPath` and the fresh, safe single-component
`orderId`:

```text
<repo>/.centurion/agents_results/<orderId>/
```

Canonical results, raw candidates, launcher start/closure receipts, executor
stdout/stderr captures, gateway events, and gateway evidence must be strict
descendants of that directory. The runner and gateway derive this path rather
than trusting a caller-supplied project namespace, and reject traversal,
separators, root-level names, and other escapes before launch or custody
creation. `expectedArtifacts`, `filesChanged`, and result-reported product or
application artifacts remain governed by declared `allowedPaths`; they are not
automatically forced into the control namespace.

Each successor attempt uses a fresh `orderId` and create-only control paths.
Existing root-level legacy files are not moved by validation; cleanup or
migration is a separate, explicitly reviewed operation.

For direct Codex or Claude launches, invoke `scripts/result_gateway.py` instead of launching the executor in the background yourself. Keep the executor transport output in a raw candidate path that is distinct from the canonical result, stdout, stderr, event log, and closure receipt:

```bash
CONTROL_DIR="$PWD/.centurion/agents_results/<orderId>"
python3 scripts/result_gateway.py \
  --order /path/to/order.json \
  --candidate "$CONTROL_DIR/raw-candidate.json" \
  --candidate-source file \
  --start-receipt "$CONTROL_DIR/launcher-start.json" \
  --closure "$CONTROL_DIR/launcher-closure.json" \
  --evidence-dir "$CONTROL_DIR/evidence" \
  --events "$CONTROL_DIR/result-gateway.events.jsonl"
```

Use `--candidate-source file` for Codex file candidates. For Claude commands that emit the canonical result only on stdout, use `--candidate-source stdout`; the gateway captures raw stdout, waits for launcher closure, and materializes the candidate path only when the entire stdout stream is one strict unfenced schema-valid identity-matching `AGENT_RESULT_JSON_V1` object. Duplicate keys, non-finite numbers, prose, envelopes, multiple objects, and partial output remain digest-bound raw evidence and fail closed. The evidence directory and every output parent must already exist as writable directories, and result, candidate, start receipt, closure, stream, event, and evidence namespaces must not alias.

Before checking or creating any candidate, stream, result, start-receipt, closure, event, or evidence output, the gateway runs the full canonical `agent_contract_runner.validate_order` path, including attempt-ledger-aware `validate_order_routing`. Invalid routing therefore returns nonzero before any child launch or custody/stream artifact. After validation, the gateway binds the exact canonical routing metadata and its deterministic `routingSha256` digest into both the start and closure receipts.

The gateway then reads the child command and timeout from `order.launch`, creates a fresh start receipt, launches the child exactly once without a shell, waits for bounded process and pipe closure, captures stdout/stderr, and only then asks the internal builder to create the canonical result. The receipts also bind exact order bytes, a cryptographically random gateway run ID, timestamps, receipt paths, the start-receipt digest, and the canonical-result digest. Timeouts and controller capture failures produce a failed result where the canonical path remains writable. A valid matching candidate preserves its `done`, `blocked`, or `failed` status even when the child exits nonzero; the gateway process still returns nonzero for the nonzero launcher exit. There is no automatic retry after child launch.

After gateway closure, the installed controller monitor verifies terminal closure only when the canonical result is schema-valid and identity-matching and the matching digest-bound start and closure receipts are present:

```bash
monitor-delegation.sh \
  --order /path/to/order.json \
  --result "$CONTROL_DIR/AGENT_RESULT.json" \
  --start-receipt "$CONTROL_DIR/launcher-start.json" \
  --closure "$CONTROL_DIR/launcher-closure.json"
```

The monitor recomputes the canonical route from the strict order, verifies its deterministic digest, and requires exact routing equality across the order, start receipt, and closure before reporting `terminal-closure-verified`. Monitor exit 0 means the requested attempt has a verified terminal closure. It does not mean semantic success: inspect the separately reported result status and all proof before acceptance. Receipts are controller custody evidence, not a signature against a malicious same-uid writer. A requested model string is routing intent only and must never be reported as an observed runtime model; Aquila/controller must validate independent provider runtime-model evidence before task acceptance.

Every successor attempt requires a fresh `orderId` and fresh create-only result, start-receipt, and closure paths. Do not reuse or overwrite an earlier attempt's custody files. Installer activation is an external controller operation: back up the live targets, copy only the reviewed bytes, verify hashes and modes, and retain an exact rollback path. The installer does not provide that backup or rollback guarantee itself.

Python prerequisite: the existing `jsonschema` runtime must be available. This skill does not install it. The result builder resolves its schema in deterministic order: an explicit `--schema` or library argument, non-empty `AQUILA_AGENT_RESULT_SCHEMA`, the packaged `references/agent-result.schema.json`, non-empty `HERMES_HOME/contracts/agent-result.schema.json`, then `~/.hermes/contracts/agent-result.schema.json`.

From this skill's `scripts/` directory, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 regression_review_ladder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_contract_runner.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_result_builder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_result_gateway.py
```

The routing policy is installed at `../aquila-team-orchestration/references/review-routing-ladder-and-cost-control.md`.

## Safety boundaries

- Treat allowed paths as capability, not intent; preserve forbidden paths and actions.
- Require artifacts, scoped diffs, and exact proof outcomes; exit code alone is not proof.
- Keep result identity/history immutable and preserve malformed source bytes by hash.
- Do not use this skill to deploy, mutate live services, access secrets, or widen an order.
