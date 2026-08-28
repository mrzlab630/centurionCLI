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
- `skills/open-design-producer` is installed as a shared production capability;
  it is not a 38th owner or subagent.
- `--agent <name>` can force a session to one owner.
- `--agents <json>` can define ephemeral bounded agents for one session.
- `--allowedTools`, `--disallowedTools`, `--tools`, and `--permission-mode` constrain what the model can do.
- `--mcp-config` plus `--strict-mcp-config` constrains MCP servers for a session.
- `--json-schema` constrains non-interactive structured output.
- `--safe-mode` and `--bare` are troubleshooting and isolation modes.

Prompting alone is not an obedience guarantee. For risky or implementation work, combine prompt constraints with tool restrictions, permission mode, result schema, and owner-side verification.

For Claude Opus 5, use `references/opus-5-profile.md` as the compact model profile. Do not use the large context window as a default; pass a CURATOR-style dossier and load exact references only when the owner needs them.

## Owner Selection

Default owner route:

- OPTIO / `orchestrator`: plan, route, mission prep.
- EXPLORATOR / `researcher`: local or web research, reference search, docs.
- CODER / `coder`: implementation.
- PICTOR / `pictor`: frontend UI implementation, Open Design create/revise work, responsive layouts, animation.
- AEDILIS / `aedilis`: UI/UX architecture, Open Design briefs and visual acceptance, design systems, accessibility review.
- NOMENCLATOR / `nomenclator`: product language, CTA, labels, microcopy.
- TESTER / `tester`: tests, evals, regression proof.
- REVIEWER / `reviewer`: code review and regression risk.
- GUARDIAN / `security`: secrets, dependency, MCP, external-skill, permission, production, wallet/payment/KYC gates.
- CENSOR / `censor`: WAR ROOM, adversarial verification, assumptions.
- SIGNIFER / `git-master`: branches, commits, PRs, safe git.
- CURATOR / `context-optimizer`: skill-surface drift, context load, duplicate skills.

If no route is clear, use OPTIO first.

AEDILIS and PICTOR may invoke `$open-design-producer`. Domain owners such as
LUDIFEX, PRAECO, NOMENCLATOR, GLOSSATOR, MERCATOR, and INDAGATOR supply
constraints; TESTER, REVIEWER, and GUARDIAN provide acceptance gates.

## CLAUDE_ORDER v1

Use `CLAUDE_ORDER v1` whenever Claude Code is asked to execute a bounded implementation slice or when a controller needs strict acceptance criteria.

Controller must provide:

- `Owner`: one Legionary slug or name.
- `Workspace`: exact path.
- `Allowed paths`: exact files/directories Claude may change.
- `Non-goals`: explicit exclusions.
- `Forbidden content patterns`: regex/text patterns that must not appear.
- `Proof commands`: commands to run or explain why unavailable.
- `Order ID`: one safe path component used for the control namespace.
- `Result file`: `<workspace>/.centurion/agents_results/<orderId>/CLAUDE_RESULT.json`.

Hard-stop rules:

- If needed work is outside allowed paths, stop and report `blocked`.
- If non-goals conflict with the task, stop and report `blocked`.
- Do not add dependencies, network calls, scripts, broad discovery, or extra files unless explicitly allowed.
- Read only files needed for the order and proof.
- Never modify secrets, credentials, production deploys, destructive state, wallet/payment/KYC flows, exploit execution, or final risk judgment unless the order explicitly names the target and proof gate.

Required result shape:

```json
{
  "resultVersion": "AGENT_RESULT_JSON_V1",
  "orderId": "<orderId>",
  "executor": "claude",
  "status": "done",
  "summary": "Completed the bounded order.",
  "filesChanged": [{ "path": "relative/product-path", "action": "modified" }],
  "artifacts": [],
  "proof": [{ "command": "npm test", "cwd": "<workspace>", "status": "pass", "exitCode": 0, "summary": "..." }],
  "selfReview": { "performed": true, "findings": [], "fixesApplied": [] },
  "scopeDeviations": [],
  "forbiddenPatternHits": [],
  "remainingRisks": [],
  "questions": [],
  "errors": [],
  "stdoutSummary": "",
  "stderrSummary": ""
}
```

Result typing is part of the contract. Canonical `filesChanged` contains objects and must match product-file changes only; the snapshot and result control files are excluded. For `status=done`, proof must be non-empty, every `proof[].status` must be `"pass"`, `selfReview.performed` must be `true`, and scope/forbidden arrays must be empty.

Final stdout for print-mode orders should contain only:

```text
CLAUDE_RESULT_FILE=.centurion/agents_results/<orderId>/CLAUDE_RESULT.json
STATUS=<done|blocked>
```

Before snapshot or verify, resolve the installed kit root:

```sh
CENTURION_CLAUDE_KIT="${CLAUDE_HOME:-$HOME/.claude}/skills/centurion-legion"
```

For an installation created with a custom `--claude-home`, set `CENTURION_CLAUDE_KIT` to that exact `<claude-home>/skills/centurion-legion` root. The controller must invoke the bundled guard as `node "$CENTURION_CLAUDE_KIT/scripts/claude-order-guard.mjs"`, rerun owner proof, and inspect the diff/artifact directly before accepting.

### Legacy compatibility

The former `CLAUDE_ORDER_V1` result shape is accepted only by an explicit `verify --allow-legacy` invocation. It keeps string `filesChanged` entries, including the result control file, and legacy `proof[].result`/`selfReviewFixed` semantics. Do not emit it for new orders.

## WAR ROOM

For `WAR ROOM`, use three positions:

- Prosecutor: CENSOR/REVIEWER breaks the plan.
- Advocate: CODER/ARCHITECTUS defends feasibility and constraints.
- Judge: OPTIO chooses the smallest safe action and proof gate.

Verdict must list required fixes, owner, handoffs, proof commands, and residual risks.
