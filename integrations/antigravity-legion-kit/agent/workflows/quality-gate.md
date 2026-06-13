---
description: Run the standard JavaScript/TypeScript project quality gate.
---

# Quality Gate Workflow

Detect package manager and scripts from `package.json`, then run the strongest available equivalent of:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

If the repo exposes a combined command such as `pnpm check`, prefer that after inspecting what it runs.

For UI-visible changes, add the relevant browser/e2e/smoke command. For runtime changes, verify process ownership and health endpoints.

If `AUXILIUM AGY` contributed to the change, add this acceptance gate:

- confirm `agy` reported self-review findings, fixes applied, rerun proof, and `SELF_REVIEW_FIXED=<yes/no>`
- inspect the diff or artifact directly instead of trusting the `agy` summary
- rerun the strongest local proof command before reporting completion
