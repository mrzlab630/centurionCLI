# QUAESTOR — Scam Patterns Reference

> Taxonomy of crypto scam types with on-chain fingerprints, detection algorithms, and prevention.

## 1. Pump & Dump

**Severity:** CRITICAL | **Frequency:** Very Common | **Chain:** All, especially Solana (memecoins)

### Phases
```
Phase 1: ACCUMULATION          Phase 2: MARKUP              Phase 3: DISTRIBUTION
├── Creator deploys token      ├── Social media push         ├── Creator sells large chunks
├── Creator buys via 5+ wallets├── Coordinated shilling      ├── Price crashes 80-99%
├── Fake "holder count"        ├── Volume spike (>5σ)        ├── Remaining holders stuck
├── Low initial liquidity      ├── Retail FOMO buying        ├── Liquidity drained
└── Duration: minutes-hours    └── Duration: minutes-days    └── Duration: seconds-minutes
```

### On-Chain Fingerprints
| Signal | Detection Method | Weight |
|---|---|---|
| **Creator wallet cluster** | Common funding source, similar timing | CRITICAL |
| **Coordinated buys** | Multiple wallets buying within same block/slot | HIGH |
| **Volume spike** | Volume > 5σ from rolling mean | HIGH |
| **Holder concentration** | Top 10 wallets > 60% of supply | HIGH |
| **Liquidity ratio** | SOL in pool vs token supply × price | MEDIUM |
| **Token age** | Created < 24h + high volume = suspicious | MEDIUM |
| **Social media surge** | Twitter/Telegram mentions spike | SUPPORTING |

### Detection Algorithm
```
IF (holder_cluster_detected AND volume_spike > 5σ) → ALERT: Pump Phase 2
IF (top10_supply > 60% AND token_age < 24h) → ALERT: Pre-pump accumulation
IF (large_sells_from_creator_cluster AND volume_declining) → ALERT: Dump Phase 3
CONFIDENCE = weighted_sum(signals) / max_possible
```

### Solana-Specific Variants
- **Pump.fun Launch Dumps:** Creator launches on Pump.fun, buys via multiple wallets during bonding curve, dumps after migration to Raydium
- **Coordinated Sniper Rings:** Bot networks snipe at launch, create fake momentum, dump on followers
- **Telegram Alpha Group Scam:** Group "calls" a token, insiders already loaded, group members are exit liquidity

---

## 2. Honeypot

**Severity:** CRITICAL | **Frequency:** Common | **Chain:** EVM (most common), Solana (program-level)

### Mechanism
Token can be bought but NOT sold. Contract/program blocks sell transactions.

### Types
| Type | Implementation | Detection |
|---|---|---|
| **Tax Honeypot** | Sell tax = 100% | Simulate sell TX, check output |
| **Blacklist Honeypot** | Buyers auto-added to transfer blacklist | Check if transfer function has address checks |
| **Max TX Honeypot** | Max sell amount = 0 or near-zero | Check maxTransactionAmount |
| **Pause Honeypot** | Owner can pause transfers | Check for pausable/ownable + active pause |
| **Proxy Honeypot** | Logic can be changed after deployment | Check for proxy pattern (delegatecall) |
| **Time-lock Honeypot** | Sells blocked until future timestamp | Check for time-based conditions |

### On-Chain Fingerprints
| Signal | Detection | Weight |
|---|---|---|
| **Sell simulation fails** | Attempt sell TX via simulation | CRITICAL |
| **Buy-only transactions** | Only buys in TX history, no sells | CRITICAL |
| **Contract not verified** | No source code on explorer | HIGH |
| **Owner not renounced** | Contract has active owner functions | HIGH |
| **Proxy contract** | Uses delegatecall pattern | HIGH |
| **Unusual transfer function** | Custom logic in transfer/transferFrom | MEDIUM |

### Solana Honeypot Detection
Solana uses programs (not contracts) — different detection approach:
- Check if token has freeze authority (owner can freeze accounts)
- Check if token has mint authority (owner can mint infinite supply)
- Simulate a sell TX through Raydium/Jupiter
- Check for program upgrade authority (can change logic)

---

## 3. Rug Pull

**Severity:** CRITICAL | **Frequency:** Very Common | **Chain:** All

### Types
| Type | Mechanism | Speed |
|---|---|---|
| **Hard Rug** | Creator removes all liquidity at once | Instant |
| **Soft Rug** | Team gradually sells, abandons project | Days-weeks |
| **Slow Rug** | High sell tax + gradual drain | Days-months |
| **LP Rug** | Liquidity is unlocked → removed | Instant after unlock |

### On-Chain Fingerprints
| Signal | Detection | Weight |
|---|---|---|
| **LP not locked** | Check LP token holder — is it the deployer? | CRITICAL |
| **LP lock expiring** | Lock contract countdown | CRITICAL |
| **Mint authority active** | Owner can mint new tokens (infinite supply) | CRITICAL |
| **Creator history** | Same wallet deployed 5+ short-lived tokens | HIGH |
| **LP ratio declining** | Liquidity being drained gradually | HIGH |
| **Team wallet sells** | Known team wallets selling large amounts | HIGH |
| **Social media silence** | Telegram/Discord activity drops to zero | MEDIUM |

### Prevention Checklist
- [ ] Is LP locked? For how long? Which locker contract?
- [ ] Is mint authority revoked?
- [ ] Is freeze authority revoked? (Solana)
- [ ] Is contract/program ownership renounced?
- [ ] What % of supply do top 10 wallets hold?
- [ ] Does creator have history of rug pulls?
- [ ] Is there a real team with verifiable identity?

---

## 4. Sandwich Attack

**Severity:** HIGH | **Frequency:** Very Common (automated) | **Chain:** All DEX-supporting chains

### Mechanism
```
1. Victim submits swap TX with slippage tolerance X%
2. Attacker FRONTRUN: buys same token before victim → pushes price up
3. Victim TX executes at worse price (within their slippage)
4. Attacker BACKRUN: sells immediately after → captures slippage as profit
```

### Economics
```
Attacker Profit = Victim's Slippage Loss - Gas Costs (×2 TX)
Typical: 0.5-3% of victim's trade size
```

### On-Chain Fingerprints
| Signal | Detection | Weight |
|---|---|---|
| **Same-slot frontrun+backrun** | TX A (buy), TX B (victim), TX C (sell) in same slot | CRITICAL |
| **Attacker wallet pattern** | Same wallet repeatedly sandwiches, profits from spread | HIGH |
| **Jito bundles** | 3 TX bundled together (attacker, victim, attacker) | HIGH |
| **Slippage exploitation** | Victim paid max slippage on trade | MEDIUM |

### Solana Sandwich Specifics
- Uses **Jito bundles** for atomic execution (all 3 TX in same bundle)
- No traditional mempool — relies on Jito relay or validator proximity
- **Tip economy:** Attacker pays Jito tip to ensure bundle ordering
- **Defense:** Use Jito bundles yourself, lower slippage, use aggregators with MEV protection

---

## 5. Flash Loan Attack

**Severity:** CRITICAL | **Frequency:** Occasional (high-value) | **Chain:** EVM (primarily), Solana (growing)

### Mechanism
```
1. Borrow large amount via flash loan (no collateral, same TX)
2. Manipulate price on a DEX (large buy/sell)
3. Exploit protocol that reads the manipulated price
4. Repay flash loan + profit
All in single atomic transaction.
```

### Attack Vectors
| Vector | Target | Example |
|---|---|---|
| **Oracle Manipulation** | Price oracle reads spot DEX price | Manipulate Uniswap pair → exploit lending protocol |
| **Governance Attack** | Flash-borrow governance tokens | Vote on malicious proposal |
| **Liquidation Trigger** | Push collateral below threshold | Force liquidations, buy assets cheap |
| **AMM Pool Drain** | Exploit AMM math with large trades | Calculate optimal trade sequence to extract value |

### Detection
- Single TX with enormous value flow (millions in one TX)
- Flash loan borrow + repay in same TX
- Multiple protocol interactions in one TX
- Price impact > 10% in a single trade within the TX

---

## 6. Wash Trading

**Severity:** HIGH | **Frequency:** Very Common | **Chain:** All

### Mechanism
Trading with yourself to inflate volume statistics.

### On-Chain Fingerprints
| Signal | Detection | Weight |
|---|---|---|
| **Circular transactions** | A→B→C→A pattern with same amounts | CRITICAL |
| **Common funding** | All trading wallets funded from same source | HIGH |
| **Equal amounts** | Repeated trades of exact same size | HIGH |
| **Zero net change** | Wallet balance unchanged after many trades | HIGH |
| **Bot timing** | Trades at exact intervals (every 30s, 1m) | MEDIUM |
| **Volume without holder growth** | Volume spikes but holder count flat | MEDIUM |

### Detection Algorithm
```
1. Build transaction graph for token
2. Find strongly connected components (cycles)
3. Check if cycle wallets share funding source
4. Calculate Gini coefficient of trade sizes (low Gini = wash)
5. Check time regularity of trades (FFT for periodicity)
```

---

## 7. Spoofing / Layering

**Severity:** HIGH | **Frequency:** Common on CEXs, rare on DEXs | **Chain:** CEX order books

### Mechanism
Place large buy/sell orders with intent to cancel before execution → creates false impression of support/resistance.

### On-Chain (DEX variant)
On DEXs, spoofing manifests as:
- **Fake LP:** Add large LP → attract trades → remove LP
- **Fake volume:** Wash trades that create artificial price levels
- **Quote stuffing:** Spam TX to congest network during critical moments

---

## 8. Exit Scam

**Severity:** CRITICAL | **Frequency:** Common | **Chain:** All

### Pattern
```
1. Build hype (website, social media, promises)
2. Raise funds (token sale, NFT mint, presale)
3. Deliver minimum viable product (or nothing)
4. Team dumps tokens / drains treasury
5. Social media deleted, team disappears
```

### Warning Signs (Pre-Scam)
| Signal | Red Flag Level |
|---|---|
| Anonymous team | MEDIUM (common in crypto, but risk factor) |
| No doxxed members | HIGH |
| Unrealistic promises (100× guaranteed) | CRITICAL |
| No working product before token | HIGH |
| Token unlock schedule front-loaded to team | HIGH |
| No audit of smart contracts | MEDIUM |
| Single treasury wallet (no multisig) | HIGH |
| Copy-paste whitepaper | HIGH |

---

## 9. Sybil Attack

**Severity:** HIGH | **Frequency:** Common (airdrops, governance)

### Mechanism
One entity operates many wallets to appear as many users.

### On-Chain Fingerprints
| Signal | Detection | Weight |
|---|---|---|
| **Common funding** | All wallets funded from 1-2 sources | CRITICAL |
| **Timing correlation** | Wallets active at same times | HIGH |
| **Gas patterns** | Similar gas usage, same RPC endpoint | MEDIUM |
| **Behavioral similarity** | Same DApps, same order of operations | HIGH |
| **Network graph** | Dense cluster with single funding source | CRITICAL |

### Detection (Graph Analysis)
```
1. Build wallet-to-wallet transfer graph
2. Community detection (Louvain algorithm)
3. Check cluster properties: funding source, timing, behavior
4. Score: cluster_size × behavior_similarity × funding_concentration
5. Flag clusters with score > threshold as Sybil
```

---

## 10. Oracle Manipulation

**Severity:** CRITICAL | **Frequency:** Occasional | **Chain:** All DeFi chains

### Mechanism
Attack the price feed (oracle) that DeFi protocols rely on for pricing.

### Attack Vectors
| Vector | Method |
|---|---|
| **Spot price manipulation** | Large trade on thin DEX pool → protocol reads wrong price |
| **TWAP manipulation** | Sustained trading to shift time-weighted price |
| **Chainlink stale price** | Exploit during oracle update delay |
| **Pyth confidence interval** | Exploit when confidence is wide (Solana) |

### Defense
- Use TWAP (Time-Weighted Average Price) instead of spot
- Multiple oracle sources (Chainlink + Pyth + internal)
- Circuit breakers for extreme price deviation
- Confidence interval checks (Pyth provides this)

---

## Quick Reference: Scam Detection Priority

| Scenario | Check First | Then Check |
|---|---|---|
| **New token launch** | Honeypot → Rug Pull → Pump&Dump | Creator history, LP lock |
| **Volume spike** | Wash Trading → Pump&Dump | Holder growth vs volume |
| **DeFi protocol** | Flash Loan → Oracle Manipulation | Contract audit status |
| **High slippage trade** | Sandwich Attack | MEV protection used? |
| **Airdrop farming** | Sybil Attack | Wallet cluster analysis |
| **Project investigation** | Exit Scam indicators | Team doxxing, treasury multisig |
