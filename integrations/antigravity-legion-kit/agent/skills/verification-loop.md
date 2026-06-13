---
name: verification-loop
description: Same-session validation loop for Antigravity code changes.
---

# Verification Loop

## Steps

1. Identify the changed surface: frontend, API, database, worker, runtime, docs.
2. Choose the narrowest meaningful checks first.
3. Run the repository's canonical scripts.
4. If a check fails, fix the root cause or report the blocker. Do not bury failures in the summary.
5. For live/runtime work, verify process owner, port, health endpoint, and logs.

## Output Template

```text
Validation:
- command: result
- command: result

Not run:
- command: reason
```

