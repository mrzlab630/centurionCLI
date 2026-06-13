---
name: performance-budget
description: Define and audit frontend, API, database, worker, and runtime performance budgets without blind optimization.
---

# Performance Budget

Use when performance is a feature, when a change risks latency/bundle regressions, or when the user reports slowness.

## Budgets To Consider

- frontend bundle size and route-level lazy loading
- Core Web Vitals and layout shift
- API p95 latency and error rate
- database query time and index usage
- worker queue lag and retry rate
- memory/CPU under sustained runtime
- startup/restart time for dev/prod services

## Workflow

1. Identify the user-facing or operator-facing performance path.
2. Choose the smallest meaningful metric.
3. Inspect or measure before changing.
4. Fix the bottleneck, not the nearest code smell.
5. Re-measure or run a focused proxy check.
6. Report before/after evidence and remaining risk.

