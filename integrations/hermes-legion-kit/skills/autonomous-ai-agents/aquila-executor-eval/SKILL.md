---
name: aquila-executor-eval
description: Benchmark codex, claude, agy, and Hermes delegate_task on repeatable tasks using isolated workspaces, AGENT_ORDER_JSON_V1, deterministic graders, pass@k, time, scope, and artifact-contract metrics. Use when comparing executor reliability, validating model/tooling upgrades, or proving delegation health.
version: 1.0.0
author: Aquila/CENTURION
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [aquila, eval, benchmark, codex, claude, agy, delegate-task, pass-at-k]
    related_skills: [delegated-cli-executor-orchestration, delegating-code-to-executors, test-driven-development, requesting-code-review]
---

# Aquila Executor Eval

Use this skill to compare or regression-test executor surfaces: codex, claude, agy, and Hermes `delegate_task`. It adapts ECC eval-harness ideas to Aquila's existing order/result contracts.

## Activation

Load this when:
- choosing which executor should own a class of task;
- checking whether a model/tooling update changed executor reliability;
- proving that agy/codex/claude delegation contracts still work;
- investigating repeated missing artifacts, scope drift, or weak proof.

## Eval Principles

- Use real representative tasks, not toy prompts.
- Pin the repo state or use an isolated worktree/scratch copy.
- Use AGENT_ORDER_JSON_V1 for every executor that can accept structured text.
- Require AGENT_RESULT_JSON_V1 or an explicit mappable structured output.
- At least one grader must be deterministic: test, build, grep, JSON schema, or file existence.
- LLM review is secondary evidence, never the only pass/fail signal.

## Task Definition

Keep eval tasks small and reproducible:

```yaml
name: frontend-layout-fix
repo: /abs/path/to/repo
base_ref: HEAD
risk: medium
executor_candidates: [codex, claude, agy]
allowed_paths:
  - src/components/Target.tsx
forbidden_paths:
  - package-lock.json
objective: "Fix mobile overflow in Target without changing API behavior."
proof:
  - command: npm test -- Target
  - command: npm run build
  - command: node scripts/check-no-overflow.mjs
success:
  - result JSON exists and status is done
  - only allowed paths changed
  - all required proof commands pass
  - selfReview performed
```

## Metrics

Record per executor:

| Metric | Meaning |
| --- | --- |
| pass@1 | First attempt produced accepted artifact and proof. |
| pass@3 | At least one of three bounded attempts succeeded. |
| time_seconds | Wall-clock time until accepted or failed. |
| contract_compliance | Valid result JSON, required fields, artifact paths, proof summaries. |
| scope_score | Only allowed paths changed; no forbidden actions. |
| proof_score | Aquila reran proof, not just executor self-report. |
| correction_count | Number of correction orders needed. |
| cost_note | Token/API cost if available; otherwise qualitative cost. |

## Workflow

1. Select 3-5 task types from real work: code fix, UI/prototype, review/debug, docs/content, harness audit.
2. Preflight executor availability with harmless version/readiness checks.
3. Create isolated worktree/scratch workspace per run when file edits are involved.
4. Send the same bounded order shape to each executor, adjusted only for launcher syntax.
5. Verify artifacts yourself: result JSON, diff scope, proof commands, selfReview.
6. Record failures as data. Do not "help" one executor more than another unless the eval is explicitly a recovery eval.
7. Summarize routing implications for future Aquila decisions.

## Acceptance Gate For Executor Health

An executor is healthy for a task class only if:
- it can receive a bounded order;
- it writes the expected artifact or valid stdout result;
- it respects allowed/forbidden paths;
- Aquila can rerun proof successfully;
- repeated failures have a classified cause and a fallback path.

## Output Standard

```yaml
executor_eval:
  task_set: "name/date"
  verdict: "routing recommendation"
  results:
    codex:
      pass_at_1: "0/1"
      pass_at_3: "0/3"
      strengths: []
      weaknesses: []
    claude:
      pass_at_1: "0/1"
      pass_at_3: "0/3"
      strengths: []
      weaknesses: []
    agy:
      pass_at_1: "0/1"
      pass_at_3: "0/3"
      strengths: []
      weaknesses: []
  routing_updates:
    - "Use agy only for bounded UI draft tasks with browser proof."
  evidence:
    - "artifact path or command"
```
