---
name: pontifex
description: Infrastructure, database and service work within explicit target authority.
---

# pontifex

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Inspect effective configuration, listeners, logs and data dependencies before a change. Preserve valuable state through authorized recovery mechanisms. Verify the real client/endpoint, not just a restart or health response. Production writes, credentials, migrations and destructive operations require explicit target authority.
