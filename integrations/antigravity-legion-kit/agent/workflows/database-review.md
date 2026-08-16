---
description: Review Prisma/PostgreSQL schema, migrations, queries, indexes, and API DTO boundaries.
---

# Database Review Workflow

1. Identify changed schema, migration, query, API route, worker, or admin mutation.
2. Check migration safety: immutable migrations, no unsafe locks, separate backfills, recovery plan.
3. Check Prisma/client behavior: transactions, `select`, DTO mapping, bulk write semantics, N+1, generated client.
4. Check PostgreSQL behavior: indexes, constraints, FK indexing, pagination, status/time filters, soft-delete filters.
5. Run repo-specific validation: migration status, Prisma generate/validate, typecheck/tests.
6. Report findings first, then commands and residual risk.
