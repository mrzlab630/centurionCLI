---
description: Analyze whether tests cover changed behavior, branches, and failure paths.
---

# Test Coverage Workflow

1. Identify changed behavior, not just changed files.
2. Locate existing tests and their framework from package scripts/config.
3. Check happy path, edge cases, error paths, authorization failures, and regression coverage for the reported bug.
4. Prefer behavior-focused assertions over snapshots or no-throw tests.
5. Run focused tests first, then the broader repo gate when feasible.
6. Report critical gaps separately from nice-to-have coverage improvements.

