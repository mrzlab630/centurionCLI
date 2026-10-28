---
name: agent-contract-runner
description: Canonical contract validation and Gateway adapter.
---

# agent-contract-runner

Before preparing a packet or launch, apply "Project scope lock and external
dependencies" in skills/orchestrator/SKILL.md relative to the installed client
home. Missing Gateway/verifier/routing capability is an external product blocker,
not permission to prepare a repair or approval request. Use the existing blocked
result/state; `BLOCKED_EXTERNAL_DEPENDENCY` is a reporting disposition, not a new
schema enum. This adapter adds no maintenance, bootstrap or bypass authority.

New orders use AGENT_ORDER_JSON_V1 and exact AGENT_HANDOFF_V1; results use AGENT_RESULT_JSON_V1. For policyVersion 3.0, workers return the author payload through the selected native adapter; `outputContract.resultPath` is Gateway-exclusive and workers never write it or invoke a finalizer. Legacy file-output contracts remain validation-only compatibility for existing non-3.0 orders and are not new dispatch authority. Only scripts/result_gateway.py creates the 3.0 canonical result and controller receipts and launches new 3.0 children; scripts/agent_contract_runner.py is shared validation. Preserve raw/final bytes and verify identity, typed arrays, hashes, paths and proof. Progress or exit zero is not acceptance. Model/effort policy is owned by controller routing. Historical contracts are validation-only, never automatic new dispatch.

## User authorization and risk warnings

The user's recorded instruction is the action authority. Explain concrete risks
and recommended checks; the user decides. Preflight reports medium/high risk as
`USER_RISK_DECISION` with severity `warning`, never an automatic dispatch denial.
Do not request the same permission repeatedly after approval. Verification is
selected in the approved mission, not imposed by a risk label or defect history.
V3's unavailable verifier and automatic specialist gate are retired. Historical
V3 metadata remains readable with V2 review semantics and no separate approval
store. Keep the exact authorized scope, real evidence and Gateway custody.

Workers remain bounded; reviewers report findings and never edit product or assign
another reviewer. Core authority and mission budgets override recipe examples.

Apply the core's "Report recovery and verification of saved work": malformed
reporting alone never justifies a product rerun. `--recover-report` collects
successive isolated reporting ordinals within the approved shared budget and
stops on identical invalid responses. `--recover-report-from` collects exact
controller-authorized manual-review bytes without a model launch. Required
product proof and user-selected review still apply. Use the runner's
`--continue-mission` with a state-bound owner decision to register manual review
or extend budget; preserve all spent counters, raw output and finalized results.

New policy 3.0 model launches use `launch.timeoutSeconds: null` with mission
`budget.deadlineAt: null` for monitored execution without a lifetime cutoff.
Finite values are honored only when explicitly selected; existing missions and
receipts are not rewritten. Read periodic Gateway `process_observed` events;
liveness/output activity is not evidence of productive progress or acceptance.
Silence alone never kills or replays a worker. Stop the owning Gateway through
SIGTERM/SIGINT; do not modify locked state. Stop cleanup remains bounded and
checks process identity. Output caps, count budgets and no-replay rules still apply.
Periodic pings are read-only local diagnostics, not model turns. They record
local CPU/output activity and `alive_active|alive_waiting|exited|unknown`;
`modelStatus` stays `unknown` without a provider signal bound to this request.
A failed diagnostic identity/activity read is recorded and retried at the next
observation without killing the child. Initial custody and stop identity checks
remain mandatory. Hours without output or heartbeat never prove a hang.
