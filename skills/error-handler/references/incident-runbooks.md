# Incident Runbooks — Per-Component

Detailed diagnostic and recovery procedures for each Sniper Bot component.

---

## 1. Solana Node (localhost:8899)

### Symptoms
- RPC calls timeout or refuse connection
- `getSlot` returns error
- PM2 processes fail with "connection refused"

### Diagnosis
```bash
# Is validator running?
pgrep -a agave-validator || echo "VALIDATOR NOT RUNNING"

# Check RPC
curl -s localhost:8899 -X POST -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' | jq .

# Check Geyser gRPC
grpcurl -plaintext localhost:10000 list 2>&1 | head -5

# Check disk space (validator needs lots)
df -h /opt/solana/

# Check validator logs (last errors)
journalctl -u sol -n 50 --no-pager | grep -i "error\|panic\|crash"
```

### Common Fixes
| Issue | Fix |
|---|---|
| Validator not running | `sudo systemctl start sol` |
| Disk full | Clear old snapshots: `ls -la /opt/solana/validator-ledger/snapshot-*` |
| Missing flag | Check `/opt/solana/validator.sh` for `--enable-accounts-disk-index` (required since v3.1.x) |
| Bank hash mismatch | Need fresh snapshot: stop → delete ledger → restart with `--no-snapshot-fetch` removed |
| Geyser plugin crash | Check `/opt/solana/yellowstone-grpc-config.json` → account_include_max=250 |

### Known Issues (from MEMORY.md)
- v3.1.9 REQUIRES `--enable-accounts-disk-index` (was optional in v3.0.14)
- Geyser is READ-ONLY — cannot cause bank hash mismatch
- Node failure root cause was validator software bug, NOT ScamNet load

---

## 2. PostgreSQL

### Symptoms
- Prisma errors "connection refused" or "too many clients"
- Queries timeout
- Data inconsistency

### Diagnosis
```bash
# Is PG running?
pg_isready

# Connection count
psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Long-running queries (>10s)
psql -c "SELECT pid, now()-query_start AS duration, query FROM pg_stat_activity WHERE state='active' AND now()-query_start > interval '10 seconds';"

# Database size
psql -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC;"

# Table sizes (analytics schema)
psql -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables WHERE schemaname='bot_network' ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;"
```

### Common Fixes
| Issue | Fix |
|---|---|
| Too many connections | Check pool settings, kill idle: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle' AND query_start < now() - interval '10 minutes';` |
| Slow queries | Check `EXPLAIN ANALYZE`, add missing index |
| Disk full | `VACUUM FULL` on large tables, check WAL archiving |
| Missing column/default | ALTER TABLE with DEFAULT (see last_activity_at incident) |

### Known Issues
- `last_activity_at` NO DEFAULT → Prisma crash (FIXED: ALTER DEFAULT NOW())
- 6 CRITICAL Prisma schema mismatches (non-nullable + no DB default)

---

## 3. PM2 Processes

### Process Map
| PM2 ID | Name | Role |
|---|---|---|
| 2 | snorter_tg_bot | Telegram Bot |
| 3 | walletsWatcherListener | Legacy Listener |
| 4 | walletsWatcherProcessor | Non-Jito Copy-Trading |
| 5 | walletsWatcherListenerGeyserGrpc | Geyser Listener |
| 7 | walletsWatcherProcessorJito | Jito Processor |
| 8 | scamnet-tracker | ScamNet Tracker |

### Diagnosis
```bash
# Overview
pm2 list

# Specific process details
pm2 describe <id>

# Restart count (high = crash loop)
pm2 jlist | jq '.[] | {name: .name, restarts: .pm2_env.restart_time, status: .pm2_env.status}'

# Memory usage
pm2 jlist | jq '.[] | {name: .name, memory: (.monit.memory / 1048576 | floor | tostring + " MB")}'

# Recent errors for process
tail -100 logs/errs_*<name>*-<id>.log
```

### Common Fixes
| Issue | Fix |
|---|---|
| Process stopped | `pm2 restart <id>` |
| Crash loop (high restarts) | Check error log, fix root cause, then restart |
| OOM (memory growing) | Check for unbounded arrays/maps, add cap. Restart. |
| All processes down | `pm2 resurrect` or re-run ecosystem config |

### Known Issues
- ScamNet fire-and-forget creates unbounded async → serial queue fix
- registeredPools/pendingAddresses cleanup was DISABLED → timer re-enabled
- tokenAccountCache unbounded → capped at 5000

---

## 4. ScamNet (PM2 id:8)

### Symptoms
- No new addresses discovered
- Pool detection stopped
- TG notifications stopped

### Diagnosis
```bash
# Status
pm2 describe 8 | grep -E 'status|restarts|memory'

# Recent activity
tail -50 logs/out_scamnet_tracker-8.log | grep -E 'NEW|POOL|BANK|address'

# Error count
grep -c "ERROR\|Error\|error" logs/errs_scamnet_tracker-8.log

# DB health
psql -c "SELECT COUNT(*) as addresses FROM bot_network.addresses;"
psql -c "SELECT classification, COUNT(*) FROM bot_network.addresses GROUP BY classification ORDER BY 2 DESC;"
psql -c "SELECT COUNT(*) as pools FROM bot_network.pool_analyses;"

# Geyser connection (is it receiving data?)
tail -20 logs/out_scamnet_tracker-8.log | grep -i "geyser\|subscribe\|slot"
```

### Common Fixes
| Issue | Fix |
|---|---|
| Geyser disconnect | Restart ScamNet: `pm2 restart 8`. Check node Geyser plugin. |
| No addresses | Check garbage filter threshold (3+ TX). Check Geyser filters count. |
| Memory growing | Check pendingAddresses cap (10K), registeredPools cap (1000) |
| Build error | `cd /home/yokinaboy/sniper/scamnet/app && npm run build && pm2 restart 8` |

---

## 5. Copy-Trading (PM2 id:4,5,7)

### Symptoms
- Trades not copying
- Delays in execution
- "Insufficient balance" errors

### Diagnosis
```bash
# All 3 processes
for id in 4 5 7; do echo "=== PM2:$id ===" && pm2 describe $id | grep -E 'status|restarts|memory'; done

# Geyser listener (id:5) — is it receiving signals?
tail -30 logs/out_*walletsWatcherListenerGeyserGrpc-5.log | grep -i "signal\|trade\|swap"

# Jito processor (id:7) — is it executing?
tail -30 logs/out_*walletsWatcherProcessorJito-7.log | grep -i "execute\|bundle\|swap"

# Non-Jito processor (id:4) — BullMQ workers
tail -30 logs/out_*walletsWatcherProcessor-4.log | grep -i "worker\|process\|swap"

# Error patterns
tail -100 logs/errs_*walletsWatcherProcessorJito-7.log | grep -c "Insufficient\|timeout\|error"

# Redis (copy-trading signals)
redis-cli keys "copy_trading:*" | head -10
```

### Common Fixes
| Issue | Fix |
|---|---|
| Geyser not receiving | Restart listener: `pm2 restart 5`. Check node Geyser. |
| Jito bundle failing | Check Jito endpoint, tip amount, blockhash freshness |
| Insufficient balance | Low Balance Pause system (3 fails → 5 min pause). Check wallet SOL. |
| BullMQ stuck | Check Redis connection. `pm2 restart 4`. |

---

## 6. Telegram Bot (PM2 id:2)

### Diagnosis
```bash
pm2 describe 2 | grep -E 'status|restarts|memory'
tail -50 logs/errs_snorter_tg_bot_index-2.log
tail -50 logs/out_snorter_tg_bot_index-2.log | grep -i "error\|webhook\|polling"
```

### Common Fixes
| Issue | Fix |
|---|---|
| Bot unresponsive | `pm2 restart 2` |
| Webhook conflict | Delete webhook: `curl "https://api.telegram.org/bot$TOKEN/deleteWebhook"` then restart |
| Build error | `cd /home/yokinaboy/sniper/telegram/base && npm run build && pm2 restart 2` |

---

## 7. Redis

### Diagnosis
```bash
redis-cli ping
redis-cli info memory | grep -E "used_memory_human|maxmemory"
redis-cli info clients | grep connected
redis-cli dbsize
```

### Common Fixes
| Issue | Fix |
|---|---|
| Not running | `sudo systemctl start redis` |
| Memory full | Check maxmemory policy, flush expired keys |
| Too many connections | Check client list: `redis-cli client list` |
