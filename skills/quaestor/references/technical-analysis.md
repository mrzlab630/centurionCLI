# QUAESTOR — Technical Analysis Reference

> Indicators, patterns, and on-chain metrics for crypto market analysis.

## 1. Trend Indicators

### Moving Averages
| Type | Formula | Use |
|---|---|---|
| **SMA(n)** | Average of last n closes | Smooth trend, lagging |
| **EMA(n)** | Weighted towards recent prices | More responsive than SMA |
| **WMA(n)** | Linearly weighted | Between SMA and EMA |
| **VWMA(n)** | Volume-weighted | Factors in trading activity |

**Key EMAs:** 9 (scalp), 20 (short-term), 50 (medium), 100 (long), 200 (major trend)
**Golden Cross:** 50-EMA crosses above 200-EMA → bullish
**Death Cross:** 50-EMA crosses below 200-EMA → bearish

### MACD (Moving Average Convergence Divergence)
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```
- **Bullish:** MACD crosses above Signal, histogram turns positive
- **Bearish:** MACD crosses below Signal, histogram turns negative
- **Divergence:** Price makes new high but MACD doesn't = bearish divergence (and vice versa)

### ADX (Average Directional Index)
```
ADX = Smoothed average of |+DI - -DI| / (+DI + -DI)
```
| ADX Value | Trend Strength |
|---|---|
| < 20 | No trend (range-bound) |
| 20-40 | Developing trend |
| 40-60 | Strong trend |
| > 60 | Extremely strong trend |

### Ichimoku Cloud
| Component | Calculation | Purpose |
|---|---|---|
| **Tenkan-sen** | (9-high + 9-low) / 2 | Conversion line (fast) |
| **Kijun-sen** | (26-high + 26-low) / 2 | Base line (slow) |
| **Senkou Span A** | (Tenkan + Kijun) / 2, plotted 26 ahead | Leading span A |
| **Senkou Span B** | (52-high + 52-low) / 2, plotted 26 ahead | Leading span B |
| **Chikou Span** | Close, plotted 26 behind | Lagging confirmation |

**Cloud (Kumo):** Between Span A and Span B. Price above cloud = bullish, below = bearish. Thicker cloud = stronger support/resistance.

---

## 2. Momentum Indicators

### RSI (Relative Strength Index)
```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss (over 14 periods default)
```
| Zone | Signal |
|---|---|
| > 70 | Overbought (potential reversal down) |
| 30-70 | Neutral |
| < 30 | Oversold (potential reversal up) |

**Hidden Divergence:** Price makes higher low + RSI makes lower low = bullish continuation.
**Crypto note:** In strong trends, RSI can stay >70 or <30 for extended periods. Use 80/20 thresholds in strong trends.

### Stochastic RSI
```
StochRSI = (RSI - RSI_low) / (RSI_high - RSI_low)
```
More sensitive than RSI. Good for timing entries in trending markets.
- Overbought: > 0.8
- Oversold: < 0.2

### Williams %R
```
%R = (Highest High - Close) / (Highest High - Lowest Low) × -100
```
Range: -100 to 0. Below -80 = oversold. Above -20 = overbought. Faster than RSI.

### CCI (Commodity Channel Index)
```
CCI = (Typical Price - SMA(TP)) / (0.015 × Mean Deviation)
```
> +100 = overbought. < -100 = oversold. Good for cyclical assets.

---

## 3. Volatility Indicators

### Bollinger Bands
```
Middle Band = SMA(20)
Upper Band = SMA(20) + 2σ
Lower Band = SMA(20) - 2σ
```
- **Squeeze:** Bands narrow → volatility compression → breakout imminent
- **Walk the Band:** Price rides upper/lower band during strong trends
- **W-bottom:** Double bottom with second low inside bands = reversal
- **Band Width:** (Upper - Lower) / Middle — quantifies volatility

### ATR (Average True Range)
```
TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
ATR = SMA(14) of TR
```
Use for: stop-loss placement (2-3× ATR), position sizing, volatility comparison.

### Keltner Channels
```
Middle = EMA(20)
Upper = EMA(20) + 2 × ATR(10)
Lower = EMA(20) - 2 × ATR(10)
```
Similar to Bollinger but ATR-based instead of standard deviation. Less sensitive to individual outliers.

---

## 4. Volume Indicators

### OBV (On-Balance Volume)
```
If Close > Prev Close: OBV = Prev OBV + Volume
If Close < Prev Close: OBV = Prev OBV - Volume
```
Cumulative. Rising OBV with flat price = accumulation. Falling OBV with flat price = distribution.

### Volume Profile
Shows volume distribution at each price level over a period.
- **POC (Point of Control):** Price with most volume — strong magnet
- **Value Area (VA):** 70% of volume range — support/resistance zone
- **HVN (High Volume Node):** Strong S/R
- **LVN (Low Volume Node):** Price moves quickly through these

### VWAP (Volume Weighted Average Price)
```
VWAP = Σ(Price × Volume) / Σ(Volume)
```
Institutional benchmark. Price above VWAP = bullish intraday, below = bearish.

### CVD (Cumulative Volume Delta)
```
Delta = Buy Volume - Sell Volume (per candle)
CVD = Running sum of Delta
```
Rising CVD + rising price = healthy trend. Falling CVD + rising price = divergence (weak trend).

---

## 5. Chart Patterns

### Reversal Patterns
| Pattern | Trend Before | Signal | Reliability |
|---|---|---|---|
| **Head & Shoulders** | Uptrend | Bearish | HIGH |
| **Inverse H&S** | Downtrend | Bullish | HIGH |
| **Double Top** | Uptrend | Bearish | HIGH |
| **Double Bottom** | Downtrend | Bullish | HIGH |
| **Triple Top/Bottom** | Either | Reversal | VERY HIGH |
| **Rising Wedge** | Uptrend | Bearish | MEDIUM |
| **Falling Wedge** | Downtrend | Bullish | MEDIUM |

### Continuation Patterns
| Pattern | Trend | Signal | Reliability |
|---|---|---|---|
| **Bull/Bear Flag** | Trending | Continuation | HIGH |
| **Pennant** | Trending | Continuation | MEDIUM |
| **Symmetrical Triangle** | Either | Breakout direction | MEDIUM |
| **Ascending Triangle** | Uptrend | Bullish | HIGH |
| **Descending Triangle** | Downtrend | Bearish | HIGH |
| **Cup & Handle** | Uptrend | Bullish continuation | HIGH |

### Crypto Reliability Warning
Chart patterns are LESS reliable in crypto due to:
- 24/7 trading (no gaps/opens to confirm patterns)
- Lower liquidity = easier manipulation
- Bot-driven markets can create fake patterns
- Meme coins ignore all TA

---

## 6. Multi-Timeframe Analysis (MTA)

**Rule:** Always analyze at least 3 timeframes.

| Timeframe | Purpose | For |
|---|---|---|
| **Higher (4H/1D/1W)** | Context — overall trend | Direction bias |
| **Middle (1H/4H)** | Signal — pattern/setup identification | Trade setup |
| **Lower (5m/15m)** | Entry — precise entry timing | Execution |

**Process:**
1. Higher TF: determine trend direction (long only in uptrend, short only in downtrend)
2. Middle TF: find setup (pattern, indicator signal)
3. Lower TF: time the entry (support bounce, breakout candle)

---

## 7. Candlestick Patterns (Key)

### Single Candle
| Pattern | Appearance | Signal |
|---|---|---|
| **Hammer** | Small body, long lower wick (bottom) | Bullish reversal |
| **Shooting Star** | Small body, long upper wick (top) | Bearish reversal |
| **Doji** | Open ≈ Close, wicks both sides | Indecision |
| **Marubozu** | Full body, no wicks | Strong conviction |

### Multi-Candle
| Pattern | Signal | Reliability |
|---|---|---|
| **Engulfing (Bullish/Bearish)** | Reversal | HIGH |
| **Morning/Evening Star** | Reversal | HIGH |
| **Three White Soldiers / Black Crows** | Strong continuation | MEDIUM |
| **Tweezer Top/Bottom** | Reversal | MEDIUM |

---

## 8. On-Chain Technical Indicators

### Solana-Specific Metrics
| Metric | Source | What It Shows |
|---|---|---|
| **DEX Volume (Jupiter/Raydium)** | On-chain TX | Market activity, speculation level |
| **New Token Creation Rate** | Pump.fun / Raydium launches | Speculative sentiment |
| **Active Wallets** | Validator data | Network health |
| **TX Count / TPS** | Block data | Usage demand |
| **Staking Ratio** | Stake accounts | SOL locked (supply reduction) |
| **Priority Fees** | TX fees | Network congestion, demand |

### Token-Level On-Chain TA
| Metric | What To Check | Red Flag |
|---|---|---|
| **Holder Count** | Growing or declining? | Sharp drop = exodus |
| **Top 10 Holder %** | Concentration | >50% = manipulation risk |
| **Transfer Count** | Velocity | Sudden spike = coordinated move |
| **Unique Buyers vs Sellers** | Net demand | Sellers >> Buyers = dump |
| **LP Amount** | Liquidity depth | Low LP = high slippage, rug risk |

---

## Quick Reference: Indicator Confluence

**Strong Buy Signal (3+ needed):**
- Price above 200-EMA + above Ichimoku cloud
- RSI crossing above 50 from oversold
- MACD bullish crossover
- OBV/CVD rising
- Volume increasing on up moves
- On-chain: exchange outflow + active addresses rising

**Strong Sell Signal (3+ needed):**
- Price below 200-EMA + below Ichimoku cloud
- RSI crossing below 50 from overbought
- MACD bearish crossover
- OBV/CVD falling
- Volume increasing on down moves
- On-chain: exchange inflow + whale selling
