---
description: Model routing and behavior rules for Antigravity agents using Gemini Pro, Gemini Flash, and Opus.
---

# Antigravity Model Routing

Use the smallest model that can complete the work without losing correctness.

## Gemini Pro 3.1

Use for:

- architecture and phase planning
- ambiguous requirements
- cross-module reasoning
- database/API contract decisions
- security-sensitive design
- large refactors where mistakes are expensive

Behavior:

- read local context before proposing changes
- identify assumptions and validation gates
- produce a concrete implementation path, not generic advice

## Gemini 3.5 Flash

Use for:

- fast repository search and summarization
- simple edits
- test failure triage when the failure is local and obvious
- documentation cleanup
- command/result summarization

Behavior:

- be concise
- avoid broad architecture changes
- escalate to Pro/Opus when uncertainty or blast radius grows

## Opus 4.6

Use for:

- adversarial review and WAR ROOM analysis
- security review
- hard debugging
- complex UI critique
- final pre-merge review of risky changes

Behavior:

- challenge assumptions
- look for hidden regressions, missing tests, data-contract mismatch, and runtime ownership issues
- prioritize findings with file/line evidence

## Default Escalation

Escalate from Flash to Pro/Opus when:

- more than one package/app boundary is touched
- auth, payments, wallet, delivery, admin, database, or runtime ownership is involved
- the task affects production deployment or live services
- the first attempted fix fails twice
- project docs and code disagree

