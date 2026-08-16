# Confirmed Behavioral Patterns

> Updated by AUGUR after each analysis session.
> Only CONFIRMED patterns (observed in 3+ pools or p<0.05).

## Network Operation Patterns

### NOP-01: Jito Bundle Structure (2026-03-04, HIGH)
CREATE TX + all network BUY TXs are packed in one Jito bundle.
Same slot, same second. Signer of CREATE = creator wallet.
Network buys: 3-7 snipers, each buying ~0.5-2 SOL worth of tokens.
Total network buy: typically 3-15 SOL per pool.

### NOP-02: Sniper Sell Wave Timing (REVISED 2026-03-05, N=93, HIGH)
Network snipers begin selling at seconds_since_creation = 1-5.
Sell timing by pool type:
- pump_dump: first_sell_delay median=16s (P75=43s)
- unknown: median=2.5s
- flash_rug: median=104s (irrelevant — no buyers)
- slow_rug: median=126s
Sell wave duration: 1-3 seconds (possibly bundled).

### NOP-03: Pool Abandonment Criteria (2026-03-04, MEDIUM)
If zero organic buyers within 3 seconds → pool is abandoned (flash_rug).
Network sells everything and moves on.
Confirmed: flash_rug has 100% network trade ratio, 0.0 organic buyers (N=10).

### NOP-04: Funding Pattern (2026-03-03, MEDIUM)
Snipers funded at ~10 SOL each from bank/transit.
Funding happens 30-60 min before pool creation (not immediately before).

### NOP-05: Network Participation is Type-Dependent (NEW 2026-03-05, N=93, HIGH)
| Type | Net trade ratio | Net vol ratio | Top5 concentration |
|---|---|---|---|
| flash_rug | 100% | 100% | 100% |
| unknown | 56% | 73% | 92% |
| slow_rug | 53% | 67% | 99% |
| wash_trading | 40% | 42% | 100% |
| pump_dump | 31% | 35% | 71% |
pump_dump has LOWEST network dominance → most organic participation.

## Pool Lifecycle Patterns

### PLP-01: Five Pool Types (REVISED 2026-03-05, N=93)
| Type | N | Avg traders | Avg peak SOL | Median TTP |
|---|---|---|---|---|
| pump_dump | 36 | 39.8 | 9.97 | 18s |
| unknown | 32 | 7.0 | 3.20 | 1s |
| flash_rug | 10 | 1.1 | 0.49 | 0s |
| slow_rug | 10 | 3.4 | 1.46 | 12s |
| wash_trading | 5 | 2.6 | 0.62 | 1s |

### PLP-02: Peak Timing Distribution (REVISED 2026-03-05, N=93)
Overall: 51.6% pools peak within 5s, 66.7% within 15s, 94.6% within 300s.
By type:
- pump_dump: P25=6s, median=18s, P75=122s, P90=657s
- unknown: P25=0s, median=1s, P75=7s
- flash_rug: median=0s (instant)

### PLP-03: Pump_dump Sub-Types (NEW 2026-03-05, N=36)
- **organic_hit** (N=2): TTP>300s, 30+ traders. The "jackpots" (avg peak 26.56 SOL).
- **moderate_pump** (N=11): TTP 10-120s, peak>3 SOL (avg 10.39 SOL).
- **standard** (N=19): TTP≤10s. Typical fast pump-dump (avg peak 9.66 SOL).
- **quick_flip** (N=4): TTP≤10s, peak≤3 SOL. Small fast trades.

## Trader Behavior Patterns

### TBP-01: Organic Buyer Sources (2026-03-04, HYPOTHESIS)
Organic buyers likely discover pools via pump.fun front page.
Confirmed by PLP-03: organic_hit pools need TIME (>5min) to attract organic crowd.

### TBP-02: Benford Signature of Bot + Human Traders (NEW 2026-03-05, N=93, HIGH)
Pump_dump buy amounts have MASSIVE Benford deviation (chi2=1818, p<0.001).
Digit 9 = 22.2% (expected 4.6%) — round amounts (0.1 SOL, 1.0 SOL).
**Surprise**: even organic buys deviate → Telegram bot users use round default amounts.
slow_rug buys are Benford-compliant (p=0.058) — more natural amounts.

### TBP-03: Entropy Fingerprint (NEW 2026-03-05, N=93, HIGH)
Trade amount entropy separates pool types:
- flash_rug: 0.19 (near zero) — all trades same size = pure bot
- pump_dump: 2.26 — diverse sizes = mix of bots + humans
Network entropy < organic entropy within all pool types.
**Threshold**: entropy < 0.5 → 100% chance flash_rug or wash_trading.

## Organic Hit Pattern

### OHP-01: Organic Hit Characteristics (NEW 2026-03-05, N=4, MEDIUM)
4 pools with >50 traders, >10 SOL peak, >90% organic ratio identified.
Key features: organic_ratio > 90%, long time_to_peak (43s-2998s), high entropy.
Network barely participates (0.78-1.48 SOL buy), but pool grows organically.
GRf3Dwo5: OFI stays positive through 30min+ (consistent buy pressure).
OFI phases for GRf3Dwo5: 0-5s=+0.12, 6-30s=+0.88, 31-60s=+0.62, 1-5m=-0.15, 10-30m=+0.09.

---

*Last updated: 2026-03-05 (Protocol A, N=93) | Next: after 100-pool milestone*
