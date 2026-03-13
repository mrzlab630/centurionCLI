# QUAESTOR — Trading Strategies Reference

> Strategy taxonomy with edge analysis, risk parameters, and failure modes.

## 1. DCA (Dollar-Cost Averaging)

**Type:** Passive | **Risk:** LOW | **Edge:** Time-averaging volatility

### Mechanism
Buy fixed $ amount at fixed intervals regardless of price.

### Math
```
Average Cost = Total Invested / Total Units Acquired
```
DCA outperforms lump-sum ~33% of the time in trending markets but reduces drawdown variance significantly.

### Variants
| Variant | Description | Edge vs Basic DCA |
|---|---|---|
| **Standard DCA** | Fixed amount, fixed interval | Baseline |
| **Value DCA** | Adjust amount to reach target value per period | Better accumulation at lows |
| **Aggressive DCA** | Increase amount when RSI < 30 / MVRV < 1 | Better average cost |
| **Reverse DCA** | Sell fixed amounts (de-accumulation) | Profit-taking discipline |

### Failure Modes
- Doesn't work in prolonged downtrends (averaging into zero for dead projects)
- Opportunity cost in strong bull markets (lump-sum beats DCA)
- Requires surviving 80%+ drawdowns psychologically

---

## 2. Grid Trading

**Type:** Systematic | **Risk:** MEDIUM | **Edge:** Range-bound mean reversion

### Mechanism
Place buy orders below and sell orders above current price at fixed intervals ("grid").

### Parameters
| Parameter | Description | Typical Range |
|---|---|---|
| **Upper Bound** | Top of grid range | Resistance level |
| **Lower Bound** | Bottom of grid range | Support level |
| **Grid Count** | Number of levels | 10-50 |
| **Grid Spacing** | Distance between levels | 0.5-2% (arithmetic) or 1-5% (geometric) |
| **Amount per Grid** | Position size per level | Total capital / grid count |

### Math
```
Profit per grid = Grid Spacing × Amount per Grid
Total profit (range-bound) = Trades Completed × Profit per Grid - Fees
```

### Variants
| Variant | Best For |
|---|---|
| **Arithmetic Grid** | Stable coins, low-volatility pairs |
| **Geometric Grid** | High-volatility crypto (equal % between levels) |
| **Infinity Grid** | No upper bound — sells on the way up, buys on the way down |
| **Reverse Grid** | Short-biased — for declining assets |

### Failure Modes
- **Breakout:** Price moves beyond grid → stuck with one-sided inventory
- **Trend:** Accumulates losing positions against trend
- **Fees:** High-fee venues can eat grid profits (need <0.1% maker fees)
- **Gap/Flash crash:** Price jumps over grid levels

---

## 3. Trend Following

**Type:** Active | **Risk:** MEDIUM | **Edge:** Momentum persistence

### Entry Signals
| Signal | Method | Timeframe |
|---|---|---|
| **MA Crossover** | Fast EMA crosses slow EMA | 4H-1D |
| **Breakout** | Price breaks above resistance with volume | 1H-4H |
| **Ichimoku** | Tenkan crosses Kijun above cloud | 4H-1D |
| **ADX** | ADX > 25 + DI+ > DI- (uptrend) | 4H-1D |
| **Higher High / Higher Low** | Structure break | Any |

### Exit Strategies
| Strategy | Method |
|---|---|
| **Trailing Stop** | ATR-based (2-3× ATR below price) |
| **Chandelier Exit** | Highest high - 3×ATR |
| **Parabolic SAR** | Accelerating dots system |
| **MA Cross** | Fast MA crosses below slow MA |
| **Break of Structure** | Lower low in uptrend |

### Failure Modes
- **Whipsaw:** False breakouts in range-bound markets → repeated small losses
- **Late entry:** Entering after the move → buying the top
- **Too tight stops:** Getting stopped out by normal volatility

---

## 4. Mean Reversion

**Type:** Active | **Risk:** MEDIUM | **Edge:** Statistical reversion to mean

### Signals
| Signal | Indicator | Entry |
|---|---|---|
| **Bollinger Band touch** | Price touches lower band | Long |
| **RSI extreme** | RSI < 20 | Long |
| **Z-Score** | Z < -2 from mean | Long |
| **VWAP deviation** | Price > 2σ below VWAP | Long |

### Requirements
- Confirm asset IS mean-reverting (Hurst exponent < 0.5)
- Set max loss (mean reversion fails catastrophically in trending markets)
- Use higher timeframe to confirm range-bound regime

### Failure Modes
- **Regime change:** Market transitions from range to trend → reversion trades become trend-fighting
- **Black swan:** Extreme moves don't revert (rug pulls, exchange hacks)
- **Crypto trap:** Many tokens LOOK mean-reverting until they dump to zero

---

## 5. Arbitrage

**Type:** Systematic | **Risk:** LOW-MEDIUM | **Edge:** Price discrepancy across venues

### Types
| Type | Description | Latency Required | Capital Needed |
|---|---|---|---|
| **CEX-CEX** | Same asset, different exchange prices | <100ms | HIGH |
| **CEX-DEX** | Price difference between centralized and decentralized | <500ms | MEDIUM |
| **DEX-DEX** | Same pair on different DEXs (Raydium vs Orca) | <400ms (on-chain) | MEDIUM |
| **Triangular** | A→B→C→A across 3 pairs for profit | <200ms | MEDIUM |
| **Statistical** | Cointegrated pairs diverge, bet on convergence | Seconds-minutes | HIGH |
| **Cross-chain** | Same asset on different blockchains | Minutes (bridge time) | HIGH |

### DEX Arbitrage (Solana-specific)
```
Buy on Raydium (cheaper) → Sell on Orca (more expensive)
Profit = Price_diff × Amount - Gas - Slippage
```

**Risks:**
- Slippage (price moves before execution)
- MEV (frontrunners sandwich your arb TX)
- Bridge risk (for cross-chain)
- Failed TX fees (on-chain gas is lost even on failure)

### Failure Modes
- **Competition:** Arbitrage profits converge to zero as more bots compete
- **Latency arms race:** Need co-located servers, custom RPC
- **Inventory risk:** Holding assets on multiple venues

---

## 6. MEV Extraction (Maximal Extractable Value)

**Type:** Algorithmic | **Risk:** HIGH | **Edge:** Mempool information asymmetry

### MEV Types
| Type | Mechanism | Profit Source |
|---|---|---|
| **Sandwich Attack** | Frontrun + backrun around victim TX | Victim's slippage |
| **Backrunning** | Execute right after a large TX | Arbitrage from price impact |
| **Liquidation** | Trigger and execute DeFi liquidations | Liquidation bonus |
| **JIT Liquidity** | Add/remove liquidity around a swap | Fee capture |
| **NFT Sniping** | Frontrun rare NFT mints/listings | Underpriced asset capture |

### Solana MEV Landscape
- **Jito:** Dominant MEV infrastructure on Solana (bundles, tips)
- **No public mempool:** Solana doesn't have a traditional mempool — MEV relies on leader proximity and Jito bundle system
- **Tip economy:** Validators earn tips from searchers for bundle inclusion
- **Competition:** Extremely high. Sub-10ms execution required.

### Ethical Considerations
- Sandwich attacks are predatory (extracting from retail users)
- Backrunning and liquidations are considered fair play
- JIT liquidity is beneficial (adds temporary depth)
- Regulatory attention increasing (especially on sandwich attacks)

---

## 7. Sniping (New Token Launches)

**Type:** Aggressive | **Risk:** VERY HIGH | **Edge:** First-mover on new listings

### Mechanism
Buy a token within the first seconds/blocks of its pool creation.

### Pipeline
```
1. DETECT: Pool creation event (Geyser/WebSocket)
2. VALIDATE: Check contract, liquidity, creator history
3. EXECUTE: Buy TX with high priority (Jito bundle)
4. MANAGE: Set stop-loss, take-profit, trail-stop
5. EXIT: Sell on first pump or at predetermined target
```

### Critical Parameters
| Parameter | Description | Typical |
|---|---|---|
| **Detection latency** | Time from pool creation to signal | <100ms |
| **Execution latency** | Time from signal to TX confirmation | <500ms |
| **Position size** | Amount per snipe | 0.1-2 SOL |
| **Slippage tolerance** | Max acceptable slippage | 10-30% |
| **Stop-loss** | Max loss per position | 30-50% |
| **Take-profit** | Target gain | 50-500% |

### Failure Modes
- 90%+ of sniped tokens go to zero
- Honeypots (can't sell)
- Sandwich attacks on your buy TX
- Creator dumps immediately (FAST_DUMP pattern)
- High gas/priority fees even on losses

---

## 8. Copy Trading

**Type:** Passive | **Risk:** MEDIUM | **Edge:** Mirroring proven wallets

### Mechanism
Monitor target wallets → replicate their trades in real-time.

### Target Selection Criteria
| Criteria | What to Check | Red Flag |
|---|---|---|
| **Win Rate** | % of profitable trades | <40% → avoid |
| **PnL History** | Net profit over 30/90 days | Inconsistent → avoid |
| **Trade Frequency** | Trades per day | >50 → likely bot, verify strategy |
| **Holding Time** | Average position duration | <1 min → MEV bot, not trader |
| **Max Drawdown** | Worst losing streak | >50% → too risky |
| **Token Diversity** | Variety of tokens traded | Only 1-2 tokens → manipulation risk |

### Risk Management
- **Position sizing:** Don't copy 1:1 — scale down proportionally
- **Wallet diversification:** Copy 3-5 wallets, not just one
- **Delay penalty:** Your copy is always AFTER the target → worse price (slippage impact)
- **Front-running:** Other copy-bots watching same wallet → race condition

### Failure Modes
- Target wallet changes strategy → your historical analysis becomes stale
- Target knows they're being copied → can exploit followers (pump signal, dump on copiers)
- Latency → worse entries/exits than target
- Target's size vs your size → different slippage profiles

---

## 9. Market Making

**Type:** Systematic | **Risk:** MEDIUM | **Edge:** Bid-ask spread capture

### Mechanism
Continuously place buy and sell orders around mid-price, profiting from the spread.

### Parameters
| Parameter | Description |
|---|---|
| **Spread** | Distance between bid and ask (min = 2× fees) |
| **Depth** | Number of order levels on each side |
| **Skew** | Asymmetric pricing based on inventory/trend |
| **Inventory limit** | Max position in either direction |
| **Quote size** | Amount per order level |

### Crypto Market Making
- **AMM LP:** Providing liquidity to AMMs is passive market making
- **Concentrated Liquidity:** Orca Whirlpool / Uniswap V3 — tighter ranges = more fees but more IL
- **Impermanent Loss:** If price moves, LPs lose vs holding
- **IL Formula:** IL = 2√(price_ratio) / (1 + price_ratio) - 1

### Failure Modes
- **Directional move:** Accumulate losing inventory against trend
- **Toxic flow:** Informed traders (MEV, whales) pick off your quotes
- **Impermanent loss:** Exceeds fee income in volatile markets
- **Smart contract risk:** LP funds locked in potentially exploitable contracts

---

## Quick Reference: Strategy Selection

| Market Condition | Best Strategies | Avoid |
|---|---|---|
| **Strong Uptrend** | Trend Following, Sniping, Copy Trading | Grid (accumulates shorts) |
| **Range-Bound** | Grid, Mean Reversion, Market Making | Trend Following (whipsaws) |
| **Strong Downtrend** | DCA (accumulate), Reverse DCA (exit) | Sniping, Aggressive longs |
| **High Volatility** | Grid (wider), Trend Following | Market Making (toxic flow) |
| **Low Volatility** | Market Making, Statistical Arb | Trend Following (no signals) |
| **New Launches** | Sniping + Copy Trading combo | DCA, Grid |
