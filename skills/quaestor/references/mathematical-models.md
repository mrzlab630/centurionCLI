# QUAESTOR — Mathematical Models Reference

> Formulas, statistical methods, and quantitative frameworks for crypto analysis.

## 1. Position Sizing

### Kelly Criterion
Optimal fraction of capital to risk per bet.

```
f* = (b × p - q) / b

Where:
  f* = fraction of bankroll to bet
  b  = net odds (win amount / loss amount)
  p  = probability of winning
  q  = 1 - p (probability of losing)
```

| Example | p | b | f* | Interpretation |
|---|---|---|---|---|
| High-confidence trade | 0.6 | 2.0 | 0.40 | Bet 40% of bankroll |
| Medium-confidence | 0.55 | 1.5 | 0.25 | Bet 25% |
| Low-confidence | 0.45 | 3.0 | 0.267 | Still positive EV |
| Negative EV | 0.30 | 2.0 | -0.05 | DON'T TRADE (f* < 0) |

**Practical rules:**
- Use **Half-Kelly** (f*/2) to reduce variance — common in professional trading
- **Quarter-Kelly** for crypto (higher uncertainty than estimated)
- NEVER exceed Kelly — over-betting guarantees ruin eventually
- Requires accurate probability estimates (hard in crypto)

### Fixed Fractional
```
Position Size = Account × Risk% / (Entry - StopLoss)
```
Simpler than Kelly. Risk 1-3% per trade. Standard for most traders.

### Risk of Ruin
```
R = ((1 - Edge) / (1 + Edge))^Units

Where:
  Edge = (Win% × AvgWin - Loss% × AvgLoss) / AvgLoss
  Units = Bankroll / AvgBetSize
```
At 2% risk per trade with 55% win rate: R ≈ 0.0001 (negligible)
At 10% risk per trade with 55% win rate: R ≈ 0.12 (12% chance of ruin)

---

## 2. Risk-Adjusted Returns

### Sharpe Ratio
Risk-adjusted return relative to risk-free rate.
```
S = (Rp - Rf) / σp

Where:
  Rp = portfolio return
  Rf = risk-free rate (typically 3-5% annually)
  σp = standard deviation of portfolio returns
```
| Sharpe | Interpretation |
|---|---|
| < 0 | Negative risk-adjusted return — worse than risk-free |
| 0-1 | Suboptimal |
| 1-2 | Good |
| 2-3 | Very good |
| > 3 | Excellent (verify — may indicate overfitting) |

### Sortino Ratio
Like Sharpe but only penalizes downside volatility.
```
Sortino = (Rp - Rf) / σd

Where:
  σd = standard deviation of NEGATIVE returns only
```
Better than Sharpe for crypto (upside volatility is desirable).

### Calmar Ratio
Return vs maximum drawdown.
```
Calmar = Annual Return / Max Drawdown
```
| Calmar | Interpretation |
|---|---|
| < 0.5 | Poor |
| 0.5-1 | Acceptable |
| 1-3 | Good |
| > 3 | Excellent |

### Maximum Drawdown
```
MDD = max(Peak_i - Trough_j) / Peak_i, for all j > i
```
Measures worst peak-to-trough decline. Critical for survivability.

---

## 3. Expected Value & Edge

### Expected Value (EV)
```
EV = P(win) × Average_Win - P(loss) × Average_Loss

Positive EV → trade has edge (long-term profitable)
Negative EV → trade is -EV (guaranteed loss long-term)
```

### Win Rate Required for Breakeven
```
Required_WR = 1 / (1 + R:R)

Where R:R = Risk:Reward ratio
```
| Risk:Reward | Required Win Rate |
|---|---|
| 1:1 | 50% |
| 1:2 | 33.3% |
| 1:3 | 25% |
| 2:1 | 66.7% |
| 3:1 | 75% |

### Edge Decay
In crypto, edges decay fast due to competition.
```
Edge_t = Edge_0 × e^(-λt)

Where:
  λ = decay rate (higher for simpler strategies)
  t = time since edge discovery
```
- MEV edge: λ ≈ 0.5-1.0/month (fast decay)
- Copy trading edge: λ ≈ 0.1-0.3/month
- Market cycle timing: λ ≈ 0.01-0.05/month (slow decay)

---

## 4. Volatility Models

### Historical Volatility
```
σ = std(ln(P_t / P_{t-1})) × √(252)    (annualized, 252 trading days)
σ_crypto = std(ln(P_t / P_{t-1})) × √(365)    (crypto is 365 days)
```

### GARCH(1,1) (Generalized Autoregressive Conditional Heteroskedasticity)
Models time-varying volatility (volatility clustering).
```
σ²_t = ω + α × ε²_{t-1} + β × σ²_{t-1}

Where:
  ω = long-run average variance weight
  α = reaction to recent shock (yesterday's squared return)
  β = persistence (yesterday's variance)
  α + β < 1 for stationarity
```
**High α:** Volatility reacts strongly to new shocks (jumpy)
**High β:** Volatility is persistent (decays slowly)
**Crypto typical:** α ≈ 0.05-0.15, β ≈ 0.80-0.93

### Parkinson Volatility (High-Low estimator)
```
σ² = (1/4ln2) × (ln(H/L))²
```
More efficient than close-to-close. Uses intraday range.

---

## 5. Statistical Tests & Detection

### Z-Score (Deviation Detection)
```
z = (x - μ) / σ
```
| Z-Score | Probability | Application |
|---|---|---|
| ±1σ | 68.3% | Normal variation |
| ±2σ | 95.4% | Unusual — worth watching |
| ±3σ | 99.7% | Extreme — likely anomaly |
| ±5σ | 99.99994% | Almost certainly manipulation or extraordinary event |

**For volume anomaly detection:**
```
z_volume = (current_volume - rolling_mean) / rolling_std
IF z_volume > 5 → FLAG as potential pump
```

### Benford's Law (First-Digit Analysis)
Natural data follows Benford's distribution for first digits.
```
P(d) = log10(1 + 1/d), for d = 1,2,...,9
Expected: 1→30.1%, 2→17.6%, 3→12.5%, 4→9.7%, 5→7.9%, 6→6.7%, 7→5.8%, 8→5.1%, 9→4.6%
```
**Application:** If trade amounts or TX values deviate significantly from Benford's → potential wash trading or manipulation.

### Hurst Exponent (Trend Persistence)
```
H = log(R/S) / log(n)

Where R/S = rescaled range statistic
```
| H Value | Interpretation | Trading Strategy |
|---|---|---|
| H < 0.5 | Mean-reverting | Mean reversion strategies |
| H ≈ 0.5 | Random walk | No edge from trend/reversion |
| H > 0.5 | Trending (persistent) | Trend following strategies |

**Crypto typical:** BTC H ≈ 0.55-0.65 on daily (mildly trending). Altcoins more variable.

---

## 6. Bayesian Analysis

### Bayes' Theorem
```
P(A|B) = P(B|A) × P(A) / P(B)

Where:
  P(A|B) = probability of A given B (posterior)
  P(B|A) = probability of B given A (likelihood)
  P(A)   = prior probability of A
  P(B)   = probability of B (evidence)
```

### Application: Scam Probability Update
```
Prior: P(scam) = 0.80 (80% of new tokens are scams — base rate)

Evidence: Creator has 3 previously successful tokens
P(3_success | scam) = 0.05 (rare for scammers to have legit history)
P(3_success | legit) = 0.30

P(scam | 3_success) = (0.05 × 0.80) / ((0.05 × 0.80) + (0.30 × 0.20))
                     = 0.04 / (0.04 + 0.06)
                     = 0.40 (updated: 40% scam probability)
```

### Sequential Bayesian Update
Each new piece of evidence updates the posterior:
```
Signal 1: LP locked → P(scam) drops
Signal 2: Mint authority active → P(scam) rises
Signal 3: Team doxxed → P(scam) drops
Signal 4: Volume spike without holder growth → P(scam) rises
```

---

## 7. Monte Carlo Simulation

### Method
```
1. Define model: returns distribution, parameters
2. Generate N random scenarios (10,000-100,000)
3. For each scenario: simulate portfolio path
4. Analyze distribution of outcomes
```

### Application: Strategy Backtesting Robustness
```
For i = 1 to N:
    Resample historical returns (bootstrap)
    Run strategy on resampled data
    Record final PnL, max drawdown, Sharpe

Output:
    Median outcome, 5th percentile (worst case), 95th percentile (best case)
    P(ruin) = count(outcomes < ruin_threshold) / N
```

### Application: Pool Behavior Prediction
```
For each new pool:
    Sample from historical pool outcomes by feature similarity
    Weight samples by feature match quality
    Output: P(ROCKET), P(SLOW_BURNER), P(FAST_DUMP), P(SLOW_BLEED)
```

---

## 8. On-Chain Math

### AMM (Constant Product) Math
```
x × y = k

Where:
  x = token A reserves
  y = token B reserves
  k = constant product (invariant)
```

**Price:** P = y/x (how much B per A)
**Price impact:**
```
Price_impact = 2 × amount / (reserve + amount)
```
For 1 SOL trade in 100 SOL pool: impact = 2×1/101 ≈ 2%

### Bonding Curve Math (Pump.fun)
```
P(s) = a × s^n + b

Where:
  s = supply sold
  n = curve exponent (typically 1 for linear, 2 for quadratic)
  a, b = curve parameters
```
Linear bonding curve: each token costs more than the last.
Market cap at supply s: MC = P(s) × s

### Impermanent Loss (IL)
```
IL = 2 × √(price_ratio) / (1 + price_ratio) - 1

Where:
  price_ratio = current_price / entry_price
```
| Price Change | IL |
|---|---|
| ±25% | -0.6% |
| ±50% | -2.0% |
| ±100% (2×) | -5.7% |
| ±300% (4×) | -20.0% |
| ±500% (6×) | -30.0% |

For CLMM (concentrated liquidity), IL is amplified proportionally to concentration range.

### Gini Coefficient (Holder Distribution)
```
G = (2 × Σ(i × x_i)) / (n × Σ(x_i)) - (n+1)/n

Where:
  x_i = sorted holdings (ascending)
  n = number of holders
```
| Gini | Interpretation |
|---|---|
| 0.0-0.3 | Equal distribution (healthy) |
| 0.3-0.6 | Moderate concentration |
| 0.6-0.8 | High concentration (whale-dominated) |
| 0.8-1.0 | Extreme concentration (likely scam/pre-mine) |

---

## 9. Signal Combination

### Weighted Signal Score
```
Score = Σ(w_i × signal_i) / Σ(w_i)

Where:
  signal_i = individual signal value (0 or 1, or continuous)
  w_i = weight (based on historical accuracy)
```

### Ensemble Methods (for multiple models)
| Method | Approach | Best For |
|---|---|---|
| **Simple Average** | Equal weight all models | When models are similar quality |
| **Weighted Average** | Weight by past accuracy | When some models are better |
| **Voting** | Majority vote (binary signals) | Classification (scam/not scam) |
| **Stacking** | Meta-model trained on model outputs | When you have enough data |

### Correlation-Aware Combination
Signals that are independent (low correlation) add more information.
```
Effective N = N / (1 + (N-1) × avg_correlation)
```
3 signals with avg correlation 0.8: Effective N = 3/(1+2×0.8) = 1.15 (barely more than 1 signal)
3 signals with avg correlation 0.2: Effective N = 3/(1+2×0.2) = 2.14 (much more informative)

---

## Quick Reference: Which Model for What

| Task | Primary Model | Secondary |
|---|---|---|
| **Position sizing** | Kelly Criterion (half-Kelly) | Fixed Fractional (simpler) |
| **Strategy evaluation** | Sharpe/Sortino + Max Drawdown | Monte Carlo simulation |
| **Scam probability** | Bayesian Update (sequential) | Weighted Signal Score |
| **Anomaly detection** | Z-Score (volume, price) | Benford's Law (amounts) |
| **Trend vs Range** | Hurst Exponent | ADX indicator |
| **Volatility modeling** | GARCH(1,1) | Parkinson (simpler) |
| **Pool prediction** | Monte Carlo + Feature matching | Bayesian with priors |
| **Price impact** | AMM math (x×y=k) | Bonding curve formula |
| **Risk assessment** | Risk of Ruin + Max Drawdown | Calmar Ratio |
| **Signal combining** | Weighted average (accuracy-weighted) | Ensemble voting |
