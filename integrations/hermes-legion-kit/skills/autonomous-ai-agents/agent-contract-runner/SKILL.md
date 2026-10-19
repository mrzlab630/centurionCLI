---
name: agent-contract-runner
description: Canonical contract validation and Gateway adapter.
---

# agent-contract-runner

New orders use AGENT_ORDER_JSON_V1 and exact AGENT_HANDOFF_V1; results use AGENT_RESULT_JSON_V1. For policyVersion 3.0, workers return the author payload through the selected native adapter; `outputContract.resultPath` is Gateway-exclusive and workers never write it or invoke a finalizer. Legacy file-output contracts remain validation-only compatibility for existing non-3.0 orders and are not new dispatch authority. Only scripts/result_gateway.py creates the 3.0 canonical result and controller receipts and launches new 3.0 children; scripts/agent_contract_runner.py is shared validation. Preserve raw/final bytes and verify identity, typed arrays, hashes, paths and proof. Progress or exit zero is not acceptance. Model/effort policy is owned by controller routing. Historical contracts are validation-only, never automatic new dispatch.

Workers remain bounded; reviewers report findings and never edit product or assign
another reviewer. Core authority and mission budgets override recipe examples.

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
