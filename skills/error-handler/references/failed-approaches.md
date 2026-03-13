# Failed Approaches — DEBUGGER (Error Handler)

> Check this file BEFORE diagnosing issues. Do not repeat these mistakes.

---

## [2026-03-03] Blaming Load for Node Crash (Misdiagnosis)
**Approach:** Solana validator crashed → initial diagnosis: "ScamNet is putting too much load on the node via Geyser."
**Why it failed:** Geyser is a READ-ONLY observer plugin. It runs AFTER the replay stage. It is physically impossible for Geyser subscriptions to cause bank hash mismatch or state divergence.
**Correct path:** Root cause was validator software bug (AccountNotFound → state divergence). Check `journalctl -u sol` for actual error messages before blaming load. Geyser can NEVER cause consensus failures.

## [2026-03-03] Missing Validator Flags After Upgrade
**Approach:** Upgraded agave-validator from v3.0.14 to v3.1.9. Used same startup flags.
**Why it failed:** v3.1.x REQUIRES `--enable-accounts-disk-index` — was optional in v3.0.x. Validator enters crash loop without it. No clear error message pointing to the flag.
**Correct path:** ALWAYS check release notes for new required flags on major version upgrades. Check `/opt/solana/validator.sh` for flag completeness. Current required flags documented in incident-runbooks.md.

## [2026-03-07] Prisma Schema Mismatch — Non-Nullable Without DB Default
**Approach:** Prisma schema declares field as required (non-nullable), but DB column has no DEFAULT.
**Why it failed:** `last_activity_at` added to Prisma as required DateTime, but ALTER TABLE didn't set DEFAULT NOW(). Every INSERT without explicit value → Prisma crash → 0 addresses discovered.
**Correct path:** ALWAYS check DB defaults match Prisma nullability. If Prisma says required → DB MUST have a DEFAULT. Found 6 CRITICAL mismatches across sniper_transactions, blockchains, dex tables. Rule: `ALTER TABLE ... ADD COLUMN ... DEFAULT value` BEFORE updating Prisma schema.

## [2026-03-07] Diagnosing "No Data" as Feature Bug vs DB Bug
**Approach:** ScamNet stopped discovering addresses → looked at Geyser filters, detection logic, classification code.
**Why it failed:** Real cause was `last_activity_at` column without DEFAULT → every Prisma INSERT crashed. Zero addresses saved. Feature code was fine — DB layer was broken.
**Correct path:** When "no data" is the symptom, FIRST check: 1) Is the DB reachable? 2) Are INSERTs working? 3) Check PM2 error logs for Prisma/DB errors. THEN check feature logic.
