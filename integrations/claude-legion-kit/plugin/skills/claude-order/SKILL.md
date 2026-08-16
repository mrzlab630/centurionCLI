---
name: claude-order
description: Use when running or reviewing CLAUDE_ORDER v1 bounded execution with allowed paths, forbidden patterns, structured result JSON, and owner-side proof.
---

# CLAUDE_ORDER v1

This skill defines strict bounded execution for Claude Code.

## Controller Checklist

1. Create a snapshot before delegation:
   `node integrations/claude-legion-kit/scripts/claude-order-guard.mjs snapshot --workspace <dir> --out /tmp/claude-before.json`
2. Send a `CLAUDE_ORDER v1` containing owner, workspace, allowed paths, non-goals, forbidden patterns, proof commands, and `CLAUDE_RESULT.json` requirement.
3. Prefer CLI constraints when using print mode:
   - `--agent <owner-slug>` for one owner.
   - `--permission-mode plan` for planning only.
   - `--permission-mode default` or `acceptEdits` for implementation where prompts should not bypass confirmation.
   - `--allowedTools` and `--disallowedTools` for tool gating.
   - `--strict-mcp-config` with a minimal `--mcp-config` when MCP access is needed.
   - `--json-schema` for pure structured output tasks.
4. Verify after execution:
   `node integrations/claude-legion-kit/scripts/claude-order-guard.mjs verify --workspace <dir> --before /tmp/claude-before.json --allowed <paths> --result CLAUDE_RESULT.json --forbidden <patterns>`
5. Rerun proof and inspect the diff/artifact directly.

## Result Contract

`CLAUDE_RESULT.json` must use this exact shape:

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

`filesChanged`, `proof`, `scopeViolations`, `forbiddenPatternHits`, and `remainingRisks` are arrays. Use `[]` for no findings; never use strings such as `"none"`. `filesChanged` must match the actual changed files, including `CLAUDE_RESULT.json`. For `status=done`, every `proof[].result` must be `"passed"`; use `status=blocked` if proof was not run or did not pass.

## Acceptance Rule

Never accept Claude stdout, narration, or confidence alone. Accept only observed filesystem scope, structured result, proof, and owner review.
