# Claude Role Routing Rule

This file is a reviewed manual control-plane note. It records the approved
Claude/Codex routing policy without copying the full local SOUL, secrets, or
machine-specific settings. The installer does not apply it.

## Placement

Add the following clauses to the executor-routing section of the live
`SOUL.md`, next to the one-owner and independent-approval rules. Review the
surrounding text for conflicts before applying the clauses manually.

## Approved Clauses

- **Claude Opus 5-5: Principal independent reviewer.** Use the exact `claude-opus-5-5` route to inspect executor work and return evidence-backed findings to Aquila. If the primary is unavailable, pass `--fallback-model claude-opus-5` explicitly.
- **Claude Sonnet 5-5: Secondary execution route.** Use `claude-sonnet-5-5` as the primary Sonnet route and `claude-sonnet-5` only as its explicit fallback.
- **Claude Fable 5-1: Dormant/manual route.** The `claude-fable-5-1` -> `claude-fable-5` pair is documented for manual dispatch only; this repository owns no executable Fable integration or runtime default.
- **Codex remains the default implementation owner.** GPT-6 Luna at `medium` is the routine bounded default; `none`/`low` is reserved for exact mechanical work. Use `high` for non-trivial implementation, review, or raised evidence/risk needs. GPT-6.1 Sol handles implementation requiring judgment. GPT-6 Sol is fallback-only after verified pre-side-effect unavailability of GPT-6.1 Sol. High complexity, material ambiguity, cross-service/architecture/security, hard debugging, or long-horizon work requires GPT-6.1 Sol and task-appropriate raised effort. Any Codex implementation with a proof gap requires independent Claude review.
- **Corrections return to Luna/Sol.** Astra provides bounded ARCHITECTUS consultation for architecture and hard problems; Claude reviews the resulting implementation. A terminal reviewer cannot edit product files or apply its own findings.
- **Claude is not allowed to self-approve** implementation it owns. Legacy Claude execution remains readable by the validator, but is not the current implementation default. Under V2/V3 no independent reviewer route exists for Claude-owned implementation; block dispatch pending a separately approved route.
- Aquila retains final judgment over routing, review acceptance, and completion.
