# Model Performance Tracking

> Log every model/strategy test here. Track improvement over time.

## Performance Log

| Date | Model/Strategy | Dataset | Win Rate | Avg Profit | Med Profit | Notes |
|---|---|---|---|---|---|---|
| 2026-03-05 | Ideal entry (peak exit) sec=0 | 93 pools | 89% | +42.5% | +7.3% | Theoretical max (assumes exit at peak) |
| 2026-03-05 | Ideal entry (peak exit) sec=1 | 93 pools | 69% | +38.9% | +5.3% | Theoretical max |
| 2026-03-05 | Ideal entry (peak exit) sec=2 | 93 pools | 67% | +35.7% | +9.2% | Theoretical max |
| 2026-03-05 | Ideal entry (peak exit) sec=3 | 93 pools | 81% | +14.4% | +11.6% | Theoretical max |
| 2026-03-05 | Grid Search v1 (realistic, sec=0) | 46 pools | 78% | - | - | orgWindow=2s, timeStop=15s, TP=15% |
| 2026-03-05 | Grid Search v1 (realistic, sec=1) | 46 pools | 20% | -1.05% | - | UNPROFITABLE with realistic exits |
| 2026-03-05 | Grid Search v1 (realistic, sec=2) | 46 pools | 20% | -0.47% | - | UNPROFITABLE with realistic exits |

## Key Insight: Theoretical vs Realistic
**WARNING**: Theoretical max (exit at peak) gives wildly optimistic numbers.
With N=93 (includes organic hits like GRf3Dwo5=+291%): sec=0 shows 89% win, +42.5% avg.
With N=46 (realistic time-stop/TP exits): sec=1 shows 20% win, -1.05% avg.
Difference = organic hits skew averages. Use MEDIAN, not MEAN for decision-making.

## Baselines (to beat)

| Method | Metric | Value | Date | N |
|---|---|---|---|---|
| Random (coin flip) | Win Rate | 50% | theoretical | - |
| Always-buy-sec=0 (peak exit) | Win Rate | 89% | 2026-03-05 | 93 |
| Realistic sec=0 (grid search) | Win Rate | 78% | 2026-03-05 | 46 |

## Feature Importance (Spearman Correlation with peak_sol, N=93)

| Rank | Feature | rho | p-value | Significance |
|---|---|---|---|---|
| 1 | unique_traders | 0.888 | <0.0001 | *** |
| 2 | network_sell_sol | 0.693 | <0.0001 | *** |
| 3 | network_buy_sol | 0.669 | <0.0001 | *** |
| 4 | initial_sol | -0.340 | 0.0009 | *** |
| 5 | first_sell_delay | -0.238 | 0.021 | * |
| 6 | time_to_peak | 0.220 | 0.034 | * |

## Entropy as Classifier (N=93)

| Threshold | Correctly classifies |
|---|---|
| entropy < 0.5 | flash_rug or wash_trading (100% precision) |
| entropy > 2.0 | pump_dump (high confidence) |
| entropy 0.5-2.0 | ambiguous zone (unknown, slow_rug) |

---

*Last updated: 2026-03-05 (Protocol A batch, N=93)*
