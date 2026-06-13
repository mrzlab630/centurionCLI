---
name: database-production-review
description: ECC-adapted review skill for Prisma/PostgreSQL migrations, production readiness, data integrity, and runtime risk.
---

# Database Production Review

Use this skill when a task touches database schema, Prisma queries, API contracts, admin routes, workers, delivery/payment/game-economy mutations, deploy scripts, or production-like runtime behavior.

## Review Order

1. Read the repository's local instructions and package scripts.
2. Identify the data boundary: schema, migration, query, DTO, route, worker, webhook, or admin mutation.
3. Check migration safety before application logic: immutability, rollback/recovery, locks, backfill, indexes, generated client.
4. Check data integrity: transactions, idempotency, audit fields, authorization, race conditions, retries.
5. Check production operation: env vars, startup validation, health checks, PM2/Docker/CI/deploy commands, rollback path.
6. Run the narrowest meaningful validation command and then the repo's combined gate when feasible.

## Prisma And PostgreSQL Checks

- `PrismaClient` should be singleton or follow the repo's established client lifecycle.
- Use `select`/DTO mapping on API hot paths and any user-facing response.
- Avoid N+1 query patterns; batch or include/select deliberately.
- Keep transactions short. Do not call external services inside a DB transaction.
- Remember `updateMany`/`deleteMany` return counts, not records.
- `@updatedAt` is not a substitute for explicit audit events on bulk writes.
- Prefer cursor pagination for large tables and feeds.
- Verify indexes on FKs, tenant/user scoping columns, status filters, timestamps, and soft-delete columns.

## Output Contract

Report:

- database or production surfaces touched
- exact risks found, ordered by severity
- commands run and results
- commands not run and why
- recommended follow-up if risk remains

