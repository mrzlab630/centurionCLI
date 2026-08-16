# Database Schema Reference

## Connection
```
Host: localhost | DB: meme_sniper_analytics | User: meme_sniper_analytics
Password: JHyt5lEddg57hGhjverJKMetdft54bf
```

## bot_network.phantom_trades (186 rows, as of 2026-03-10)
| Column | Type | Description |
|---|---|---|
| id | bigint | PK (period markers: ≤87=A, 88-118=B, 119-124=C, 125-157=D, 158-221=E, >221=F) |
| pool_address | varchar | Bonding curve address |
| token_mint | varchar | Token mint |
| entry_signal | varchar | e.g. `organic_3_in_2s` |
| entry_sec_since_creation | int | Seconds from pool creation to entry |
| entry_pool_sol | numeric | Pool SOL at entry |
| entry_organic_buyers | int | Organic buyers at entry |
| exit_signal | varchar | e.g. `network_dump_3.5sol`, `pool_below_entry`, `trail_stop_52pct_peak31.2` |
| exit_sec_since_creation | int | Seconds from creation to exit |
| exit_pool_sol | numeric | Pool SOL at exit |
| virtual_profit_pct | numeric | Virtual profit % (bonding curve formula) |
| actual_peak_sol | numeric | Actual peak pool SOL observed |
| actual_peak_seconds | int | Seconds to actual peak |
| status | varchar | active/closed |
| entry_features | jsonb | Detailed entry data (network/organic buyers, SOL, addresses) |
| exit_features | jsonb | Detailed exit data (network sells, peak, organic after) |
| created_at | timestamptz | Entry timestamp |

## bot_network.pool_analyses (1,229 rows)
| Column | Type | Description |
|---|---|---|
| id | bigint | PK |
| pool_address | varchar | Bonding curve address |
| token_mint | varchar | Token mint address |
| token_creation_id | bigint | FK to token_creations |
| dex_type | varchar | DEX type (pumpfun) |
| creator_address | varchar | Creator wallet |
| creator_address_id | int | FK to addresses |
| creation_time | timestamptz | Pool creation time |
| first_buy_time | timestamptz | First buy timestamp |
| first_network_sell_time | timestamptz | First network sell |
| peak_time | timestamptz | Peak pool SOL time |
| initial_sol | numeric | SOL at creation |
| peak_sol | numeric | Max pool SOL reached |
| pool_sol_at_first_sell | numeric | Pool SOL when first sell |
| first_buy_delay_seconds | int | Seconds: creation → first buy |
| first_sell_delay_seconds | int | Seconds: creation → first sell |
| time_to_peak_seconds | int | Seconds: creation → peak |
| pool_growth_at_sell_pct | numeric | % growth at first sell |
| total_trades | int | Total trade count |
| total_buys / total_sells | int | Buy/sell counts |
| unique_traders / unique_buyers | int | Unique participants |
| buyers_before_first_sell | int | Buyers before any sell |
| network_buy_count / network_buy_sol | int/numeric | Network buy metrics |
| network_sell_count / network_sell_sol | int/numeric | Network sell metrics |
| regular_buy_count / regular_buy_sol | int/numeric | Organic buy metrics |
| regular_sell_count / regular_sell_sol | int/numeric | Organic sell metrics |
| operation_type | varchar | Classification (hit, flash_rug, etc) |
| analysis_version | int | Schema version |

## bot_network.pool_trades (103,267 rows)
| Column | Type | Description |
|---|---|---|
| id | bigint | PK |
| pool_analysis_id | bigint | FK to pool_analyses |
| pool_address | varchar | Bonding curve |
| signature | varchar | TX signature |
| slot | bigint | Solana slot |
| block_time | timestamptz | Block timestamp |
| trade_index | int | Order within pool |
| direction | varchar | 'buy' or 'sell' |
| trader_address | varchar | Trader wallet |
| trader_address_id | int | FK to addresses (nullable) |
| sol_amount | numeric | SOL traded |
| token_amount | numeric | Tokens traded |
| pool_sol_after | numeric | Pool SOL after trade |
| seconds_since_creation | int | Seconds from pool creation |
| trader_type | varchar | Classification of trader |
| is_network_related | boolean | Known network member? |

## bot_network.addresses (20,403 active rows)
| Column | Type | Key fields |
|---|---|---|
| id | int | PK |
| address | varchar | Solana address |
| address_type | varchar | bank/transit/sniper/creator |
| first_seen_at | timestamptz | Discovery time |
| priority | int | Geyser priority score |

## bot_network.sol_transfers (2.4M rows)
Core transfer log. Fields: sender, recipient, amount_sol, signature, slot, block_time.

## bot_network.token_creations
Token creation events. Fields: creator_address, token_mint, bonding_curve, signature, slot.

## Useful Queries

### Pool with all trades
```sql
SELECT pa.*, pt.trade_index, pt.direction, pt.trader_address,
       pt.sol_amount, pt.pool_sol_after, pt.seconds_since_creation,
       pt.is_network_related, pt.trader_type
FROM bot_network.pool_analyses pa
JOIN bot_network.pool_trades pt ON pt.pool_analysis_id = pa.id
WHERE pa.id = $1
ORDER BY pt.trade_index;
```

### Network wallet check
```sql
SELECT address, address_type
FROM bot_network.addresses
WHERE address = $1;
```

### Active pools by type
```sql
SELECT operation_type, COUNT(*), AVG(peak_sol), AVG(time_to_peak_seconds)
FROM bot_network.pool_analyses
GROUP BY operation_type ORDER BY count DESC;
```

### Phantom trades by period and exit signal
```sql
SELECT
    CASE WHEN id<=87 THEN 'A' WHEN id<=118 THEN 'B' WHEN id<=124 THEN 'C'
         WHEN id<=157 THEN 'D' WHEN id<=221 THEN 'E' ELSE 'F' END as period,
    CASE WHEN exit_signal LIKE 'network_dump%' THEN 'network_dump'
         WHEN exit_signal LIKE 'trail_stop%' THEN 'trail_stop'
         WHEN exit_signal LIKE 'safety_stop%' THEN 'safety_stop'
         ELSE COALESCE(exit_signal, 'OPEN') END as signal,
    COUNT(*), ROUND(AVG(virtual_profit_pct)::numeric, 1) as avg_profit,
    ROUND(100.0 * COUNT(*) FILTER (WHERE virtual_profit_pct > 0) /
        NULLIF(COUNT(*) FILTER (WHERE virtual_profit_pct IS NOT NULL), 0)::numeric, 0) as win_pct
FROM bot_network.phantom_trades
GROUP BY 1, 2 ORDER BY 1, 3 DESC;
```

### Pre-entry pool_trades analysis for phantom pools
```sql
WITH pre AS (
    SELECT pt.id, pt.exit_signal, pt.virtual_profit_pct, pt.entry_pool_sol,
           COUNT(DISTINCT CASE WHEN ptr.is_network_related AND ptr.direction='buy' THEN ptr.trader_address END) as net_buyers,
           COUNT(DISTINCT CASE WHEN NOT ptr.is_network_related AND ptr.direction='buy' THEN ptr.trader_address END) as org_buyers,
           SUM(CASE WHEN ptr.is_network_related AND ptr.direction='buy' THEN ptr.sol_amount ELSE 0 END) as net_sol,
           SUM(CASE WHEN NOT ptr.is_network_related AND ptr.direction='buy' THEN ptr.sol_amount ELSE 0 END) as org_sol
    FROM bot_network.phantom_trades pt
    JOIN bot_network.pool_trades ptr ON ptr.pool_address = pt.pool_address
        AND ptr.seconds_since_creation <= pt.entry_sec_since_creation
    WHERE pt.id > 221 AND pt.virtual_profit_pct IS NOT NULL
    GROUP BY pt.id, pt.exit_signal, pt.virtual_profit_pct, pt.entry_pool_sol
)
SELECT * FROM pre ORDER BY id;
```

### Data collection command
```bash
cd /home/yokinaboy/sniper/scamnet/app && npx tsx scripts/collect-pool-data.ts --limit 200
```
