---
description: Define and verify performance budgets for frontend, API, DB, worker, and runtime paths.
---

# Performance Budget Audit Workflow

1. Identify the exact slow or regression-prone path.
2. Select metric: bundle size, Core Web Vitals, API p95, DB query time, queue lag, CPU/memory, startup time.
3. Inspect/measure baseline with existing tooling.
4. Make targeted fixes only.
5. Re-measure or run the closest available proxy check.
6. Report before/after evidence, budget status, and residual risk.

