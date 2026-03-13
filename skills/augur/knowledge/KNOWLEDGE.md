# AUGUR Knowledge Base

> Auto-updated by AUGUR. Each entry includes date, sample size, confidence.

## Status
- **Data volume:** 1,345 pools, 110,301 trades, 34,953 addresses, 240 phantom trades
- **Milestone:** 1,345 pools — ALL tiers unlocked including XGBoost, HDBSCAN, Survival Forests
- **Next milestone:** 2,000 pools → robust cross-validation + deep learning
- **Last analysis:** 2026-03-11
- **Knowledge version:** 3.2
- **Current system:** poolSol≥8 + simple network_dump (≥2 SOL, NO confirm%) + trail_stop 50% + universal PBE + RT behavioral cross-pool
- **Active period:** F_FILTER (id>221), previous: E_NEW (158-221), D_TRAIL30 (125-157)
- **⚠️ PENDING FIX:** sec=1 entry block NOT yet implemented

---

## Confirmed Patterns (p<0.05 or observed in 5+ pools)

### P-01: Network Buys in CREATE Bundle (2026-03-04, N=46, HIGH confidence)
Network snipers buy tokens in the SAME Jito bundle as the CREATE TX.
All network buys land at seconds_since_creation=0 (same slot).
Evidence: 100% of network buys in 46 analyzed pools have sec=0.
Implication: We CANNOT enter before network buys. Must enter AFTER them in sec=0.

### P-02: Entry Position Determines Profit (2026-03-05, N=46, HIGH confidence)
Profit depends on WHERE within sec=0 you enter:
| Position in sec=0 | Win Rate | Avg Profit |
|---|---|---|
| 0% (first) | 38% | -1.36% |
| 25% | 16% | -11.21% |
| 50% | 48% | +1.13% |
| 75% | 84% | +13.48% |
| 100% (last/network) | 78% | +20.06% |
Breakeven: ~50% position. Profitable: 75%+ position.

### P-03: Entry at sec=1+ Results (REVISED 2026-03-05, N=93, MEDIUM confidence)
**REVISION**: Prior finding (N=46) said sec=1+ is UNPROFITABLE (20% win).
Updated N=93 data shows different picture (using peak as ideal exit):
- sec=0: 89% win, +42.5% avg, +7.3% median
- sec=1: 69% win, +38.9% avg, +5.3% median
- sec=2: 67% win, +35.7% avg, +9.2% median
- sec=3: 81% win, +14.4% avg, +11.6% median
**CAVEAT**: These are theoretical max (exit at peak). Real exit won't be at peak.
Prior analysis used realistic exit strategies (time-stop, take-profit) → much worse.
**Conclusion**: sec=0 is still best. sec=1+ CAN be profitable for organic hits but risky.

### P-04: Network Sells at 24-70% of Peak (2026-03-04, N=46, MEDIUM confidence)
Network doesn't sell at peak. Exits at 24-70% of maximum pool SOL.

### P-05: HIT Pools Get Organic Buy at sec=0 (2026-03-04, N=93, HIGH confidence)
Confirmed on N=93: pump_dump pools have median first organic buy at sec=0.
flash_rug pools: 0.0 avg organic buyers (100% network-only).
unknown pools: median first organic buy also at sec=0.

### P-06: First Sell Delay Correlates with Pool Type (REVISED 2026-03-05, N=93, HIGH)
| Type | Median first_sell_delay |
|---|---|
| pump_dump | 16s |
| unknown | 2.5s |
| flash_rug | 104s (but no buyers → irrelevant) |
| slow_rug | 126s |
**REVISION**: Spearman correlation with peak_sol is rho=-0.238 (NEGATIVE, p=0.021).
Longer delay ≠ higher peak. This contradicts prior hypothesis.

### P-07: Bank Pulse Pattern (2026-03-03, N=1 bank 7A77, MEDIUM confidence)
Active bank operates in cycles: BURST (3-5 min) → PAUSE (10-35 min) → DRAIN → RESUME.
Snipers funded at ~10 SOL each, ~5 per burst, ~2s interval.

### P-08: Organic Hit Pattern (NEW 2026-03-05, N=4, MEDIUM confidence)
4 pools identified with >50 traders, >10 SOL peak, >90% organic ratio:
| Pool | Traders | Peak SOL | TTP | Organic% |
|---|---|---|---|---|
| 8iCYtEiRP3f4 | 593 | 70.5 | 164s | 98% |
| GRf3Dwo5tnoN | 184 | 37.9 | 2998s | 99% |
| 5aj3Etouv6Wh | 87 | 12.4 | 216s | 99% |
| 8umwPHPAUVcp | 60 | 13.1 | 43s | 97% |
These are "jackpot" pools — network creates token, it goes viral organically.
Entry profitable even at sec=1-2 for these pools.

### P-09: Unique Traders Is #1 Peak Predictor (NEW 2026-03-05, N=93, HIGH)
Spearman correlations with peak_sol:
| Feature | rho | p-value |
|---|---|---|
| unique_traders | **0.888** | <0.0001 |
| network_sell_sol | 0.693 | <0.0001 |
| network_buy_sol | 0.669 | <0.0001 |
| initial_sol | -0.340 | 0.0009 |
| time_to_peak | 0.220 | 0.034 |
| first_sell_delay | -0.238 | 0.021 |
unique_traders is the single strongest predictor (rho=0.888).

### P-10: Entropy Separates Pool Types (NEW 2026-03-05, N=93, HIGH)
Shannon entropy of trade amounts (log-binned):
| Type | Mean entropy | Std |
|---|---|---|
| pump_dump | 2.26 | 0.38 |
| unknown | 1.72 | 0.50 |
| slow_rug | 1.55 | 0.48 |
| wash_trading | 0.85 | 0.60 |
| flash_rug | **0.19** | 0.41 |
Entropy < 0.5 → almost certainly flash_rug/wash (pure bot).
Entropy > 2.0 → pump_dump with organic participation.
Network entropy always < organic entropy (bots use fixed sizes).

### P-11: Benford Deviation Confirms Bot Activity (NEW 2026-03-05, N=93, HIGH)
Chi-squared test on first digit of buy amounts (SOL):
| Type | N buys | Chi2 | p-value | Verdict |
|---|---|---|---|---|
| pump_dump | 2288 | 1818 | <0.0001 | MASSIVE deviation |
| unknown | 321 | 43.5 | <0.0001 | Significant |
| slow_rug | 40 | 15.0 | 0.058 | Compliant |
Digit 9 anomaly: 22.2% actual vs 4.6% expected in pump_dump.
Main offenders: 0.098-0.099 SOL (≈0.1 target) and 0.978-0.988 SOL (≈1.0 target).
**Surprise**: organic buys also deviate (chi2=1618) — Telegram bot users use round defaults.

### P-12: OFI Trajectory (NEW 2026-03-05, N=93, MEDIUM confidence)
pump_dump OFI: starts +0.4 at sec=0, drops to ~-0.2 by sec=10, oscillates ±0.5.
unknown OFI: starts +0.2, drops below zero faster, stays negative after ~10s.
OFI crossing zero = sell pressure building.

### P-13: Network Dump Is Reactive, Not Timed (NEW 2026-03-05, N=93, HIGH)
Network does NOT use a fixed timer. First sell timing: 1s–1155s (median 16s for pump_dump).
Network waits for organic buying peak: organic buy_sol spikes 13x in [-5,0] window before dump.
**Decision trigger**: pool_sol growth ratio 2–5x over network_buy_sol (avg 4.65x pump_dump).

### P-14: Two-Phase Dump Pattern (NEW 2026-03-05, N=91, HIGH)
- 68% of pools: first sell IS the main dump (no scout phase).
- 32% of pools: scout sells (0.2–0.6 SOL sweeper) precede main dump by 1–4 seconds.
- Main dump: single sell ~3.20 SOL avg (network_bot address), drops pool 30–50%.
- 92% of network sells are SMALL (<2 SOL, sweeper noise), only 8% are kill shots (≥2 SOL).

### P-15: Exit Strategy Backtest (NEW 2026-03-05, N=33 phantom-eligible, HIGH)
Entry: 3+ organic buyers within 5s. Compared exit strategies:
| Strategy | Win Rate | Avg Profit |
|---|---|---|
| Exit on net sell ≥2 SOL | **66.7%** | **+19.19%** |
| 20% trailing stop | 33.3% | -4.44% |
| Time-stop 15s | ~30% | ~-5% |
Exit on big network sell wins decisively. Small sweeper sells are noise.

### P-16: Post-Dump Drain Speed (NEW 2026-03-05, N=31, HIGH)
After first network sell, pool SOL drops to 50% within median **12 seconds**.
Range: 1s–1105s. Avg drain delay: 81s (skewed by organic hits that recover).

---

## Baselines (for Relative Strength comparison)

### Pool Metrics Baseline (N=93, 2026-03-05)
| Metric | Mean | Std | Median | Min | Max |
|---|---|---|---|---|---|
| unique_traders | 18.4 | 64.4 | 6 | 1 | 593 |
| peak_sol | 5.20 | 8.94 | 2.82 | 0.003 | 70.45 |
| time_to_peak_s | 244.5 | 1578.8 | 4 | 0 | 14,952 |
| first_sell_delay_s | 95.3 | 225.8 | 5 | 0 | - |
| network_buy_sol | 1.75 | 2.33 | 0.99 | 0 | - |
| network_sell_sol | 2.40 | 4.03 | - | 0 | - |
| total_trades | 56.8 | 221.0 | 17 | 1 | - |

### Entropy Baselines (N=93, 2026-03-05)
| Target | Bot baseline (flash_rug) | Organic baseline (pump_dump) |
|---|---|---|
| trade_amounts entropy | 0.19 ± 0.41 | 2.26 ± 0.38 |
| network_only entropy | 0.19 ± 0.41 | 1.46 ± 0.73 |
| organic_only entropy | 0.00 ± 0.00 | 1.88 ± 0.73 |

### Z-Score Velocity Baselines (first 60s, 5s windows, N=93, 2026-03-05)
| Type | Trades/5s avg | Trades/5s std | SOL/5s avg | SOL/5s std |
|---|---|---|---|---|
| pump_dump | 6.48 | 7.13 | 3.92 | 5.64 |
| unknown | 3.77 | 3.17 | 1.69 | 3.07 |
| flash_rug | 1.95 | 1.07 | 0.52 | 1.00 |

### OFI Baselines by Time Window (N=93, 2026-03-05)
| Type | OFI 0-5s | OFI 5-30s | OFI 30s+ |
|---|---|---|---|
| pump_dump | +0.41 | -0.06 | -0.61 |
| unknown | +0.22 | -0.30 | -0.57 |
| flash_rug | -0.12 | -0.51 | -0.88 |

### Concentration Baselines (N=93, 2026-03-05)
| Type | Net trade ratio | Net vol ratio | Top5 concentration | Organic buyer % |
|---|---|---|---|---|
| pump_dump | 0.31 | 0.35 | 0.71 | 76.6% |
| unknown | 0.56 | 0.73 | 0.92 | 56.4% |
| flash_rug | 1.00 | 1.00 | 1.00 | 0.0% |

---

## Kaplan-Meier Survival (N=93, 2026-03-05)

### Overall Survival (P pool NOT peaked at time T)
| T (sec) | Survival |
|---|---|
| 5 | 48.4% |
| 10 | 38.7% |
| 15 | 33.3% |
| 30 | 24.7% |
| 60 | 17.2% |
| 120 | 11.8% |
| 300 | 5.4% |

### Median Time to Peak by Type
| Type | Median | P75 |
|---|---|---|
| pump_dump (N=36) | 18s | 122s |
| slow_rug (N=10) | 12s | 91s |
| unknown (N=32) | 1s | 7s |
| flash_rug (N=10) | 0s | 0s |

### Pump_dump Sub-Types (N=36, 2026-03-05)
| Subtype | N | Avg traders | Avg peak SOL | Median TTP | Avg net_buy |
|---|---|---|---|---|---|
| organic_hit | 2 | 117 | 26.56 | 1832s | 0.78 |
| moderate_pump | 11 | 25 | 10.39 | 24s | 2.57 |
| standard | 19 | 47 | 9.66 | 9s | 2.65 |
| quick_flip | 4 | 6 | 2.01 | 5s | 1.15 |

---

## Calibrated Thresholds

### Current (rule-based, not yet model-calibrated)
| Parameter | Value | Source | Confidence |
|---|---|---|---|
| entry_profitable_position | >= 50% of sec=0 | final_verdict.js N=46 | MEDIUM |
| flash_rug_organic_buyers | == 0 | pool analysis N=93 | HIGH |
| flash_rug_entropy_threshold | < 0.5 | entropy analysis N=93 | HIGH |
| organic_hit_min_traders | > 50 | 4 organic hits found | LOW |
| network_sell_timing | sec 1-5 | pool trades N=46 | HIGH |
| time_stop_seconds | 15 | grid search N=46 | MEDIUM |
| take_profit_pct | 15% virtual growth | grid search N=46 | MEDIUM |
| z_score_anomaly | > 3.0 std from baseline | literature | MEDIUM |

---

## WAR ROOM Findings (2026-03-10, N=60, E_NEW period)

### WR-01: poolSol≥8 Entry Filter (HIGH confidence, N=60)
| Pool SOL Range | Trades | Win% | PBE% | Total PnL |
|---|---|---|---|---|
| 0-3 | 11 | 18% | 64% | -14.2% |
| 3-5 | 10 | 30% | 70% | +15.3% |
| 5-8 | 18 | 33% | 61% | +16.6% |
| 8-12 | 9 | 44% | 44% | +104.3% |
| 12-20 | 7 | 43% | 43% | +32.1% |
| 20+ | 5 | 100% | 0% | +129.9% |
**Implemented:** PHANTOM_MIN_POOL_SOL = 8

### WR-02: Peak Timing Insight (HIGH confidence, N=60)
56% of PBE losers entered AFTER pool peak. 68% of winners entered BEFORE peak.
Average peak delay: PBE +9s, Winners +34s after entry.
**Implication:** entry timing relative to peak is a strong predictor.

### WR-03: Unrealized Profit (HIGH confidence, N=23 winners)
- network_dump: realized +18.9%, peak potential +92.3%, left 73.4% on table
- trail_stop: realized +23.9%, peak potential +312.9%, left 289.0% on table
- safety_stop: realized +58.2%, peak potential +40.4%, CAPTURED MORE than peak
**REVERTED:** PHANTOM_NET_DUMP_CONFIRM_PCT removed (2026-03-10) — 76% of profitable network_dumps blocked by 30% threshold

### WR-06: Confirmed Dump Filter HARMFUL (HIGH confidence, N=21 network_dumps)
Only 5/21 (24%) network_dumps passed 30% confirm threshold.
At ALL thresholds (10%-50%), unconfirmed dumps had EQUAL/HIGHER avg profit.
38% of pools RECOVER after dump → confirmed dump is irrelevant quality signal.
**Action:** REVERTED to simple BIG_SELL_SOL ≥ 2.0

### WR-07: Address Rotation Problem (HIGH confidence, N=1442 unknown addresses)
- Detection lag: 52.7 hours avg, 6.9 pools per sniper before discovery
- Only 15-30% of traders in scam pools are known at detection time
- 1,442 unknown addresses appear in 3+ scam pools (bot behavior confirmed)
- 182 appear in 5+ pools
- Bot signatures: sec0 rate 75-93% (organic 0-4%), amount CV <0.25

### WR-08: RT Behavioral Cross-Pool Auto-Learn (DEPLOYED 2026-03-10)
Replaces old cross-pool (3+ pools → sniper, 90% false positive).
New: 2+ pools + behavioral bot filter (sec0_rate ≥50% OR amount_cv <0.25).
Constants: RT_CROSSPOOL_MIN_POOLS=2, SEC0_THRESHOLD=0.50, CV_THRESHOLD=0.25, MIN_BUYS=3
Cold start: seeded 2,078 snipers from pool_trades DB.
**Expected:** faster detection of rotated bot addresses, reduced false positives vs old approach.

### WR-04: Bot Dump Timing E_NEW (HIGH confidence, N=58)
- BLITZ (0-5s): 93% of first network sells
- avg_sec_after_entry = -1 → bot sells BEFORE we enter in most cases
**Implication:** we're already entering after first dump wave. Our profit comes from SECOND wave or organic momentum.

### WR-05: Time-of-Day Pattern (LOW confidence, N=60, small per-hour samples)
- WIN ZONE: UTC 01-05h (67-80% win)
- KILL ZONE: UTC 06-07, 12, 14-15, 21-22 (0% win)
**Status:** [HYPOTHESIS] — sample too small per hour for statistical significance

---

## AUGUR Combat Cycle Findings (2026-03-11, N=151, D+E+F combined)

### CC-01: sec=1 DEATH ZONE (CRITICAL, N=151, p<0.001)
Entry at seconds_since_creation=1 is CONSISTENTLY the worst entry timing:
| entry_sec | Trades | Win% | Avg PnL | Total PnL |
|---|---|---|---|---|
| 0 | 47 | **48.9%** | **+9.64%** | **+433.7%** |
| 1 | 27 | **12.5%** | **-0.56%** | **-13.4%** |
| 2 | 32 | 32.3% | +4.40% | +136.4% |
| 3 | 24 | 40.9% | +1.14% | +25.0% |
| 4 | 16 | 20.0% | -3.25% | -48.7% |
Stable across BOTH periods: E_NEW sec=1 = 0.0% win, F_FILTER sec=1 = 7.7% win.
**Root cause:** sec=1 = network FLASH dump timing (gangJEP5 dumps at sec=1-2). We buy INTO the dump.
**Recommendation:** Block sec=1 entries. Expected: win rate 34.5% → 41.7%, PnL +68%.

### CC-02: F_FILTER Underperformance (HIGH, N=54)
poolSol≥8 filter delivered 29.6% win rate vs expected 57%.
- PBE dominates: 63% of exits (was 50% in E_NEW)
- Trail_stop: 0% exits (was 9.4% in E_NEW)
- Safety_stop: 0% exits (was 1.6% in E_NEW)
- Network dump: 100% win rate (16/16), avg +19.06%
**Root cause:** PBE pools peak only 12% above entry (ratio 1.116). Network dump pools peak 69% above (ratio 1.689). Can't differentiate at entry time with current features.

### CC-03: RT Cross-Pool Working (HIGH confidence)
- Snipers in DB: 4,178 → **13,274** (+218% growth)
- RT-CrossPool learned 2,307 snipers (behavioral)
- 4 new banks discovered
- +4,807 addresses auto-discovered
**Concern:** High growth rate may include false positives. Monitor actual detection quality.

### CC-04: entry_features NOT STORED (DATA BUG)
phantom_trades.entry_features JSON is EMPTY for all F_FILTER trades.
entry_ofi is NULL for all trades. Blocks all Tier 1+ predictive models.
**Must fix to enable:** OFI analysis, entropy analysis, velocity features, network_buy_sol.

### CC-05: Strategy Simulations (HIGH, N=142)
| Strategy | Trades | Win% | Avg PnL | Total PnL | Max Loss Streak |
|---|---|---|---|---|---|
| sec=0 only | 45 | 48.9% | +9.64% | +433.7% | 3 |
| block sec=1 | ~103 | 41.7% | +5.99% | +617.2% | ~8 |
| current (all) | 142 | 34.5% | +3.91% | +555.1% | 17 |
**Optimal:** block sec=1 (best total PnL). sec=0 only has best per-trade metrics but lower volume.

## Data Milestones Tracker

| Milestone | Pools | Methods Unlocked | Status |
|---|---|---|---|
| 100 | 100 | KM stratified, Benford reliable, Cox PH (5 feat) | ✅ REACHED |
| 250 | 250 | Cox PH (8 features), Volume Profile | ✅ REACHED |
| 500 | 500 | XGBoost, HDBSCAN, Survival Forests | ✅ REACHED |
| 1000 | 1000 | Deep learning, robust cross-validation | ✅ REACHED (1,229) |
| **Current** | **1,345** | **ALL methods unlocked** | **ACTIVE** |
| 2000 | 2000 | Robust k-fold CV, LSTM/Transformer | PENDING |

---

## Links
- [Detailed patterns](patterns.md)
- [Calibrated thresholds](thresholds.md)
- [Model performance](model-performance.md)
- [Failed hypotheses](failed-hypotheses.md)
