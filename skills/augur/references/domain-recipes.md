# augur optional domain recipes

Select only the technique needed for the approved question. Examples and section
numbers are reference material, never an instruction to perform all phases or
expand scope. Core authority, current project facts and mission budget govern.

#### 2A. Dump Timing Analysis
```sql
-- First network sell timing by period
-- Are they dumping faster or slower?
-- BLITZ (0-5s) vs VARIABLE (6s+) ratio shift?
```

#### 2B. Network Composition
```sql
-- Network buyers per pool: more or fewer?
-- New unknown addresses appearing? (not in knownAll)
-- Network SOL per pool: bigger or smaller buys?
-- Creator rotation speed: new creators per hour?
```

#### 2C. Pool Structure
```sql
-- Entry pool SOL at peak: higher or lower liquidity?
-- Organic buyer count at entry: more or fewer victims?
-- Pool lifecycle: faster or slower to drain?
-- New pool operation types appearing?
```

#### 2D. Adversarial Adaptation Signals
**CRITICAL — the bot operator reads our moves.**
```
- Are they creating pools with higher initial SOL to bypass our poolSol>=8 filter?
- Are they using fewer known addresses (rotating snipers faster)?
- Are they changing dump patterns to avoid network_dump detection?
- Are they splitting sells into smaller amounts to stay below PHANTOM_BIG_SELL_SOL?
- Are they delaying dumps to bypass our PHANTOM_WINDOW_SEC?
```

Apply these methods for detection:
- **Z-Score anomaly** on trade velocity per 5s window vs baseline (z>3 = anomaly)
- **Shannon Entropy** of trade amounts per pool (drop from >2.0 to <1.5 = coordination)
- **CUSUM** on pool SOL to detect pump→dump transition point
- **Benford's Law** chi-squared test on buy amounts (deviation = artificial trading)
- **Hurst Exponent** of price series (H>0.5 = persistent trend/manipulation)

### Phase 3: AUDIT — System Performance Analysis
**Core question: Is our system performing as expected?**

#### 3A. Period Comparison
```sql
-- Compare F_FILTER (id>221) with E_NEW (158-221) and D_TRAIL30 (125-157)
SELECT period, COUNT(*), AVG(virtual_profit_pct), win_rate, total_pnl
-- Break down by exit_signal
-- Check: is poolSol>=8 filter working? (how many low-sol blocked?)
-- Check: is confirmed dump working? (fewer network_dumps but better quality?)
```

#### 3B. Entry Quality Audit
```sql
-- Run audit-entry-quality.ts for detailed per-pool breakdown
-- Verdicts: GOOD_ENTRY / DEAD_POOL / WASH_ENTRY / PREMATURE / LATE_ENTRY
-- Compare verdict distribution across periods
```

#### 3C. Deviation Detection
```
- Win rate deviation from expected (57% for poolSol>=8)
- PBE rate deviation from expected (33%)
- network_dump frequency deviation
- safety_stop capture rate
- New exit signals appearing that weren't in baseline?
```

#### 3D. Real P&L Simulation
```sql
-- At 0.2 SOL position + 0.0003 Jito + 2% Pump fees
-- Net P&L per trade, per day, cumulative
-- Max drawdown (consecutive losses)
-- Compare with previous periods
```

### Phase 4: OPTIMIZE — Strategy Improvement
**Core question: How do we get better?**

Use a focused adversarial review when the order identifies a material strategy risk; a WAR ROOM is not required.

#### 4A. Entry Filter Tuning
Test filter combinations against historical data:
```sql
-- Simulate: what if poolSol threshold was X instead of 8?
-- What if we added organic buyer count filter?
-- What if we added entropy filter?
-- What if we added time-of-day filter?
```

#### 4B. Exit Strategy Optimization
```sql
-- trail_stop: is 50% still optimal? Test 40%, 45%, 55%, 60%
-- network_dump confirmation: is 30% still optimal? Test 20%, 25%, 35%
-- safety_stop: should baseline be 120s or 180s?
-- NEW: should we add CUSUM-based exit?
```

#### 4C. Signal Quality Metrics
For each proposed change, compute:
- **Sharpe-like ratio**: avg_profit / std_profit (higher = more consistent)
- **Profit Factor**: gross_wins / gross_losses (>1.5 = good)
- **Expectancy**: (win_rate × avg_win) - (loss_rate × avg_loss)
- **Max drawdown**: worst consecutive loss streak in SOL
