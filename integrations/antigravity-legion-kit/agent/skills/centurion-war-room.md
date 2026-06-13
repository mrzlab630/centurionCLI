---
name: centurion-war-room
description: Adversarial planning, debugging, and verification protocol for difficult Antigravity tasks.
---

# CENTURION WAR ROOM

Use this skill when the user says `WAR ROOM`, when a bug survived a simple fix, or when the change touches security, payments, runtime, database, admin actions, or user-visible state.

## Protocol

1. Recon: read project docs, git state, relevant code, scripts, and runtime/process state if applicable.
2. Debate: evaluate from three roles:
   - OPTIO: scope, phase, plan, dependencies
   - GUARDIAN: security, secrets, abuse paths, unsafe assumptions
   - TESTER: reproducibility, gates, missing proof
3. Action: implement the smallest change that addresses the root cause.
4. Probatio: run the strongest feasible proof in the same session.
5. Report: findings first when reviewing, otherwise concise summary plus proof.

## Failure Modes To Catch

- client-owned state used as source of truth
- build passing without typecheck
- UI fixed visually but not verified at mobile size
- PM2/tmux/port ownership confusion
- route/API contract drift
- admin mutation without actor/reason/idempotency/audit
- payment/wallet/delivery mutation without ledger/idempotency

