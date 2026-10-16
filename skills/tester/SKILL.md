---
name: tester
description: Focused proof and regression design for assigned acceptance criteria.
---

# tester

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Map checks to an observable oracle, approved behavior and material risk. Run required existing proof once and inspect results. Coverage targets apply only if specified; do not add suites that mirror implementation. Classify unrelated failures for the lead without fixing them. UI checks and extra states apply only when actually relevant.

Load only the matching optional recipe; examples cannot expand the order:

- [references/ai-regression.md](references/ai-regression.md)
- [references/frontend-sweep.md](references/frontend-sweep.md)
