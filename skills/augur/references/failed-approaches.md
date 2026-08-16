# Failed Approaches — AUGUR

> Check this file BEFORE starting analysis. Do not repeat these mistakes.

---

## [2026-03-04] Pool Detection via Known Address Trading = FALSE POSITIVES
**Approach:** If known network addresses (snipers/transit) trade in a Pump.fun pool → classify as network pool (HIGH confidence path).
**Why it failed:** 15K+ known addresses = high probability of random overlap in popular pools. Transit selling tokens ≠ network created the token. Snipers trading ≠ coordination.
**Correct path:** CRITICAL-only detection — require known CREATOR address + CREATE discriminator TX. Removed HIGH/LOW confidence paths entirely.

## [2026-03-03] autoDiscover for ANY known→unknown = Cascading Misclassification
**Approach:** When a known address sends SOL to unknown → auto-classify the unknown based on amount ranges (team_sniper, main_sniper, etc.).
**Why it failed:** Triggered for ALL known types (transit, sniper, creator), not just banks. Transit sends 3 SOL → "team_sniper_funding" → chain of fake snipers/creators. 90-99% misclassification rate.
**Correct path:** autoDiscover restricted to: bank→unknown (full classify) + sniper→unknown (only sniper sub-distributor classify). Added behavioral reclassification (sniper ≥35 SOL → transit, creator ≥10 SOL → transit).

## [2026-03-03] SPL Token Program in CREATOR_PROGRAMS
**Approach:** TokenkegQfeZyigYk... listed in CREATOR_PROGRAMS to detect token creation.
**Why it failed:** SPL Token program appears in nearly ALL transactions (transfers, swaps, everything) → every TX looked like "creator_funding."
**Correct path:** Removed SPL Token from CREATOR_PROGRAMS. Use Pump.fun CREATE discriminator + Metaplex for creator detection.

## [2026-03-10] Confirmed Network Dump (≥2 SOL AND ≥30% drop)
**Approach:** Require BOTH ≥2 SOL drop AND ≥30% drop from peak for network_dump signal (instead of simple ≥2 SOL threshold).
**Why it failed:** Blocked 76% of profitable dumps. Many legitimate dumps are small absolute drops but still signal network exit.
**Correct path:** REVERTED to simple BIG_SELL_SOL ≥ 2.0 threshold. Simplicity wins — network_dump has 90-100% win rate with simple threshold.

## [2026-03-10] Correlation ≠ Causation in Pool Type Analysis
**Approach:** "unknown" pool type has 26% win rate vs pump_dump 43% → filter out unknown pools.
**Why it failed:** "unknown" = unclassified pools, not a real category. Many unknowns become pump_dump after more data. Filtering by classification artifact, not signal.
**Correct path:** Focus on measurable entry signals (poolSol, sec_since_creation, OFI) not post-hoc classifications.

## [2026-03-08] trail_stop at 30% = False Triggers on Organic Drawdown
**Approach:** Trail stop at 30% from peak — exit when price drops 30%.
**Why it failed:** Organic (non-network) drawdowns frequently hit 30%. 10/11 BELOW_ENTRY losses: universal PBE fires EARLIER at better price than trail_stop. Trail_stop was catching noise.
**Correct path:** trail_stop raised to 50% — only catastrophic crashes trigger it. Normal exits handled by universal PBE (any seller, price below entry).
