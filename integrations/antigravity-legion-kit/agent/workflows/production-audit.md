---
description: Run an ECC-adapted production readiness audit from local evidence.
---

# Production Audit Workflow

Use before deploy, after risky merges, or when the user asks what could break in production.

## Evidence

Run or inspect:

```bash
git status --short --branch
git log --oneline --decorate -20
```

Then inspect scripts, CI/deploy docs, Docker/PM2 configs, env examples, migrations, API routes, workers, webhooks, auth/admin boundaries, health checks, logs, and rollback notes.

## Risk Lenses

- auth and authorization
- secrets and client bundle exposure
- database migrations and backfills
- idempotency for writes, jobs, webhooks, delivery, payments, and game economy
- observability, health checks, and operator recovery path
- browser-critical user flows on desktop and mobile

## Output

Return a short ship/block recommendation, top risks by severity, proof collected, and exact next fixes.

