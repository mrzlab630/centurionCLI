---
description: Model routing and behavior rules for Gemini 3.8 Flash and the CENTURION executor, advisor, and reviewer routes.
---

# Antigravity Model Routing

The controller selects the model for the bounded specialty. Models do not
change ownership, scope, or acceptance authority.

## GPT-6 Luna And Sol

Luna handles clear bounded implementation; Sol handles uncertain, complex,
or consequential code and diagnosis. Return those tasks to the controller for
a Codex order. A Gemini session cannot silently change the model or assume
another executor's authority.

## GPT-6 Astra

Request ARCHITECTUS consultation for architecture ambiguity, cross-system
tradeoffs, or hard diagnosis. Advice is read-only and returns to the controller;
Luna/Sol implement the accepted decision and Opus independently reviews it.

## Gemini 3.8 Flash

Use for:

- UI and frontend production under PICTOR
- design alternatives and visual review under AEDILIS
- UX copy, localization, social text, and creative drafts under the matching owner
- bounded documentation and content production

Behavior:

- pin `--model gemini-3.8-flash` and `--effort low|medium|high`
- keep the assigned role, exact files, AGY guard, and owner-side proof
- return uncertainty and findings to the controller for routing

## Claude Opus 5

Use for:

- adversarial review and WAR ROOM analysis
- security review
- independent diagnosis of executor failures
- complex UI critique
- final pre-merge review of risky changes

Behavior:

- challenge assumptions
- look for hidden regressions, missing tests, data-contract mismatch, and runtime ownership issues
- prioritize findings with file/line evidence
- return required fixes to the controller for a fresh Luna/Sol order
- never implement findings while serving as terminal reviewer

## Default Escalation

Return to the controller for Sol, Astra consultation, or Opus review when:

- more than one package/app boundary is touched
- auth, payments, wallet, delivery, admin, database, or runtime ownership is involved
- the task affects production deployment or live services
- the first attempted fix fails twice
- project docs and code disagree
