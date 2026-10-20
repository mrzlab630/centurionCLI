---
name: error-handler
description: Diagnose and fix an assigned runtime failure.
---

# error-handler

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Reproduce the exact trigger, preserve useful redacted evidence, and connect logs and current code to a testable cause. Apply the smallest authorized correction, then verify the original target in the same run. Warnings alone do not require remediation.

Load only the matching optional recipe; examples cannot expand the order:

- [references/agent-self-debug.md](references/agent-self-debug.md)
