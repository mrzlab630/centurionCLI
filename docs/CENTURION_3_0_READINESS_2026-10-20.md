# CENTURION 3.0 readiness — 2026-10-20

Candidate: `3.0.0-rc.2` on `feat/centurioncli/v3-implementation`.
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


Isolated current-source installs passed for Codex, Hermes and Claude, each
writing a `CENTURION_INSTALLED_CHAIN_V1` manifest with product version
`3.0.0-rc.2`. No live home was used by these installs.

## Remaining gate before N8

Status: **prepared_pending_capability_refresh**.

The previous native capability receipts were bound to the old adapter SHA and
are invalidated by this change. The cutover package contains a new preparation
namespace under `.centurion/v3-rollout-prep-20261020/installer/`, but its native
probes were not rerun; those records must not authorize dispatch yet.

N8 still requires, in order:

1. Fresh maintenance capability probes for every enabled client and fresh
   evidence hashes against the current adapter.
2. Version-scoped instruction migration after a targeted backup and preimage
   check.
3. External no-new-work drain, service stop only after idle/ingress proof, and
   sequential Codex → Claude → Hermes installation.
4. Installed hash/mode/effective-instruction readback and one harmless Gateway
   canary proving canonical result/controller acceptance.

Historical direct-dispatch regression mains remain intentionally excluded from
3.0; they are not silently relabeled as passing. No live install, service
restart, drain, production dispatch or canary was performed in this readiness
pass.
