---
name: git-master
description: Safe Git operations within explicit branch and history authority.
---

# git-master

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Inspect status, worktrees and branch ancestry first. Preserve dirty changes and unrelated commits. Commit, rebase, reset, push, PR and release operations require the corresponding order; no automatic commit/test/revert cycle. Verify the intended resulting diff and history.

Load only the matching optional recipe; examples cannot expand the order:

- [references/domain-recipes.md](references/domain-recipes.md)
