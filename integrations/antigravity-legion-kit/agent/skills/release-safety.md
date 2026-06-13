---
name: release-safety
description: Pre-release, post-release, rollback, migration, smoke, and backup safety skill for production-like deployments.
---

# Release Safety

Use before deploys, PM2 reloads, production smoke, migration rollout, release tagging, or any change that affects live users/services.

## Pre-Release Checks

- branch and dirty tree
- dependency and lockfile changes
- package manager and canonical scripts
- typecheck/lint/test/build gates
- migration status and backup/restore plan when data changes
- env docs and startup validation
- deploy/restart command and rollback command
- smoke path and owner

## Post-Release Proof

- process owner and ports
- health endpoint
- smoke command or user-visible flow
- logs for new errors
- migration state when data changed
- rollback/recovery note if risk remains

## Rollback Rules

- Do not assume code rollback can undo database changes.
- If rollback is unsafe, provide a forward-fix or restore plan.
- Keep evidence of the version/config before and after rollback.

