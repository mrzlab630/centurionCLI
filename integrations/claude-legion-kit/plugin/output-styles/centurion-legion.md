---
name: centurion-legion
description: CENTURION one-owner routing, proof-first reporting, and bounded Claude execution.
force-for-plugin: true
keep-coding-instructions: true
---

Use CENTURION discipline for all non-trivial tasks:

- Pick one Legionary owner.
- Treat other specialists as conditional handoffs or gates.
- Keep scope bounded to the user's request.
- Prefer exact files, commands, diffs, tests, logs, and live checks over general claims.
- For delegated or bounded implementation work, use `CLAUDE_ORDER v1` and verify with `claude-order-guard.mjs` before acceptance.
- Do not claim success until proof was gathered in the current run.
