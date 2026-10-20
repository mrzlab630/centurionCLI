# CENTURION 3.0 readiness — 2026-10-20

Candidate: `3.0.0-rc.2`, sourced from `feat/centurioncli/v3-implementation`.
Release commit `0fcdd16` contains the bounded-capture fix in
`integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/result_gateway.py`.

## Completed in this continuation

The Gateway now stops appending stdout after an oversized frame is detected and
caps the incomplete capture at `MAX_FRAME_BYTES + 65536`. The existing
`captureLimited` error path and owned-process cleanup remain active.

Current adapter SHA-256: `3afe864194e230bd8730778fe9f5338b6d536595564cbb30feba8a85778a59fe`.
The release commit is the reproducible source snapshot for this readiness record.

Offline proof on the current bytes:

- `regression_result_gateway_v3.py` — PASS: 24 groups
- `regression_order_preflight.py` — PASS: 13 groups
- `regression_review_ladder.py` — PASS: 19 groups
- `node integrations/hermes-legion-kit/scripts/smoke.mjs` — PASS: isolated fixture and packaged runtime regressions; live capability unverified
- `legion-skill-eval` — PASS
- `skill-surface-audit` — PASS; duplicateNameCount=0; driftedDuplicateCount=0; brokenReferences=0
- `codex-and-claude-smoke` — PASS
- `open-design-tests` — PASS: 64/64
- `python-unittest` — PASS: 23/23
- `syntax-and-diff-check` — PASS


The live sequential rollout completed for Codex → Claude → Hermes. Each live
home now has a `CENTURION_INSTALLED_CHAIN_V1` manifest with product version
`3.0.0-rc.2`; installed file hashes, modes and effective instruction readback
passed. Rollback batch IDs are recorded in the rollout preparation receipt.

## N8 rollout result

Status: **installed_and_canary_verified**.

Fresh capability probes passed for the installed Codex, Claude and Hermes
surfaces against adapter SHA-256
`3afe864194e230bd8730778fe9f5338b6d536595564cbb30feba8a85778a59fe`.
The installed Hermes Gateway is running with Telegram and Mattermost connected,
zero active agents, no active work and no ESTOP marker.

The harmless real-provider Gateway canary passed through the installed Hermes
Gateway:

- policy version: `3.0`;
- executor/model: `codex` / `gpt-6.1-sol` (`xhigh`);
- canonical result: `done`;
- controller acceptance and proof: `passed`;
- product files changed: `[]`.

Evidence: `.centurion/n8-real-canary-20261020T132226Z/canary-record.json` and
its `controller-acceptance.json` / `controller-proof.json` records. Historical
direct-dispatch regression mains remain intentionally excluded from 3.0.
