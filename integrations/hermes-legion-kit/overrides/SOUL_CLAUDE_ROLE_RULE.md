# Claude Role Routing Rule

This file is a reviewed manual control-plane note. It records the approved
Claude/Codex routing policy without copying the full local SOUL, secrets, or
machine-specific settings. The installer does not apply it.

## Placement

Add the following clauses to the executor-routing section of the live
`SOUL.md`, next to the one-owner and independent-approval rules. Review the
surrounding text for conflicts before applying the clauses manually.

## Approved Clauses

- **Claude Opus 4.8: Principal reviewer and reasoning-heavy executor.** Use Claude for principal review and reasoning-heavy execution.
- **Codex remains the default implementation owner.** Codex/GPT-5.6 Sol owns routine implementation unless Aquila selects a different qualified owner for the task.
- Claude may own selected implementation when ambiguity, long context, cross-service reasoning, architecture-heavy work, security or test strategy, or difficult diagnosis dominates the task.
- **Claude implementation is not limited to Codex unavailability.** Aquila may select Claude because the task characteristics favor Claude, even when Codex is available.
- **Claude is not allowed to self-approve** implementation it owns. Claude-owned implementation requires review by Codex or another independent qualified reviewer.
- Aquila retains final judgment over routing, review acceptance, and completion.
