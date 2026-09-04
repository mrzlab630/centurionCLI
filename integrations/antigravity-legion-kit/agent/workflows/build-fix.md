---
description: Incrementally fix build, type, lint, and test failures with minimal changes.
---

# Build Fix Workflow

1. Read `package.json` and detect the package manager.
2. Prefer the repository's canonical gate (`pnpm check`, `pnpm build`, `pnpm test`, or equivalent) over ad hoc commands.
3. Capture the first failing command and group errors by file/module.
4. Fix dependency-order issues first: imports, types, schemas, generated clients, config.
5. Make the smallest coherent edit, then rerun the failing command.
6. Stop and report if the same error survives three attempts or the fix requires changing architecture/scope.

Report fixed errors, remaining errors, commands run, and any command skipped with reason.
