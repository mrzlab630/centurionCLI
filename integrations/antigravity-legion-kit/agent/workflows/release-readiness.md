---
description: Verify a project is ready to release or restart with tests, migrations, env docs, deploy path, rollback, and smoke proof.
---

# Release Readiness Workflow

1. Check git state and recent changes.
2. Identify changed surfaces: frontend, API, DB, worker, provider, runtime, docs, agent config.
3. Run canonical quality gates and focused checks for changed surfaces.
4. Verify migration status and backup/restore plan when data changes.
5. Verify env docs and startup validation for new config.
6. Verify deploy/restart command and rollback path.
7. Run smoke/browser/health proof when user-visible or service behavior changed.
8. Return `ship`, `ship with caveats`, or `block` with evidence.

