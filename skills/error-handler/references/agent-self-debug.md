# Agent Self-Debug

Use this reference when an agent, CLI worker, MCP call, or delegated model fails
repeatedly before reaching the actual user task. The goal is to stop blind retry
loops and produce a bounded, inspectable recovery path.

## Four-Phase Drill

### 1. Failure Capture

Record the smallest exact failing unit:

- command, prompt, tool call, or contract file path;
- current working directory and resolved executable path;
- exit code, stderr key line, stack frame, or serialized error object;
- whether the failure happened before, during, or after task execution.

Do not paraphrase away the error string. Preserve enough evidence for another
Legionary to reproduce the same failure.

### 2. Root-Cause Diagnosis

Classify the failure before changing anything:

| Class | Typical Evidence | Next Owner |
| --- | --- | --- |
| Bad instruction or oversized prompt | model ignores scope, context overflow, malformed order | OPTIO / CURATOR |
| Contract mismatch | missing JSON field, wrong version, invalid result artifact | TESTER / REVIEWER |
| Runtime/tool failure | missing binary, auth, env, timeout, process crash | DEBUGGER / PONTIFEX |
| Code defect | reproducible failing test or stack trace in project code | CODER after root cause |
| Security or permission issue | secret exposure, broad write, unsafe install | GUARDIAN |

### 3. Contained Recovery

Retry only after changing one controlled variable:

- shorten or restructure the order;
- validate JSON before execution;
- pin cwd, executable path, and environment variables;
- run a dry-run or smoke command before the full task;
- isolate the failing tool behind a smaller reproduction.

If the same failure repeats twice after controlled changes, stop retrying and
escalate with evidence instead of burning more context.

### 4. Introspection Report

Return a compact report to the controller:

```yaml
agent_self_debug:
  failure: "exact error or key line"
  phase: "before_task | during_task | after_task"
  diagnosis: "classified root cause"
  recovery_attempted:
    - "one changed variable"
  proof:
    - command: "node scripts/smoke.mjs"
      result: "passed | failed"
  next_owner: "tester | reviewer | coder | guardian | pontifex | optio"
  remaining_risks: []
```

## Reject Conditions

- Repeating the same command or prompt without changing a variable.
- Treating self-debug as proof that the requested feature works.
- Hiding the original error string behind a vague summary.
- Editing project code before root cause is isolated.
- Expanding DEBUGGER into implementation, review, security, or testing ownership.
