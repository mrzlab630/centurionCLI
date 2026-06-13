---
description: Develop non-trivial features by exploring existing code before planning and implementation.
---

# Feature Development Workflow

1. Discovery: restate requirements, constraints, current phase, and acceptance criteria.
2. Exploration: read local docs, package scripts, similar modules, tests, and data/API boundaries.
3. Architecture: produce a blueprint with files, interfaces, data flow, validation gates, and risk decisions.
4. Implementation: build in dependency order and keep edits scoped.
5. Review: run React/TypeScript/security/database/browser review lanes based on touched surfaces.
6. Verification: run focused checks plus the strongest feasible repo gate.
7. Report: files changed, proof, skipped checks, residual risks.

