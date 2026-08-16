---
description: Plan or verify rollback/recovery for code, process, config, and database changes.
---

# Rollback Check Workflow

1. Identify what changed: code, env, process manager, DB schema/data, dependency, provider config, agent config.
2. Determine whether rollback is safe, forward-only, or requires restore.
3. Record current version/config/process state before action.
4. Define exact rollback or forward-fix command/path.
5. Verify post-rollback health and logs.
6. Report remaining data/config drift.
