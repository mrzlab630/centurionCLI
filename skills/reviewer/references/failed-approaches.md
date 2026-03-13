# Failed Approaches — REVIEWER

> Check this file BEFORE code review. These are patterns that were MISSED in past reviews.

---

## [2026-03-02] Dead Code Hidden by Guard Clauses
**Approach:** Reviewed bank detection code. Candidate outgoing tracking logic looked correct.
**Why it failed:** The tracking code was placed AFTER `if (!senderKnown || recipientKnown) return;` guard. Candidates are by definition NOT in `knownAll` → `senderKnown` is always false for candidates → guard returns before tracking code runs. Dead code that LOOKS alive.
**Correct path:** When reviewing: trace actual execution flow for EACH code path's target entities. Ask: "For the entity this code targets (candidate, not known), does it survive ALL guards above?" Especially check early-return guards — they may filter out the exact entities the code below was written for.

## [2026-03-07] Silent Error Swallowing Passes Review
**Approach:** Code review approved functions with `.catch(() => {})` and `return []` on error.
**Why it failed:** 30+ instances of silent error swallowing across sell/gang predictors. 8 CRITICAL `return []`/`return 0` on DB failure. These look intentional ("graceful degradation") but actually hide production failures. Code proceeds with empty data as if query returned nothing.
**Correct path:** Flag ALL `.catch(() => {})` as review findings. Distinguish "no results" from "query failed." In financial/trading code, silent error swallowing is ALWAYS a bug. Minimum: log the error. Preferred: return Result type or throw.

## [2026-03-07] Unbounded Collections in Long-Running Processes
**Approach:** Review approved Maps and Arrays without size limits in PM2 processes.
**Why it failed:** Cleanup timer was commented out (disabled). In-memory maps grow indefinitely over days/weeks. Not visible in short-term testing.
**Correct path:** Review checklist item: For EVERY Map/Set/Array in a long-running process, ask: 1) Is there a size cap? 2) Is there eviction/cleanup? 3) Is cleanup actually ENABLED (not commented out)? 4) What happens at cap — drop oldest, reject new, or crash?

## [2026-03-08] Guard Clause Order Hiding Feature Bugs
**Approach:** `pool_below_entry` check was after `if (!isNetwork) return` guard.
**Why it failed:** pool_below_entry should fire for ANY seller (organic or network). But guard returned early for non-network pools → organic price dumps were invisible. Feature existed in code but never executed for the most important case.
**Correct path:** Review each guard clause's position relative to features below it. Ask: "Does this guard accidentally block a feature that should run regardless?" Map feature requirements (who should trigger it?) against guard conditions (who is filtered out?).
