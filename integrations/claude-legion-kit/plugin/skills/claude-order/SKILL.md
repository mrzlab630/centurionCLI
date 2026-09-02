---
name: claude-order
description: Use when running or reviewing CLAUDE_ORDER v1 bounded execution with allowed paths, forbidden patterns, structured result JSON, and owner-side proof.
---

# CLAUDE_ORDER v1

This skill defines strict bounded execution for Claude Code.

Resolve the bundled guard from the installed skill root before using the checklist:

```sh
CENTURION_CLAUDE_KIT="${CLAUDE_HOME:-$HOME/.claude}/skills/centurion-legion"
```

For an installation created with a custom `--claude-home`, set `CENTURION_CLAUDE_KIT` to that exact `<claude-home>/skills/centurion-legion` root.

## Controller Checklist

1. Choose a safe single-component `<orderId>`, set an external snapshot path, and create the control snapshot:
   `CLAUDE_SNAPSHOT="/tmp/centurion-claude-snapshots/<orderId>/CLAUDE_SNAPSHOT.json"; node "$CENTURION_CLAUDE_KIT/scripts/claude-order-guard.mjs" snapshot --workspace <dir> --order-id <orderId> --out "$CLAUDE_SNAPSHOT"`
2. Send a `CLAUDE_ORDER v1` containing owner, workspace, order ID, allowed paths, non-goals, forbidden patterns, proof commands, and the namespaced result requirement.
3. Prefer CLI constraints when using print mode:
   - `--agent <owner-slug>` for one owner.
   - `--permission-mode plan` for planning only.
   - `--permission-mode default` or `acceptEdits` for implementation where prompts should not bypass confirmation.
   - `--allowedTools` and `--disallowedTools` for tool gating.
   - `--strict-mcp-config` with a minimal `--mcp-config` when MCP access is needed.
   - `--json-schema` for pure structured output tasks.
4. Verify after execution, binding the external snapshot and namespaced result:
   `node "$CENTURION_CLAUDE_KIT/scripts/claude-order-guard.mjs" verify --workspace <dir> --order-id <orderId> --before "$CLAUDE_SNAPSHOT" --allowed <paths> --forbidden <patterns> --result <dir>/.centurion/agents_results/<orderId>/CLAUDE_RESULT.json`
5. Rerun proof and inspect the diff/artifact directly.

## Result Contract

`<workspace>/.centurion/agents_results/<orderId>/CLAUDE_RESULT.json` must use canonical `AGENT_RESULT_JSON_V1`:

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

Canonical `filesChanged` entries are objects and reconcile only product-file changes; snapshot and result control artifacts are excluded. For `status=done`, proof must be non-empty, every `proof[].status` must be `"pass"`, `selfReview.performed` must be `true`, and scope/forbidden arrays must be empty. Use `status=blocked` or `failed` if proof was not run or did not pass.

For explicit compatibility checks only, add `--allow-legacy` to verify. That mode accepts the former `CLAUDE_ORDER_V1` shape; canonical mode never accepts legacy or hybrid payloads.

## Acceptance Rule

Never accept Claude stdout, narration, or confidence alone. Accept only observed filesystem scope, structured result, proof, and owner review.
