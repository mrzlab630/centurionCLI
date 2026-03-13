# Failed Approaches — CODER

> Check this file BEFORE starting implementation. Do not repeat these mistakes.

---

## [2026-03-07] Fire-and-Forget Async in Event Handlers
**Approach:** `this.onTransfer(event)` called without await in event loop — "fire and forget" pattern.
**Why it failed:** Creates unbounded concurrent async operations. Under burst load (Geyser sending 100+ events/sec), each spawns its own Promise chain. Memory grows without limit → OOM.
**Correct path:** Serial processing queue with bounded capacity (500 max, drop-oldest on overflow). Process events one at a time within the queue.

## [2026-03-07] Unbounded Maps/Arrays as In-Memory Caches
**Approach:** `registeredPools`, `pendingAddresses`, `tokenAccountCache`, `migrationEvents` — Maps/Arrays used without size limits.
**Why it failed:** In long-running PM2 processes (days/weeks), these grow indefinitely. `tokenAccountCache` had no cap. `registeredPools` cleanup timer was commented out (disabled). `migrationEvents` array never truncated.
**Correct path:** ALWAYS cap in-memory collections: `registeredPools` (1000), `pendingAddresses` (10K + TTL 2h), `tokenAccountCache` (5000), `migrationEvents` (100). Re-enable cleanup timers. Use TTL-based eviction.

## [2026-03-07] Silent Error Swallowing: `return []` / `.catch(() => {})`
**Approach:** DB query fails → `return []` or `return 0`. Promise rejection → `.catch(() => {})`.
**Why it failed:** 8 CRITICAL instances of `return []`/`return 0` on DB failure — code proceeds with empty data as if everything is fine. 30+ `.catch(() => {})` across sell/gang predictors — errors invisible, debugging impossible.
**Correct path:** At minimum log the error. For critical paths (trading decisions), throw or return a result type that distinguishes "no data" from "query failed." Never swallow errors silently in financial code.

## [2026-03-07] Zombie Timers from Async Race Conditions
**Approach:** `emitEntrySignal()` sets up setTimeout for exit monitoring. Does not check if exit already happened during the await.
**Why it failed:** `await` in emitEntrySignal can take seconds. During that time, exit signal fires. Timer starts AFTER exit → orphaned setTimeout running on an already-closed position. Ghost positions in memory.
**Correct path:** After every `await` in signal handlers, re-check state flags (`exitSignalSent`). If state changed during await, abort. Also: force-evict stuck positions after MAX_HOLD + 60s as safety net.

## [2026-03-07] Hardcoded Secrets in Source Code
**Approach:** Telegram bot token hardcoded directly in source file.
**Why it failed:** Exposed in git history. Can't rotate without code change + deploy. Different values needed for dev/prod.
**Correct path:** Environment variables (`PHANTOM_TG_TOKEN`, `PHANTOM_TG_CHAT`). Load via `process.env`. Document required env vars in ecosystem.config.js.

## [2026-02-20] DB Transaction Missing in Multi-Step Operations
**Approach:** Wallet creation: 1) create wallet in DB, 2) add to monitoring list, 3) return to user. No transaction wrapping.
**Why it failed:** Step 2 fails → orphan wallet in DB, user gets error but wallet exists. Cache shows stale data. Steps execute in wrong order for user experience.
**Correct path:** Wrap multi-step DB operations in transactions. Add cache invalidation after mutations. Implement orphan recovery for partial failures. Reorder steps for better UX (validate first, create last).
