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

## Hard scope and lifecycle controls

The user order and frozen plan are the scope ceiling. Adding a function,
behavior, file, test, test class, refactor, dependency, or plan step requires
explicit direct Boss approval in the current task; executor inference,
reviewer suggestions, and test failures never grant approval. The objective is
limited to one initial implementation attempt and at most one
finding-mapped correction. The correction may touch only the finding-mapped
behavior and its minimum proof. After the second product attempt, return
`blocked` and wait for a fresh Boss order/objective rather than widening scope.

Every plan step freezes acceptance criteria, allowed paths, expected artifacts,
and proof commands before execution. After each step, Aquila/controller checks
changed paths, artifact identity, proof results, and scope deviation; no next
step starts until the gate passes. Required proof closes the step and forbids
speculative continuation. Tests are permitted only for an acceptance
criterion, focused regression risk, or required risk gate. A failure outside
the frozen scope is a reported blocker, not authorization to repair that area.
Scope expansion requires unchanged-byte proof plus a fresh order.

## Cutover and routing metadata

For orders created at or after `2026-08-03T11:00:42Z`, provide exactly one compact `AQUILA_ROUTING_JSON_V1:` item in `notesForExecutor`. It identifies the objective and attempt; task class; complexity, risk, ambiguity, reversibility, and evidence need; executor, model, and reasoning effort; execution and verification profiles; reviewer; confidence; and reasons. Missing, duplicate, malformed, unknown, or incompatible metadata fails closed before dispatch.

The bounded ARCHITECTUS exception uses `executionProfile:"advisory"`,
`model:"gpt-6-astra"`, `executor:"codex"`, and a named architecture trigger.
It requires xhigh or higher effort, a read-only Codex sandbox, and control-only
artifacts. `reviewer:"none"` marks advice as non-review; the recorded V2/V3
floor and subsequent Opus 5 implementation review remain unchanged.
Use the canonical routing reference for the ordered advisory -> implementation
-> independent terminal review -> controller closure lineage. Linked Gateway
orders can declare explicit product files in `order.lineage`. The controller
verifies the predecessor's live files before dispatch, then binds accepted
order, result, receipts, and product bytes in a create-only manifest and anchor.
The final acceptance receipt must pass before a successor uses that anchor.
Direct runner and Loop V1 orders do not yet support lineage finalization.

Loop V1 binds accepted candidate result bytes and the assigned objective,
task class, reviewer, and verification floor in controller state. Review
dispatch and completion check this binding. A missing binding on an older
routed loop requires controller recovery from accepted evidence. Terminal
review results cannot report product edits or applied fixes; findings return
to the implementation owner. These checks do not freeze product bytes.

For UI/design/text/creative orders, `executor: agy` supports explicit
`model: gemini-3.8-flash` under the matching creative Legionary role. Pin
`--model gemini-3.8-flash` and matching `--effort low|medium|high`. Legacy
`model: agy` remains compatible but makes no runtime model guarantee.

For Codex implementation, Luna at `medium` is the routine bounded default;
use `high` for non-trivial work or raised evidence/risk needs. `none`/`low`
is limited to exact mechanical low-complexity work. Sol is required for complex, consequential,
hard-debugging, or long-horizon work, with `high` or `xhigh` as the applicable
effort floor. The launch validator binds the effective model and effort before
dispatch, including attached option forms and provider/profile overrides.

Use `scripts/review_ladder.py` to select V3, V2, V1, or V0 deterministically:

| Profile | Terminal route |
| --- | --- |
| V0 | Deterministic controller proof only, with every pre-execution trust predicate true. The legacy post-execution fields remain schema-compatible claims and never replace observed controller checks. |
| V1 | `gpt-6-sol` review for recoverable proof gaps in non-Codex implementations; Codex implementations with proof gaps require V2/Claude. |
| V2 | `claude-opus-5` for medium consequence, ambiguity, shared contracts, or hidden failure modes. |
| V3 | Currently blocked by the runner pending a trusted approval verifier; intended route is `claude-opus-5` plus an approved specialist/Boss gate for security, auth, secrets, money, production, dependencies, public endpoints, or infrastructure. |

Evaluate V3 first. V2/V3 never downgrade to `none` or Sol. A terminal reviewer uses `executionProfile:"terminal_review"`, `terminalGate:true`, and `reviewer:"none"`; it cannot appoint another reviewer. After that terminal gate, only deterministic identity, schema, hash, path, artifact, and proof checks remain—never review-of-review recursion.

## Ledger and history promotions

`scripts/attempt_ledger.py` appends immutable JSONL attempt history. Missing token or cost telemetry is `unmeasured`, never zero. For post-cutover routing, an explicit unavailable, unreadable, or malformed ledger fails closed; the default absent ledger is empty only for first-run compatibility. Record escaped V0 defects and Sol misses so the review ladder can promote future task classes: one medium/high V0 escape raises to V2, repeated low V0 escapes temporarily raise a class, and serious/repeated Sol misses promote to Claude.

All packaged Python control-plane reads use `scripts/strict_json.py`. Orders, candidates, canonical results, result schemas, attempt-ledger rows, loop state, and nested routing metadata reject duplicate object keys, `NaN`, `Infinity`, `-Infinity`, and float literals such as `1e999` that parse to a non-finite value. The independently installed monitor embeds equivalent strict semantics for order, result, schema, start-receipt, and closure JSON.

## Commands and shipped proof

### Compatible response ingress

`scripts/response_envelope.py` accepts raw UTF-8 JSON or exactly one lowercase
`json` fence with only JSON whitespace outside it. `outputContract.acceptedTransports`
can restrict this to `raw_json`; otherwise both `raw_json` and `json_fence` are
accepted. Orders and finalized results remain strict JSON. No prose extraction,
schema repair, or product retry is performed. Duplicate keys, non-finite values,
invalid Unicode, refusal, incomplete responses, and truncation fail closed.

New handoffs should declare `outputContract.handoff` with `version:AGENT_HANDOFF_V1`,
`schemaId:AGENT_RESULT_JSON_V1`, `inReplyTo:orderId`, `senderRole:roleForTask`,
`recipientRole:controller`, and optional `objectiveId` matching routing metadata.
The response echoes it exactly. Existing artifacts then require `mediaType` and
lowercase `sha256`; the controller checks actual bytes. Legacy V1 orders without
handoff remain supported. `responseEnvelope` is controller-owned and must never
be supplied by an executor. Raw and normalized bytes are retained separately;
hashes, sizes, raw-to-normalized binding, and candidate-to-result binding are
checked again after proof.

Direct AGY/Hermes and ordinary non-advisory Codex/Claude orders can opt into the
same builder with `launch.candidateJsonPath` under the order control namespace.
The executor writes that candidate; `launch.resultJsonPath` and
`outputContract.resultPath` still designate the distinct create-only canonical
result. Without `candidateJsonPath`, the legacy direct result stays strict JSON.
Candidate, evidence, and canonical outputs must be fresh before dispatch.
Native structured output is preferred only after confirming the active runtime
supports it. File transport plus controller validation is the supported fallback;
an instruction to return JSON is not a provider guarantee.

Run validation with `scripts/agent_contract_runner.py`. For external Codex or Claude dispatch, use `scripts/result_gateway.py`. The runner rejects direct Astra advisory dispatch; other direct `--mode run` launches create their own start, closure, and terminal acceptance receipts before and after observed proof. Linked lineage orders require the Gateway. `scripts/agent_result_builder.py` is an internal canonicalization stage used by the gateway after strict order/routing preflight and launcher closure. It never invents proof, promotes malformed/blocked/failed input to `done`, or overwrites the result path.

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

Use `--candidate-source file` for Codex file candidates. For Claude stdout use
`--candidate-source stdout`: the gateway waits for launcher closure and accepts a
single raw/fenced canonical result or the existing validated Claude event
object/array/JSONL transport with exactly one successful final result event.
Its inner result may use the same clean fence. Claude terminal success, runtime
model metadata, permission denials, and tool-loop checks still apply. Prose,
ambiguous envelopes, multiple results, and partial output remain digest-bound raw
evidence and fail closed. Every output parent must exist, and result, candidate,
start receipt, closure, stream, event, and evidence namespaces must not alias.

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

The monitor recomputes the canonical route from the strict order, verifies its deterministic digest, and requires exact routing equality across the order, start receipt, and closure before reporting `terminal-closure-verified`. Monitor exit 0 means the requested attempt has a verified terminal closure. It does not mean semantic success: inspect `controller-acceptance.json`, result status, and observed proof before acceptance. `controller-proof.json` records the post-execution proof gate; final acceptance is written after lineage and loop checks. Receipts are controller custody evidence, not a signature against a malicious same-uid writer. A requested model string is routing intent only and must never be reported as an observed runtime model; Aquila/controller must validate independent provider runtime-model evidence before task acceptance.

For linked orders, set `lineage` to an object with exactly `artifactPaths`, `deletedPaths`, `previousAnchorPath`, and `previousAnchorSha256`. Use explicit regular product files or deletion markers; do not name directories. Set both previous fields to `null` for the first order. The next order takes the prior `lineage-anchor.json` path and its controller-held SHA-256, and the Gateway checks its live product files before launching. The Gateway records the current anchor digest in its output; independently verify that anchor and terminal acceptance before claiming final closure. Legitimate edits to the same product path by the successor are allowed after preflight because historical custody bytes remain frozen. Existing orders without `lineage` remain valid and do not gain cross-order verification.

Lineage verifies integrity and custody of declared files but does not prove authorship: a file in `artifactPaths` proves the controller saw that file with that hash at finalization, not that the executor created it. Between preflight (checking predecessor) and finalization (reading successor), a concurrent same-UID process can alter files. Controller-owned manifest, trusted predecessor anchor digest, create-only receipts, and frozen predecessor verification protect against drift and ordinary mistakes in same-UID local development. For production or shared environments, immutable snapshots or external controller account isolation are required for stronger authorship and tamper resistance. Direct runner and Loop V1 orders do not yet support lineage finalization.

Every successor attempt requires a fresh `orderId` and fresh create-only result, start-receipt, and closure paths. Do not reuse or overwrite an earlier attempt's custody files. Installer activation is an external controller operation: back up the live targets, copy only the reviewed bytes, verify hashes and modes, and retain an exact rollback path. The installer does not provide that backup or rollback guarantee itself.

For advisory -> implementation -> review handoffs, `scripts/accepted_inputs.py`
verifies optional `inputResults`. Each exact entry contains `orderId`, `resultPath`,
`resultSha256`, `acceptancePath`, `acceptanceSha256`, `closurePath`, and `artifacts`
with `{path, sha256, mediaType}` references. Stage the predecessor order in its
control namespace. Only Gateway-accepted `done` results with passed proof and
matching order/start/closure/result/acceptance hashes are eligible. Selected
control artifacts are read-only inputs, checked before dispatch and after proof;
Gateway rechecks before terminal acceptance. Nested inputs preserve the chain.
Changed inputs reject acceptance without rewriting canonical results. Product
files still use the separate lineage contract; inputs do not expand write scope.

Python prerequisite: the existing `jsonschema` runtime must be available. This skill does not install it. The result builder resolves its schema in deterministic order: an explicit `--schema` or library argument, non-empty `AQUILA_AGENT_RESULT_SCHEMA`, the packaged `references/agent-result.schema.json`, non-empty `HERMES_HOME/contracts/agent-result.schema.json`, then `~/.hermes/contracts/agent-result.schema.json`.

From this skill's `scripts/` directory, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 regression_review_ladder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_contract_runner.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_result_builder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_result_gateway.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_response_envelope.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_accepted_inputs.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_accepted_inputs_gateway.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_legion_handoffs.py
```

The routing policy is installed at `../aquila-team-orchestration/references/review-routing-ladder-and-cost-control.md`.

## Safety boundaries

- Treat allowed paths as capability, not intent; preserve forbidden paths and actions.
- Require artifacts, scoped diffs, and exact proof outcomes; exit code alone is not proof.
- Keep result identity/history immutable and preserve malformed source bytes by hash.
- Do not use this skill to deploy, mutate live services, access secrets, or widen an order.
