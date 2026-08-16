---
name: silent-failure-hunter
description: ECC-adapted skill for finding swallowed errors, unsafe fallbacks, missing propagation, and insufficient logging.
---

# Silent Failure Hunter

Use this skill during bug fixes, reviews, production audits, webhook/worker changes, and any task where the system may fail quietly.

## Hunt Targets

- empty `catch` blocks or ignored exceptions
- `.catch(() => null)`, `.catch(() => [])`, `.catch(() => undefined)` without a documented degraded mode
- logs that omit route/job name, actor, entity id, provider, request id, or operation context
- errors rethrown as strings or generic messages that lose stack/cause
- fire-and-forget async work without `.catch`, queue handoff, or lifecycle ownership
- network, DB, queue, file, and browser automation operations without timeout or cancellation where a hang matters
- fallback UI/data that hides real backend failures from the operator

## Output Format

For each finding, report:

- location
- severity
- issue
- impact
- concrete fix
