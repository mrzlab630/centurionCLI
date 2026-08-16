---
description: Single-owner routing contract for CENTURION Legion work inside Antigravity.
---

# Single-Owner Routing

Every task must have exactly one primary Legionary owner.

## Contract

- One task -> one owner. The owner performs the work, keeps context, and reports the result.
- Other Legionaries are conditional handoffs, not co-owners.
- The owner calls a handoff only when a concrete trigger appears: missing facts, implementation need, proof design, security risk, UX decision, copy risk, localization risk, SEO risk, or domain-specific risk.
- Handoffs return a bounded artifact to the owner: finding, brief, patch, proof command, gate decision, or blocker.
- After a handoff, control returns to the owner. Do not create parallel committees for one task.
- Gate owners such as GUARDIAN, CENSOR, TESTER, and REVIEWER may block completion, but they do not become implementation owners unless the task changes.
- `AUXILIUM AGY` is an auxiliary executor, not a Legionary owner. Delegating a slice to `agy` never changes the primary owner.

## Routing Output

Antigravity-facing plans should use this shape:

```text
Owner: <LEGIONARY> / <skill-slug> - <responsibility>
Conditional handoffs:
- <LEGIONARY>: call only when <trigger>
Proof: <command, check, or artifact>
```

Avoid `adjacent`, `recommended team`, or `A + B owns` language. Those phrases blur responsibility.

## Escalation

If the owner lacks a needed capability, call exactly one matching Legionary for that missing capability. If multiple capabilities are missing, call them sequentially in dependency order and keep the owner as the coordinator.

## AUXILIUM AGY

Use `agy` only for bounded work that the owner can specify and verify: frontend slices, UI polish, reference briefs, UX copy variants, docs drafts, focused tests, or small reproducible fixes.

Delegation requirements:

- The owner writes the objective, allowed paths, non-goals, proof commands, and acceptance criteria before calling `agy`.
- `agy` must perform a self-review pass, fix confirmed defects, rerun proof, and report `SELF_REVIEW_FIXED=<yes/no>`.
- The owner then inspects the diff or artifact directly and reruns the relevant proof.
- TESTER, REVIEWER, GUARDIAN, or CENSOR gates still apply when proof, regression, security, external-source, or claim risk appears.

Do not delegate secrets, credentials, production deploys, database migrations, destructive commands, wallet/payment/KYC flows, exploit execution, or final architecture/security/legal/product-risk judgment to `agy`.
