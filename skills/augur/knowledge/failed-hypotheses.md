# Failed Hypotheses

> Document what DIDN'T work and WHY. Prevents repeating mistakes.

## FH-01: NET_SELL as Exit Signal (2026-03-05)
**Hypothesis:** First network sell = exit trigger. Sell when network starts selling.
**Result:** FAILED at sec=1 entry. NET_SELL fires while we're at high entry price.
Network dumps INTO our position. We sell at loss.
**Root cause:** We enter AFTER network buys (high price). When network sells, price drops
below our entry. NET_SELL is profitable only if we entered BEFORE network buys.
**Lesson:** Exit signals that work at ideal entry DON'T work at realistic entry.

## FH-02: Entry Filter by Pool SOL (2026-03-05)
**Hypothesis:** Filter pools by pool_sol_after at entry. Skip pools where price already too high.
**Result:** FAILED. All entry filters from 0.5 to 999 SOL tested. ALL unprofitable at sec=1.
**Root cause:** The problem isn't pool selection — it's entry TIMING. At sec=1, ANY pool
is already too expensive because network buys at sec=0 pushed price +36.7%.
**Lesson:** No amount of filtering fixes late entry. Latency is the fundamental constraint.

## FH-03: Time-Based Exit Only (2026-03-05)
**Hypothesis:** Simple time stop (sell after N seconds). No market signals needed.
**Result:** FAILED at sec=1. Best time stop (15s): -3.33% avg, 20% win rate.
**Root cause:** Time stop doesn't account for already-inflated entry price.
**Lesson:** Time-based exit only works when entry is at favorable price.

## FH-04: HIGH Confidence Pool Detection (2026-03-04)
**Hypothesis:** Known network wallets trading in a pool = proof pool belongs to network.
**Result:** FAILED. Massive false positives. 15K+ known wallets = high overlap in popular pools.
Transit selling tokens via router ≠ network created the token.
**Root cause:** Correlation ≠ causation. Known wallets trade in MANY pools, not just network ones.
**Lesson:** Only CRITICAL confidence (known creator → CREATE TX) is reliable. Removed HIGH/LOW paths.

---

*Last updated: 2026-03-05*
