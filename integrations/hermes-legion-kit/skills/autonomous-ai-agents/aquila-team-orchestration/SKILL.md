---
name: aquila-team-orchestration
description: Aquila Team Lead workflow for routing codex, claude, agy, Hermes delegate_task, and Kanban work with one owner per task, explicit artifacts, merge gates, and evidence-based acceptance. Use when Aquila manages multi-agent delivery, delegates implementation, reviews executor results, or coordinates durable Kanban handoffs.
version: 1.1.0
author: Aquila/CENTURION
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [aquila, team-lead, delegation, kanban, codex, claude, agy, verification]
    related_skills: [delegated-cli-executor-orchestration, delegating-code-to-executors, kanban-orchestrator, requesting-code-review, test-driven-development]
---

# Aquila Team Orchestration

Use this skill when Aquila is managing work across codex, claude, agy, Hermes `delegate_task`, or Hermes Kanban. It adapts the useful ECC team-orchestration pattern to Hermes' native Team Lead model without importing ECC runtime files.

## Activation

Load this when:
- the task needs more than one executor or specialist;
- implementation must be delegated rather than performed by Aquila directly;
- work needs durable state, review gates, or restart-safe handoff;
- outputs from codex, claude, agy, or Kanban workers must be accepted or rejected.

## Core Rule

One task has one accountable owner. If the owner lacks a needed capability, they request or depend on another owner; they do not silently widen scope.

### Scope, attempt, and step gates

The user order and frozen plan are the hard scope ceiling. A new function,
behavior, file, test, test class, refactor, dependency, or plan change requires
explicit direct Boss approval in the current task; executor inference,
reviewer suggestions, and test failures are not approval. Execute one initial
implementation attempt plus at most one finding-mapped correction for the same
objective. A correction changes only the finding-mapped behavior and minimum
proof. After the second product attempt, return `blocked` and wait for a fresh
Boss order/objective; never widen scope to make a new test green.

Before execution, every plan step freezes its acceptance criteria, allowed
paths, expected artifacts, and proof commands. Aquila/controller inspects
changed paths, artifact identity, proof results, and scope deviation after
each step; the next step cannot start until that gate passes. Passing required
proof closes the step and forbids speculative continuation. Tests are allowed
only when mapped to an acceptance criterion, focused regression risk, or a
required risk gate. An out-of-scope failure is reported as `blocked`, not fixed.
Any scope expansion requires unchanged-byte proof for the accepted step and a
fresh order; it cannot be inferred from a failure.

## Executor Routing

| Need | Primary owner | Notes |
| --- | --- | --- |
| Production code, repo edits, tests, refactors | codex | Default implementation executor. Require a namespaced `CODEX_RESULT.json` or equivalent AGENT_RESULT_JSON_V1. |
| Independent review, architecture critique, hard debugging | claude | Use for second-pass verification and complex reasoning. Do not let it self-approve its own implementation. |
| UI alternatives, UX/content drafts, fast frontend prototypes | agy | Narrow scope, exact paths, browser/layout proof for UI, mandatory namespaced `AGY_RESULT.json`. |
| Small isolated parallel reasoning | Hermes `delegate_task` | Good for bounded research/review. Require structured final output mappable to AGENT_RESULT_JSON_V1. |
| Durable multi-step work, restart-safe handoffs, human interjection | Hermes Kanban | Use explicit board/card state and owner. |

## Adaptive Model and Effort Routing

Choose the model and reasoning effort independently for every DAG node. Use
Luna for mechanical/read-only/high-volume low-complexity work, Terra as the
routine bounded implementation default, and Sol for high complexity, material
ambiguity, cross-service/architecture/security, hard debugging, or
long-horizon reasoning. The effort enum is exactly
`none|low|medium|high|xhigh|max`; risk, ambiguity, reversibility, and evidence
need may raise but never lower the applicable floor. No executor self-approves;
Aquila retains final judgment. See the manual, non-installed
`overrides/ADAPTIVE_MODEL_ROUTING_POLICY.md` for the complete invariant set.

## Atomic V0-V3 Routing Cutover

For orders created at or after `2026-08-03T11:00:42Z`, add exactly one compact `AQUILA_ROUTING_JSON_V1:` item to `notesForExecutor`. It records objective and attempt identity, task class, complexity, risk, ambiguity, reversibility, evidence need, executor/model/effort, execution and verification profiles, reviewer, confidence, and reasons. Deterministic pre-delegation routing chooses V3 first, then V2, V1, and V0 only when every trust predicate is true.

| Profile | Terminal reviewer | Rule |
| --- | --- | --- |
| V0 | none | Deterministic proof only; low-risk, local, fully observable work. |
| V1 | `gpt-5.6-sol` | Recoverable work with a meaningful proof gap. |
| V2 | `claude-opus-5` | Medium consequence, shared contract, ambiguity, architecture, or hidden-failure risk. |
| V3 | `claude-opus-5` plus specialist/Boss gate | Security, auth, secrets, money, production, dependencies, public endpoints, or infrastructure. |

The terminal review never delegates a review of itself. After its model gate, Aquila performs only deterministic identity, schema, hash, path, artifact, and proof closure. Record escaped V0 defects and Sol misses in the append-only attempt ledger; the history promotions in the policy elevate future task-class routes without retrospective review of unrelated objectives. See `references/review-routing-ladder-and-cost-control.md` and the installed `agent-contract-runner` skill for the enforceable runner and regressions.

### Executor artifact boundary

Every new order derives one controller namespace from its resolved repository
and fresh safe `orderId`: `<repo>/.centurion/agents_results/<orderId>/`.
Canonical results, raw candidates, launcher receipts, executor stream captures,
gateway events, and gateway evidence stay below that directory. Product or
application artifacts explicitly declared in `expectedArtifacts`,
`filesChanged`, or the result may remain in their declared `allowedPaths`; the
namespace rule must not relocate them. Never reuse an `orderId` or overwrite a
create-only custody path. Legacy root files are left in place; migration and
cleanup require a separate order.

## Board/Card Contract

For any multi-agent or durable task, record these fields in the order, Kanban card, or handoff:

```json
{
  "title": "short task name",
  "owner": "codex|claude|agy|hermes_delegate_task|kanban_profile",
  "state": "ready|running|review|blocked|done",
  "workspace": "absolute repo/worktree path",
  "allowedPaths": ["explicit/path"],
  "forbiddenPaths": ["explicit/path"],
  "acceptanceCriteria": ["testable criterion"],
  "mergeGate": "exact condition for acceptance",
  "expectedArtifacts": ["result JSON and changed files"],
  "proofCommands": ["commands Aquila will rerun"]
}
```

## Orchestration Flow

1. **Recon**: identify project, repo/worktree, dirty state, existing instructions, available executors, and risk level.
2. **Shape**: split work into non-overlapping tasks. Avoid parallel writes to the same files unless one integrator owns the merge.
3. **Assign**: choose one owner per task and issue AGENT_ORDER_JSON_V1 when the surface can accept structured text.
4. **Execute**: let the owner work. Do not replace a failed executor with Aquila self-coding unless Boss gave direct-work override.
5. **Verify**: result JSON exists, expected artifacts exist, diff is scoped, proof commands pass, self-review is present.
6. **Review**: use claude/reviewer path for independent critique when risk is medium or higher.
7. **Integrate**: merge or accept only after the merge gate is satisfied; otherwise send a correction order.
8. **Report**: state accepted work, rejected work, evidence, risks, and next action.

## Kanban vs Delegate Task

Use `delegate_task` for small bounded tasks whose result can fit in one final response. Use Kanban when the task must survive restart, needs human input, has dependencies, or benefits from visible state and run history.

## Acceptance Rules

- Exit code 0 is not proof.
- Prose-only executor output is not completion proof for file work.
- Missing or invalid result JSON means the executor result is not accepted.
- Any scope deviation requires inspection before acceptance.
- If an artifact is missing, inspect stdout/stderr once, then issue a correction order with the exact path or switch executor.

## Failure Modes

- Agent soup: multiple agents working with no owner or merge gate.
- Invisible work: useful output exists only in chat, not an artifact.
- Overlapping writes: parallel executors edit the same files without an integrator.
- Board theater: Kanban cards lack acceptance criteria or proof commands.
- Self-approval: implementation executor also performs final acceptance.

## Output Standard

End each orchestration pass with:
- owner map;
- artifacts accepted/rejected;
- proof rerun by Aquila;
- blockers and next owner;
- whether Boss approval is needed for scope, cost, deploy, or risk.
