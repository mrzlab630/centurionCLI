# Detailed Methods Reference

## Tier 0: Always Use First

### Z-Score Anomaly Detection
```python
import numpy as np

def z_score_anomaly(values, window=20):
    """Detect anomalies in streaming data."""
    rolling_mean = np.convolve(values, np.ones(window)/window, mode='valid')
    rolling_std = np.array([np.std(values[max(0,i-window):i]) for i in range(window, len(values))])
    z_scores = (values[window:] - rolling_mean) / (rolling_std + 1e-10)
    return z_scores  # |z| > 3 = anomaly
```

**SQL version (trade velocity per second):**
```sql
WITH per_second AS (
  SELECT seconds_since_creation AS sec,
         COUNT(*) AS trades,
         SUM(sol_amount) AS volume
  FROM bot_network.pool_trades
  WHERE pool_analysis_id = $1
  GROUP BY sec
),
stats AS (
  SELECT AVG(trades) AS mu, STDDEV(trades) AS sigma FROM per_second
)
SELECT sec, trades, (trades - mu) / NULLIF(sigma, 0) AS z_score
FROM per_second, stats
ORDER BY sec;
```

**When to use:** ALWAYS. First check on any pool. If z > 3, something unusual is happening.
**Arxiv reference:** 2412.18848 — best performance at 20-second analysis window.

---

### Order Flow Imbalance (OFI)
```python
def compute_ofi(trades, window=5):
    """Sliding window OFI. +1 = all buys, -1 = all sells."""
    results = []
    for i in range(len(trades)):
        start = max(0, i - window + 1)
        w = trades[start:i+1]
        buy_vol = sum(t['sol_amount'] for t in w if t['direction'] == 'buy')
        sell_vol = sum(t['sol_amount'] for t in w if t['direction'] == 'sell')
        total = buy_vol + sell_vol
        ofi = (buy_vol - sell_vol) / total if total > 0 else 0
        results.append(ofi)
    return results
```

**Signal interpretation:**
- OFI = +1.0 → pure buying (early pump phase)
- OFI dropping → sell pressure building
- OFI crosses 0 → more selling than buying = EXIT SIGNAL
- OFI = -1.0 → pure dump

**Key insight:** OFI crossing from positive to negative is the BEST single predictor
of dump onset. Track OFI derivative (rate of change) for early warning.

---

### Shannon Entropy
```python
import math
from collections import Counter

def shannon_entropy(values, bins=10):
    """Entropy of distribution. Low = uniform/bot, High = diverse/organic."""
    if len(values) < 2:
        return 0
    # Bin continuous values
    hist = Counter()
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return 0
    for v in values:
        bin_idx = min(int((v - min_v) / (max_v - min_v) * bins), bins - 1)
        hist[bin_idx] += 1
    total = sum(hist.values())
    entropy = -sum((c/total) * math.log2(c/total) for c in hist.values() if c > 0)
    return entropy  # max = log2(bins)
```

**What to measure entropy of:**
| Target | Bot signal | Organic signal |
|---|---|---|
| SOL input amounts | Low (fixed sizes) | High (varied) |
| Inter-trade intervals | Low (regular) | High (random) |
| Wallet ages | Low (all new) | High (mixed) |

---

## Tier 1: Core Statistical Methods

### CUSUM (Cumulative Sum Control Chart)
```python
def cusum(values, target=None, threshold=5.0, drift=0.5):
    """One-sided upper CUSUM. Returns alarm points."""
    if target is None:
        target = sum(values) / len(values)
    S_high = [0]
    alarms = []
    for i, x in enumerate(values):
        s = max(0, S_high[-1] + (x - target) - drift)
        S_high.append(s)
        if s > threshold:
            alarms.append(i)
            S_high[-1] = 0  # reset
    return alarms
```

**Apply to:** trade_velocity (detect pump start), sell_volume (detect dump start).
**SQL CUSUM:** `SUM(value - avg_value) OVER (ORDER BY sec ROWS UNBOUNDED PRECEDING)`

---

### Kaplan-Meier Survival Curves
```python
from lifelines import KaplanMeierFitter

def survival_analysis(pools_df):
    """Time-to-dump survival analysis."""
    kmf = KaplanMeierFitter()
    # Event = first network sell (dump start)
    # Duration = first_sell_delay_seconds
    # Censored = pools that never had a sell (still alive)
    kmf.fit(
        durations=pools_df['first_sell_delay_seconds'],
        event_observed=pools_df['had_network_sell'],  # 1=dumped, 0=censored
        label='All Pools'
    )
    kmf.plot_survival_function()

    # Stratify by type
    for op_type in pools_df['operation_type'].unique():
        mask = pools_df['operation_type'] == op_type
        kmf.fit(pools_df.loc[mask, 'first_sell_delay_seconds'],
                pools_df.loc[mask, 'had_network_sell'],
                label=op_type)
        kmf.plot_survival_function()
```

**Interpretation:** Survival curve drops = pools being dumped. Steep drop at T=5s means
"most pools get dumped within 5 seconds." Stratification shows which pool types survive longer.

---

### Cox Proportional Hazards
```python
from lifelines import CoxPHFitter

def cox_model(pools_df):
    """Which features predict faster dump?"""
    # Max 5-8 features with 81 pools!
    features = [
        'network_buy_sol',      # How much network invested
        'unique_buyers',        # Organic interest
        'entropy_amounts',      # Trade diversity
        'ofi_at_peak',          # Buy/sell balance at peak
        'first_sell_delay_seconds'  # Duration (outcome)
    ]
    cph = CoxPHFitter()
    cph.fit(pools_df[features + ['had_network_sell']],
            duration_col='first_sell_delay_seconds',
            event_col='had_network_sell')
    cph.print_summary()
    # Hazard Ratio interpretation:
    # HR > 1 = feature INCREASES dump risk
    # HR < 1 = feature DECREASES dump risk
    return cph
```

---

### Benford's Law Test
```python
from scipy.stats import chisquare
import math

BENFORD_EXPECTED = [math.log10(1 + 1/d) for d in range(1, 10)]

def benford_test(sol_amounts):
    """Test if SOL input amounts follow Benford's law. ONLY use on SOL inputs."""
    first_digits = []
    for amt in sol_amounts:
        if amt > 0:
            s = f"{amt:.10f}".lstrip('0').lstrip('.')
            if s and s[0].isdigit() and s[0] != '0':
                first_digits.append(int(s[0]))
    if len(first_digits) < 30:
        return None  # Too few samples
    observed = [first_digits.count(d) for d in range(1, 10)]
    total = sum(observed)
    expected = [e * total for e in BENFORD_EXPECTED]
    stat, p_value = chisquare(observed, expected)
    return {'chi2': stat, 'p_value': p_value, 'is_bot': p_value < 0.05}
```

---

### Cross-Pool Co-Occurrence
```sql
-- Find wallets that appear together in multiple pools
WITH wallet_pools AS (
  SELECT trader_address, pool_analysis_id,
         MIN(seconds_since_creation) AS entry_time
  FROM bot_network.pool_trades
  WHERE direction = 'buy'
  GROUP BY trader_address, pool_analysis_id
)
SELECT a.trader_address AS wallet_a,
       b.trader_address AS wallet_b,
       COUNT(DISTINCT a.pool_analysis_id) AS shared_pools,
       AVG(ABS(a.entry_time - b.entry_time)) AS avg_timing_diff
FROM wallet_pools a
JOIN wallet_pools b ON a.pool_analysis_id = b.pool_analysis_id
  AND a.trader_address < b.trader_address
  AND ABS(a.entry_time - b.entry_time) <= 3  -- within 3 seconds
GROUP BY a.trader_address, b.trader_address
HAVING COUNT(DISTINCT a.pool_analysis_id) >= 3
ORDER BY shared_pools DESC;
```

**Interpretation:** shared_pools >= 5 AND avg_timing_diff < 2s → almost certainly same operator.

---

## Tier 2: Advanced (Python + Libraries)

### BOCPD (Bayesian Online Changepoint Detection)
```python
import ruptures

def detect_changepoints(signal, model='rbf', penalty=3):
    """Offline changepoint detection on pool trade signal."""
    algo = ruptures.Pelt(model=model, min_size=3).fit(signal)
    breakpoints = algo.predict(pen=penalty)
    return breakpoints  # indices where regime changes
```

**Apply to:** cumulative buy volume time series. Breakpoint = transition between phases.

### HDBSCAN Wallet Clustering
```python
import hdbscan
import numpy as np

def cluster_wallets(feature_matrix, min_cluster_size=5):
    """Auto-cluster wallets. Returns labels (-1 = noise/outlier)."""
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                 min_samples=3,
                                 metric='euclidean')
    labels = clusterer.fit_predict(feature_matrix)
    # Noise points = potential unknown bots or unique organic
    return labels, clusterer.probabilities_
```

**Unlock condition:** 200+ wallets with computed features.

---

## Volume Profile Analysis

```sql
-- Volume distribution across price levels (pool_sol_after = proxy for price)
WITH price_bins AS (
  SELECT
    FLOOR(pool_sol_after / 0.5) * 0.5 AS price_level,  -- 0.5 SOL bins
    direction,
    COUNT(*) AS trades,
    SUM(sol_amount) AS volume
  FROM bot_network.pool_trades
  WHERE pool_analysis_id = $1
  GROUP BY price_level, direction
)
SELECT price_level,
       SUM(CASE WHEN direction='buy' THEN volume ELSE 0 END) AS buy_volume,
       SUM(CASE WHEN direction='sell' THEN volume ELSE 0 END) AS sell_volume,
       SUM(CASE WHEN direction='buy' THEN trades ELSE 0 END) AS buy_trades,
       SUM(CASE WHEN direction='sell' THEN trades ELSE 0 END) AS sell_trades
FROM price_bins
GROUP BY price_level
ORDER BY price_level;
```

**Interpretation:** Heavy buy volume at level X + heavy sell volume at level X+2 =
network accumulated at X and dumped at X+2.

---

## Relative Strength vs Baseline

Instead of absolute thresholds, compare each pool to the "average" pool:

```python
def relative_strength(pool_metrics, baseline_metrics):
    """How does this pool compare to baseline? Returns z-scores per metric."""
    rs = {}
    for key in pool_metrics:
        if key in baseline_metrics:
            mu = baseline_metrics[key]['mean']
            sigma = baseline_metrics[key]['std']
            if sigma > 0:
                rs[key] = (pool_metrics[key] - mu) / sigma
            else:
                rs[key] = 0
    return rs
```

**Baseline** = computed from KNOWLEDGE.md (updated after each batch analysis).
RS > 2 = this pool is unusually high on this metric.
RS < -2 = this pool is unusually low.
