---
name: aquila-self-debug
description: Structured recovery workflow for Aquila when codex, claude, agy, Hermes delegate_task, MCP, browser, Kanban, or model/provider runs fail, loop, drift, or return missing artifacts. Use when executor runs repeat failures, produce prose-only results, hit adapter noise, or lose proof artifacts.
version: 1.0.0
author: Aquila/CENTURION
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [aquila, debugging, executor-failure, recovery, codex, claude, agy, mcp, kanban]
    related_skills: [systematic-debugging, delegated-cli-executor-orchestration, aquila-harness-audit]
---

# Aquila Self Debug

Use this skill when Aquila or a delegated executor is failing repeatedly, looping, drifting, or returning exit 0 with no acceptable artifact. It is a contained recovery protocol, not permission for Aquila to become the coder.

## Activation

Load this when:
- an executor result is missing, invalid, prose-only, or off-scope;
- a CLI reports auth/provider/model noise;
- MCP/browser/Kanban tooling fails or disconnects;
- repeated retries produce the same failure;
- context growth or prompt drift starts damaging execution quality.

## Phase 1: Capture

Before retrying, record the failure precisely:

```markdown
## Failure Capture
- Goal:
- Executor/surface:
- Command/interface:
- Attempt count:
- Expected artifact:
- Actual artifact state:
- Key stdout/stderr/error lines:
- Last successful step:
- Repeated pattern:
- Current cwd/repo/branch:
- Dirty state risk:
```

## Phase 2: Classify

| Pattern | Likely cause | Check |
| --- | --- | --- |
| Exit 0, no file | Contract failure or wrong writable path | `test -f`, `git status --short`, stdout/stderr. |
| Auth/login chatter | Adapter/provider env issue or transient token noise | Resolve binary, env vars, local proxy health, retry policy. |
| Read-only write failure | Sandbox or allowed path mismatch | Launcher flags, cwd, result path under workspace. |
| Repeated same command | Loop/no new evidence | Stop identical retries; run one discriminating check. |
| Browser/Camofox mismatch | Wrong browser surface | Verify actual CDP/browser route; use alternate proof if needed. |
| MCP timeout/disconnect | Server transport/session issue | `hermes mcp list`, logs if available, narrow server/tool. |
| Kanban worker stuck | Unknown assignee, workspace, profile, or protocol violation | `hermes profile list`, `hermes kanban show/tail`. |
| Tests still fail | Wrong hypothesis | Isolate exact failing test and re-read changed code. |

## Phase 3: Recover

Use the smallest safe action that changes the evidence surface:

1. Restate the real objective in one sentence.
2. Verify world state: cwd, repo, branch, files, process, config.
3. Check the expected artifact directly.
4. Inspect stdout/stderr/logs once.
5. Send one correction order with exact output path if the failure is contract-only.
6. Switch executor or proof route after repeated identical failure.
7. Stop and ask Boss only when blocked by missing auth, unavailable tool, destructive risk, or product decision.

Do not silently self-code production changes without direct-work override.

## Bounded Retry Rules

- Transient/provider/model failures: up to 3 bounded attempts with changed evidence or route.
- Contract failure: one execute-now correction order, then switch route if unchanged.
- Deterministic blocker: stop early and report exact blocker.
- Destructive-risk blocker: stop immediately.

## Phase 4: Report

```yaml
self_debug_report:
  goal: "..."
  failure: "..."
  classification: "contract_failure|adapter_noise|deterministic_blocker|transient|scope_drift|tool_failure"
  evidence:
    - "command/path/key line"
  recovery_action: "..."
  result: success|partial|blocked
  next_owner: codex|claude|agy|hermes_delegate_task|boss|aquila
  preventive_update: "skill/order/bundle/config change if warranted"
```

## Anti-Patterns

- Retrying identical commands with no new hypothesis.
- Treating one auth line as final executor death.
- Accepting future-tense prose as completed work.
- Confusing browser proof failure with product failure.
- Expanding scope during recovery.
- Letting the implementation executor self-approve.
