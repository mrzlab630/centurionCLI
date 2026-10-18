---
name: agent-contract-runner
description: Canonical contract validation and Gateway adapter.
---

# agent-contract-runner

New orders use AGENT_ORDER_JSON_V1 and exact AGENT_HANDOFF_V1; results use AGENT_RESULT_JSON_V1. For policyVersion 3.0, workers return the author payload through the selected native adapter; `outputContract.resultPath` is Gateway-exclusive and workers never write it or invoke a finalizer. Legacy file-output contracts remain validation-only compatibility for existing non-3.0 orders and are not new dispatch authority. Only scripts/result_gateway.py creates the 3.0 canonical result and controller receipts and launches new 3.0 children; scripts/agent_contract_runner.py is shared validation. Preserve raw/final bytes and verify identity, typed arrays, hashes, paths and proof. Progress or exit zero is not acceptance. Model/effort policy is owned by controller routing. Historical contracts are validation-only, never automatic new dispatch.

Workers remain bounded; reviewers report findings and never edit product or assign
another reviewer. Core authority and mission budgets override recipe examples.
