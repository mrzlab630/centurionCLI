# Calibrated Thresholds & Parameters

> Each threshold tracks: value, calibration date, sample size, method, confidence.
> Updated by AUGUR as more data becomes available.

## Strategy Parameters

| Parameter | Value | Date | N | Method | Confidence |
|---|---|---|---|---|---|
| time_stop_seconds | 15 | 2026-03-05 | 46 | Grid search (60 combos) | MEDIUM |
| take_profit_virtual_growth_pct | 15% | 2026-03-05 | 46 | Grid search | MEDIUM |
| stop_loss_pct | 30% | default | - | DB default | LOW |
| organic_window_seconds | 2 | 2026-03-05 | 46 | Grid search | MEDIUM |
| partial_sell_at_tp_pct | 70% | 2026-03-05 | 46 | Simulation | MEDIUM |
| trailing_remainder_pct | 30% | 2026-03-05 | 46 | Simulation | MEDIUM |
| trailing_drop_stop_pct | 8% | 2026-03-05 | 46 | Simulation | MEDIUM |

## Detection Thresholds

| Parameter | Value | Date | N | Method | Confidence |
|---|---|---|---|---|---|
| z_score_anomaly | > 3.0 | - | - | Statistical standard | HIGH |
| entropy_flash_rug | < 0.5 | 2026-03-05 | 93 | Protocol A batch | HIGH |
| entropy_pump_dump | > 2.0 | 2026-03-05 | 93 | Protocol A batch | HIGH |
| ofi_exit_signal | crosses 0 (pos→neg) | 2026-03-05 | 93 | OFI trajectory | MEDIUM |
| ofi_initial_pump_dump | +0.41 (0-5s window) | 2026-03-05 | 93 | OFI baselines | MEDIUM |
| benford_p_value | < 0.01 | 2026-03-05 | 93 | Chi-squared test | HIGH |
| benford_digit9_anomaly | > 15% (vs 4.6% expected) | 2026-03-05 | 93 | Batch analysis | HIGH |
| organic_hit_min_traders | > 50 | 2026-03-05 | 4 | Heuristic | LOW |
| organic_hit_organic_ratio | > 90% | 2026-03-05 | 4 | Heuristic | LOW |
| co_occurrence_min_pools | >= 3 | TBD | - | [HYPOTHESIS] | LOW |
| cusum_drift | TBD | - | - | Needs calibration | NONE |
| cusum_threshold | TBD | - | - | Needs calibration | NONE |

## Pool Classification Thresholds

| Classifier | Condition | Date | N | Confidence |
|---|---|---|---|---|
| flash_rug | organic_buyers == 0 AND entropy < 0.5 | 2026-03-05 | 93 | HIGH |
| pump_dump | organic_buyers > 0 AND entropy > 2.0 | 2026-03-05 | 93 | HIGH |
| organic_hit | traders > 50 AND organic_ratio > 90% AND peak > 10 SOL | 2026-03-05 | 4 | LOW |
| profitable_entry | position >= 50% of sec=0 trades | 2026-03-05 | 46 | MEDIUM |

## Z-Score Velocity Baselines (for anomaly detection)

| Type | Trades/5s (μ±σ) | SOL/5s (μ±σ) | Wallets/5s (μ±σ) |
|---|---|---|---|
| pump_dump | 6.48 ± 7.13 | 3.92 ± 5.64 | 5.60 ± 5.84 |
| unknown | 3.77 ± 3.17 | 1.69 ± 3.07 | 2.40 ± 2.20 |
| flash_rug | 1.95 ± 1.07 | 0.52 ± 1.00 | 1.00 ± 0.00 |

## Bonding Curve Constants

| Constant | Value | Source |
|---|---|---|
| virtual_sol_start | 30 SOL | Pump.fun docs |
| pump_fee_pct | 1% | Pump.fun docs |
| graduation_mcap | ~$69,000 | Pump.fun docs |
| graduation_liquidity | ~$12,000 | Pump.fun docs |

---

## Threshold Changelog

### 2026-03-05: Protocol A batch (N=93) — MAJOR UPDATE
- Entropy thresholds calibrated: <0.5 = flash_rug, >2.0 = pump_dump
- OFI baselines computed for all pool types
- Z-score velocity baselines established (5s windows, first 60s)
- Benford digit 9 anomaly threshold: >15% = bot activity
- Organic hit classification heuristic (LOW confidence, needs more data)
- Kaplan-Meier survival: 51.6% pools peak within 5s, 67% within 15s

### 2026-03-05: Initial calibration (N=46)
- Grid search: orgWindow=2s, timeStop=15s, TP=15%
- Results: 78% win rate (at ideal sec=0 entry)
- CENSOR warning: results only valid at sec=0 entry

---

*Last updated: 2026-03-05 (Protocol A, N=93) | Recalibrate at: 100 pools*
