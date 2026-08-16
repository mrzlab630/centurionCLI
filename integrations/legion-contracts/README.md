# Legion Contracts

Shared JSON contracts for bounded CENTURION handoffs between Codex, `agy`, Claude, and future external executors.

## Rule

Use JSON only where a controller can validate the result mechanically. Keep discussion, research notes, WAR ROOM reasoning, and user-facing summaries in Markdown.

## Contracts

- `LEGION_ORDER_V1`: controller-to-executor order for bounded work.
- `LEGION_RESULT_V1`: executor-to-controller result with changed files, proof, self-review, scope violations, and residual risk.
- `LEGION_REVIEW_V1`: reviewer-to-controller acceptance or rejection of an executor result.

Legacy result payloads remain valid when explicitly accepted by a surface guard:

- `AGY_ORDER_V1` result objects in `AGY_RESULT.json`.
- `CLAUDE_ORDER_V1` result objects in `CLAUDE_RESULT.json`.

## Validation

```bash
cd integrations/legion-contracts
npm run smoke
node ./scripts/legion-contract.mjs validate-result --file /path/to/LEGION_RESULT.json
```

Surface-specific guards should import `validateDelegationResult` and keep their own scope, forbidden-pattern, and changed-file checks close to the executor they control.
