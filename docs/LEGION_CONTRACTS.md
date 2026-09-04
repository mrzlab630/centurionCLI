# Legion JSON Contracts

CENTURION uses JSON contracts only for bounded delegation points where the controller can validate the executor output mechanically.

These contracts do not replace normal Markdown discussion, WAR ROOM reasoning, research notes, user-facing summaries, or Legionary skill instructions. They are acceptance artifacts for delegated work.

## Contract Boundary

Use structured JSON when all of these are true:

- one controller owns acceptance;
- one executor receives a bounded order;
- allowed paths, non-goals, proof commands, and result file are explicit;
- a guard can validate the result shape, proof status, and scope;
- the output is consumed by another agent or script.

Do not use JSON for open-ended exploration, broad architecture debate, chain-of-thought capture, or regular user conversation.

## Versions

- `AGENT_ORDER_JSON_V1`: canonical controller-to-executor order for bounded work.
- `AGENT_RESULT_JSON_V1`: canonical executor-to-controller result with changed files, proof, self-review, scope violations, forbidden-pattern hits, and remaining risks.
- `LEGION_REVIEW_V1`: reviewer-to-controller verdict for accepting or rejecting an executor result.

Surface-specific legacy protocols remain valid only for explicit compatibility:

- Antigravity and `agy` may opt into `AGY_ORDER_V1` plus `AGY_RESULT.json` for legacy compatibility.
- Claude Code may opt into `CLAUDE_ORDER_V1` plus `CLAUDE_RESULT.json` for legacy compatibility.

For new executor orders, controller-owned result/candidate/receipt/stream/event
and evidence files belong under
`<repo>/.centurion/agents_results/<orderId>/`, derived from the resolved
workspace repository and a fresh safe `orderId`. Explicit product/application
artifacts stay in their declared paths. Existing root files are not relocated;
cleanup is a separate operation.

Pre-execution snapshots for AGY and Claude are separate controller-custody inputs: guards require an absolute path outside the workspace plus a detached digest. A detached digest catches ordinary tampering; it is not independent authentication against a same-UID writer that can rewrite both custody files, so an external controller account or OS boundary is still required for that threat.

The shared validator accepts those legacy result payloads only when a surface guard explicitly opts in with `acceptedOrderVersions`.

## Ownership Rule

The JSON contract does not create a new Legionary owner. The primary owner remains responsible for:

- choosing whether to delegate;
- narrowing allowed files and non-goals;
- defining proof commands;
- inspecting the diff or artifact after execution;
- rejecting partial, unproved, or out-of-scope results.

If another specialty is needed, the owner calls that Legionary as a conditional handoff. Ownership does not become shared.

## Standard Flow

1. Select one primary Legionary owner.
2. If external execution is useful, create a bounded order for the executor.
3. Require a result JSON file from the executor.
4. Run the surface guard or shared validator.
5. Inspect the real diff or artifact.
6. Run owner proof.
7. Accept, reject, or request fixes.

For reviewer handoffs, the reviewer may return `LEGION_REVIEW_V1` with a verdict, reviewed proof, findings, required fixes, and residual risks.

## Validation

Shared contract package:

```bash
cd integrations/legion-contracts
npm run smoke
node ./scripts/legion-contract.mjs validate-order --file /path/to/LEGION_ORDER.json
node ./scripts/legion-contract.mjs validate-result --file /path/to/LEGION_RESULT.json
node ./scripts/legion-contract.mjs validate-review --file /path/to/LEGION_REVIEW.json
```

Legacy result validation examples (compatibility-only; canonical results need no opt-in):

```bash
CONTROL_DIR="$PWD/.centurion/agents_results/<orderId>"
node integrations/legion-contracts/scripts/legion-contract.mjs validate-result \
  --file "$CONTROL_DIR/AGY_RESULT.json" \
  --accept-order-version AGY_ORDER_V1

node integrations/legion-contracts/scripts/legion-contract.mjs validate-result \
  --file "$CONTROL_DIR/CLAUDE_RESULT.json" \
  --accept-order-version CLAUDE_ORDER_V1
```

Surface-specific guards remain the acceptance gates for scope and filesystem proof:

- `integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs`
- `integrations/claude-legion-kit/scripts/claude-order-guard.mjs`

The shared validator owns result shape. Surface guards own workspace snapshots, changed-file policy, forbidden-pattern checks, and executor-specific strictness.
