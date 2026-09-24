# Legion Contracts

Shared JSON contracts for bounded CENTURION handoffs between Codex, `agy`, Claude, and future external executors.

## Rule

Use JSON only where a controller can validate the result mechanically. Keep discussion, research notes, WAR ROOM reasoning, and user-facing summaries in Markdown.

## Contracts

- `LEGION_ORDER_V1`: controller-to-executor order for bounded work.
- `LEGION_RESULT_V1`: executor-to-controller result with changed files, proof, self-review, scope violations, and residual risk.
- `AGENT_RESULT_JSON_V1`: canonical executor result for new surface handoffs; validate with `validate-agent-result` or `validate-result --canonical`.
- `LEGION_REVIEW_V1`: reviewer-to-controller acceptance or rejection of an executor result.

Legacy result payloads remain valid when explicitly accepted by a surface guard:

- `AGY_ORDER_V1` result objects in `AGY_RESULT.json`.
- `CLAUDE_ORDER_V1` result objects in `CLAUDE_RESULT.json`.

## Validation

`normalize-response` accepts a raw JSON response or one clean lowercase `json`
fence, preserves raw/normalized bytes and SHA-256 evidence, and validates the V1
payload. `--handoff <expected-handoff.json>` pins role/schema/correlation fields.
Canonical validation commands remain strict JSON. Claude and AGY guards use the
same ingress rules and verify controller envelopes before consumption; see
`docs/LEGION_CONTRACTS.md` for the full contract and supported fallback transports.

```bash
cd integrations/legion-contracts
npm run smoke
node ./scripts/legion-contract.mjs validate-result --file /path/to/LEGION_RESULT.json
node ./scripts/legion-contract.mjs validate-agent-result --file /path/to/AGENT_RESULT.json
```

Surface-specific guards use `validateAgentResult` for canonical results and `validateDelegationResult` only for explicit legacy compatibility. They keep their own scope, forbidden-pattern, and changed-file checks close to the executor they control.
