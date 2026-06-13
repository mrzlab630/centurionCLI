---
description: ECC-adapted database, production-readiness, browser-QA, and silent-failure rules for JS projects.
---

# Database, Production, And Browser Proof Rules

These rules adapt the useful ECC skills for React/Vite/TypeScript projects under `/home/mrz/projects/js`.

## Database And Migrations

- Treat every schema change as a migration. Never manually patch production-like databases as a substitute for a migration.
- Do not edit a migration after it has been deployed or shared. Fix forward with a new migration.
- Keep schema migrations and data backfills separate unless the repository already has a proven combined pattern.
- For PostgreSQL, avoid blocking operations on large tables. Prefer concurrent indexes where supported and staged expand-contract changes for renames/removals.
- For Prisma, run the repository's migration status/generate commands after schema changes. Do not use `prisma migrate reset` outside disposable local databases.
- Map database records to explicit API DTOs before returning them. Do not expose raw ORM entities or internal fields.
- Add or verify indexes for foreign keys and columns used in `WHERE`, `JOIN`, `ORDER BY`, RLS policies, pagination, and hot admin filters.

## Production Readiness

- Before claiming a production path is ready, inspect scripts, CI/deploy docs, environment docs, migrations, auth boundaries, health checks, and rollback path.
- State-changing routes must have server-side auth, authorization, validation, idempotency where relevant, and useful audit/log context.
- Webhooks, payment-like flows, delivery-like flows, and game-economy flows must tolerate retries, duplicate delivery, and out-of-order events.
- Required env vars should be documented and validated at startup. Client bundles must never contain service secrets.
- For PM2 or long-running services, verify process ownership, ports, health endpoint, and logs before and after restart assumptions.

## Silent Failure Discipline

- Do not swallow errors with empty `catch`, `.catch(() => null)`, `.catch(() => [])`, or generic fallback values without context.
- Preserve stack traces and attach enough context for later debugging: operation, identifiers, route/job name, actor where applicable.
- Network, database, filesystem, queue, and webhook operations need explicit timeout/retry/rollback behavior proportional to risk.
- If graceful fallback is required, record the degraded mode and ensure downstream code can distinguish it from real empty data.

## Browser And UI Proof

- For browser-visible changes, verify the actual route or component state when feasible: desktop, mobile width around 320-390px, keyboard focus, loading, empty, error, and disabled states.
- Use Playwright or an existing smoke/e2e command for routing, auth, layout, Mini App shell, forms, and flows that unit tests cannot prove.
- UI fixes are not complete until text fits containers, controls have stable dimensions, and interactive states do not shift layout unexpectedly.
- Prefer evidence from the server-owned read model for visible state bugs before blaming local React state.

