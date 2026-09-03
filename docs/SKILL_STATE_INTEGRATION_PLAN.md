# SKILL.state Integration Plan

## Rationale

`SKILL.state` is introduced as a narrow operational read model for later
separate-project testing. Existing AGENT_ORDER/RESULT contracts, loop state,
result-gateway custody, evidence, transcripts, and Git remain authoritative.
The first slice is deliberately default-off, read-only, bounded, strict, and
provenance-aware so it can be evaluated without changing runner behavior.

## Architecture

`execution_state.py` reads an order and optional result/evidence-reference
index, derives a compact `AQUILA_EXECUTION_STATE_V1` object, validates it, and
writes only the operator-selected output path. Scope is the tuple
`project/objective/workItemId/orderId`; revisions bind order/result digests and,
when present, the parent artifact digest plus monotonically increasing sequence.
Raw payloads are never copied. Unknown fields, duplicate keys, non-finite
numbers, mismatched scope, stale parents, invalid transitions, secret-like
keys, and oversized state fail closed.

## Anti-Degradation Gates

- Existing contract and loop regressions remain unchanged and must pass.
- The projection is never imported or called by the runner or installer.
- Every state has exact source digests and an explicit read-only provenance mode.
- State is rejected on ambiguity, cross-scope references, stale concurrency
  metadata, unknown keys, or size overflow.
- Shadow/canary output cannot execute actions or become canonical proof.

## Rollback and Metrics

Rollback is deletion of the opt-in skill/artifact from the feature branch; no
live service or runner state is mutated. Track projection success/rejection
counts, rejection reason, serialized bytes, source count, evidence count, and
parent-sequence conflicts. Do not persist raw input or secret-like values in
metrics.

## Five Rollout Stages

1. **Local/live installation:** package the skill in a disposable Hermes-home
   install smoke and verify the default-off surface; do not modify the live
   Hermes home in this slice.
2. **Boss testing on a separate project:** invoke projection and validation on
   an isolated project with representative order/result/evidence fixtures.
3. **Analysis of returned evidence:** compare state digests, scope, transitions,
   rejection reasons, size, and provenance against the authoritative artifacts.
4. **One finding-mapped correction if needed:** make at most one narrowly scoped
   correction tied to a concrete finding, then rerun the same regression proof.
5. **Git integration:** review diff and proof, then let the owning controller
   decide commit/merge/push in a separately authorized operation.

## Current Slice Exit Criteria

The module, schema, skill, smoke coverage, and deterministic regression pass in
the feature worktree. No installation, live target, dependency, network,
service, contract, loop, or Git history mutation is part of this slice.
