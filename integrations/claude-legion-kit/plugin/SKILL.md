---
name: centurion-legion
description: Use for CENTURION Legion routing in Claude Code, one-owner task execution, WAR ROOM planning, Claude delegation control, and CLAUDE_ORDER v1 bounded implementation.
---

# CENTURION Legion For Claude Code

Use this skill when the user asks for Legionaries, WAR ROOM, Claude CLI optimization, controlled Claude execution, complex implementation, agent routing, or proof-heavy work.

## Core Contract

- One task has one primary Legionary owner.
- Other Legionaries are conditional handoffs or gates, not co-owners.
- If the owner lacks a needed capability, call or name the exact missing Legionary.
- Do not expand scope, add dependencies, browse unrelated files, or perform broad discovery unless the user or controlling order asks for it.
- Evidence beats self-report: tests, logs, diffs, schema checks, plugin validation, and direct artifact inspection.

## Claude Code Integration

Claude Code gives this plugin native control surfaces:

- `agents/*.md` defines the 37 Legionary subagents.
- `--agent <name>` can force a session to one owner.
- `--agents <json>` can define ephemeral bounded agents for one session.
- `--allowedTools`, `--disallowedTools`, `--tools`, and `--permission-mode` constrain what the model can do.
- `--mcp-config` plus `--strict-mcp-config` constrains MCP servers for a session.
- `--json-schema` constrains non-interactive structured output.
- `--safe-mode` and `--bare` are troubleshooting and isolation modes.

Prompting alone is not an obedience guarantee. For risky or implementation work, combine prompt constraints with tool restrictions, permission mode, result schema, and owner-side verification.

For Claude Opus 4.8, use `references/opus-4-8-profile.md` as the compact model profile. Do not use the large context window as a default; pass a CURATOR-style dossier and load exact references only when the owner needs them.

## Owner Selection

Default owner route:

- OPTIO / `orchestrator`: plan, route, mission prep.
- EXPLORATOR / `researcher`: local or web research, reference search, docs.
- CODER / `coder`: implementation.
- PICTOR / `pictor`: frontend UI implementation, responsive layouts, animation.
- AEDILIS / `aedilis`: UI/UX architecture, design systems, accessibility review.
- NOMENCLATOR / `nomenclator`: product language, CTA, labels, microcopy.
- TESTER / `tester`: tests, evals, regression proof.
- REVIEWER / `reviewer`: code review and regression risk.
- GUARDIAN / `security`: secrets, dependency, MCP, external-skill, permission, production, wallet/payment/KYC gates.
- CENSOR / `censor`: WAR ROOM, adversarial verification, assumptions.
- SIGNIFER / `git-master`: branches, commits, PRs, safe git.
- CURATOR / `context-optimizer`: skill-surface drift, context load, duplicate skills.

If no route is clear, use OPTIO first.

## CLAUDE_ORDER v1

Use `CLAUDE_ORDER v1` whenever Claude Code is asked to execute a bounded implementation slice or when a controller needs strict acceptance criteria.

Controller must provide:

- `Owner`: one Legionary slug or name.
- `Workspace`: exact path.
- `Allowed paths`: exact files/directories Claude may change.
- `Non-goals`: explicit exclusions.
- `Forbidden content patterns`: regex/text patterns that must not appear.
- `Proof commands`: commands to run or explain why unavailable.
- `Result file`: `CLAUDE_RESULT.json`.

Hard-stop rules:

- If needed work is outside allowed paths, stop and report `blocked`.
- If non-goals conflict with the task, stop and report `blocked`.
- Do not add dependencies, network calls, scripts, broad discovery, or extra files unless explicitly allowed.
- Read only files needed for the order and proof.
- Never modify secrets, credentials, production deploys, destructive state, wallet/payment/KYC flows, exploit execution, or final risk judgment unless the order explicitly names the target and proof gate.

Required result shape:

```json
{
  "orderVersion": "CLAUDE_ORDER_V1",
  "owner": "PICTOR",
  "status": "done",
  "filesChanged": ["relative/path", "CLAUDE_RESULT.json"],
  "proof": [{ "command": "npm test", "result": "passed", "summary": "..." }],
  "selfReviewFixed": "yes",
  "scopeViolations": [],
  "forbiddenPatternHits": [],
  "remainingRisks": []
}
```

Result typing is part of the contract: `filesChanged`, `proof`, `scopeViolations`, `forbiddenPatternHits`, and `remainingRisks` must be JSON arrays. Use an empty array (`[]`) for no findings; never use strings such as `"none"`. `filesChanged` must match the actual changed files, including `CLAUDE_RESULT.json`. For `status=done`, every `proof[].result` must be `"passed"`; use `status=blocked` if proof was not run or did not pass.

Final stdout for print-mode orders should contain only:

```text
CLAUDE_RESULT_FILE=CLAUDE_RESULT.json
STATUS=<done|blocked>
SELF_REVIEW_FIXED=<yes|no>
```

The controller must verify with `scripts/claude-order-guard.mjs`, rerun owner proof, and inspect the diff/artifact directly before accepting.

## WAR ROOM

For `WAR ROOM`, use three positions:

- Prosecutor: CENSOR/REVIEWER breaks the plan.
- Advocate: CODER/ARCHITECTUS defends feasibility and constraints.
- Judge: OPTIO chooses the smallest safe action and proof gate.

Verdict must list required fixes, owner, handoffs, proof commands, and residual risks.
