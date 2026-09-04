---
name: aquila-execution-state
description: Project bounded read-only Aquila execution state from contract and evidence references. Use when an operator explicitly requests an AQUILA_EXECUTION_STATE_V1 shadow or canary projection.
version: 0.1.0
author: Aquila
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [aquila, execution-state, provenance, shadow, canary]
    related_skills: [agent-contract-runner, aquila-team-orchestration]
---

# Aquila Execution State

This skill defines an opt-in operational projection. It does not create a new
source of truth and does not alter `AGENT_ORDER_JSON_V1`, `AGENT_RESULT_JSON_V1`,
`AQUILA_LOOP_V1`, result-gateway custody, transcripts, or event history.

## Dual-Plane Boundary

- The **contract plane** remains authoritative: order, result, loop state,
  receipts, events, transcripts, Git, and their existing validators own action
  and proof custody.
- The **state plane** is a compact, derived `AQUILA_EXECUTION_STATE_V1` artifact.
  It carries scope identity, phase/status, revision hashes, and exact evidence
  references only. It never contains raw reasoning, transcript, stdout/stderr,
  diffs, screenshots, credentials, or proposed action payloads.
- `execution_state.py project` is read-only with respect to all inputs. The
  command only writes its explicitly requested output artifact; it never calls
  an executor, dispatches a loop, retries, or applies state.

The serialized provenance mode is exactly `read-only-derived` for ordinary
projections. A controller may explicitly pass `--legacy-terminal-compat` for
one implicit historical terminal result; that snapshot is mapped to `verify`,
carries `read-only-derived-legacy-terminal`, and cannot use a parent state or
authorize actions. Explicit lifecycle metadata remains strict.

Canonical result summaries are retained through 512 UTF-8 bytes. A larger
summary is omitted from the compact state and represented only as
`execution.summaryOmitted: {reason: result-summary-over-bound, sourceBytes}`;
the canonical result and its exact `revision.resultSha256` remain authoritative.

## Default-Off Shadow/Canary Policy

This capability is default-off. No runner or installer path invokes this projection. An operator must explicitly
run the CLI. Shadow output is observational and may be discarded. Canary use is
permitted only after separate-project Boss testing, evidence analysis, and a
finding-mapped correction; canonical contracts remain the acceptance gate.

## Ownership and Limits

Aquila owns whether a projection is requested and whether it is accepted. The
contract runner owns order/result validation and loop semantics. The projection
enforces strict JSON, unknown-key rejection, scope identity, parent sequence and
hash binding, finite bounded values, transition rules, evidence-count limits,
secret-like key rejection, explicit legacy terminal preconditions, and a 16 KiB
serialized-state limit.

## Stop Conditions

Stop and report blocked when scope or provenance cannot be established, a parent
revision/hash is stale, phase/status transition is invalid, input is malformed,
an unknown field or secret-like value is encountered, state exceeds its bound,
or any request would require changing runner behavior, installing dependencies,
network access, live mutation, credentials, or another worktree.
