# Failed Approaches — PONTIFEX (DevOps/DB)

> Check this file BEFORE infrastructure changes. Do not repeat these mistakes.

---

## [2026-03-03] Validator Upgrade Without Flag Audit
**Approach:** Upgraded Solana validator v3.0.14 → v3.1.9 with identical startup script.
**Why it failed:** v3.1.x introduced REQUIRED flag `--enable-accounts-disk-index` (was optional before). No release note check. Validator crash-looped with unclear error.
**Correct path:** Before ANY validator upgrade: 1) Read release notes for breaking changes, 2) Diff required flags between versions, 3) Test with `--help` for new required args, 4) Keep rollback snapshot.

## [2026-03-07] ALTER TABLE Without DEFAULT on Required Columns
**Approach:** `ALTER TABLE bot_network.addresses ADD COLUMN last_activity_at TIMESTAMP NOT NULL;` — no DEFAULT.
**Why it failed:** All existing rows need a value. New INSERTs without explicit value fail. Prisma schema says required → every INSERT crashes. Cascade: 0 new addresses discovered.
**Correct path:** ALWAYS: `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT NOW()`. For existing data: add with DEFAULT first, then optionally remove DEFAULT if application always provides value. Test INSERT after migration.

## [2026-03-07] Prisma Schema ↔ DB Schema Mismatch (6 Critical Fields)
**Approach:** Updated Prisma schema to mark fields as required without verifying DB has matching DEFAULT.
**Why it failed:** 6 fields across sniper_transactions, blockchains, dex tables: Prisma says non-nullable, DB column is nullable with no default. Works until an INSERT omits the field → crash.
**Correct path:** Audit protocol: `SELECT column_name, is_nullable, column_default FROM information_schema.columns WHERE table_name = '...'` — compare with Prisma schema. Every non-nullable Prisma field MUST have either: DB NOT NULL + DEFAULT, or application ALWAYS provides value.

## [2026-03-03] Glob Pattern Missing Subdirectories
**Approach:** SolCommander cleanup used `glob("tmp-snapshot-*.tar.*")` to find snapshot files.
**Why it failed:** Snapshot files were in `remote/` subdirectory, not in root. Pattern only matched root-level files.
**Correct path:** Use recursive glob: `glob("**/tmp-snapshot-*.tar.*")` to search all subdirectories. Always consider that files may be in nested directories.

## [2026-02-20] Multi-Step DB Operations Without Transactions
**Approach:** Wallet creation: create record → add to monitoring → notify user. Each step is a separate query.
**Why it failed:** Step 2 fails → orphan record in DB. User sees error but wallet exists. Cache invalidation missed → stale data shown on retry.
**Correct path:** Wrap in DB transaction. Add cache invalidation AFTER successful commit. Implement orphan recovery (periodic cleanup of incomplete records). Order steps: validate → create → confirm.
