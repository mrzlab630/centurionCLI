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

- `LEGION_ORDER_V1`: neutral controller-to-executor order for bounded work.
- `LEGION_RESULT_V1`: neutral executor-to-controller result with changed files, proof, self-review, scope violations, forbidden-pattern hits, and remaining risks.
- `LEGION_REVIEW_V1`: reviewer-to-controller verdict for accepting or rejecting an executor result.

Surface-specific protocols remain valid where they already exist:

- Antigravity and `agy` keep using `AGY_ORDER_V1` plus `AGY_RESULT.json`.
- Claude Code keeps using `CLAUDE_ORDER_V1` plus `CLAUDE_RESULT.json`.

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

Legacy result validation examples:

```bash
node integrations/legion-contracts/scripts/legion-contract.mjs validate-result \
  --file /path/to/AGY_RESULT.json \
  --accept-order-version AGY_ORDER_V1

node integrations/legion-contracts/scripts/legion-contract.mjs validate-result \
  --file /path/to/CLAUDE_RESULT.json \
  --accept-order-version CLAUDE_ORDER_V1
```

Surface-specific guards remain the acceptance gates for scope and filesystem proof:

- `integrations/antigravity-legion-kit/scripts/agy-order-guard.mjs`
- `integrations/claude-legion-kit/scripts/claude-order-guard.mjs`

The shared validator owns result shape. Surface guards own workspace snapshots, changed-file policy, forbidden-pattern checks, and executor-specific strictness.
