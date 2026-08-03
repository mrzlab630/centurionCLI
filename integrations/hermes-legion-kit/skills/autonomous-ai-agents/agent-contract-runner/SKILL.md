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

Use this portable skill for bounded `AGENT_ORDER_JSON_V1` dispatch and result acceptance. It ships only the runner, builder, ledger, review ladder, and their offline regressions.

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

## Commands and shipped proof

Run the dispatcher or validator with `scripts/agent_contract_runner.py` and use `scripts/agent_result_builder.py` to create a canonical result without inventing proof, promoting malformed/blocked/failed input to `done`, or overwriting the result path.

Python prerequisite: the existing `jsonschema` runtime must be available. This skill does not install it. The result builder resolves its schema in deterministic order: an explicit `--schema` or library argument, non-empty `AQUILA_AGENT_RESULT_SCHEMA`, the packaged `references/agent-result.schema.json`, non-empty `HERMES_HOME/contracts/agent-result.schema.json`, then `~/.hermes/contracts/agent-result.schema.json`.

From this skill's `scripts/` directory, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 regression_review_ladder.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_contract_runner.py
PYTHONDONTWRITEBYTECODE=1 python3 regression_agent_result_builder.py
```

The routing policy is installed at `../aquila-team-orchestration/references/review-routing-ladder-and-cost-control.md`.

## Safety boundaries

- Treat allowed paths as capability, not intent; preserve forbidden paths and actions.
- Require artifacts, scoped diffs, and exact proof outcomes; exit code alone is not proof.
- Keep result identity/history immutable and preserve malformed source bytes by hash.
- Do not use this skill to deploy, mutate live services, access secrets, or widen an order.
