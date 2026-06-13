---
description: Trace user-facing buttons and touchpoints through full state changes to find inconsistent final UI states.
---

# Click Path Audit Workflow

Use when users report broken buttons, confusing flows, inconsistent state, or after refactors touching shared state stores.

1. List every user-facing action in the target screen.
2. For each action, trace trigger -> handler -> state/store/API call -> response -> UI state -> error/retry path.
3. Check whether actions cancel each other, race, leave stale state, or show the wrong final state.
4. Verify keyboard and pointer paths.
5. Use browser proof when feasible.
6. Report each broken path with the exact state transition that fails.

