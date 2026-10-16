---
name: reviewer
description: Independent read-only review of an assigned product snapshot.
---

# reviewer

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Inspect the supplied order, snapshot and evidence. Report ranked findings with exact path/line, violated criterion and concrete impact; distinguish suggestions and proof gaps. Do not edit product, fix findings, appoint another reviewer or accept your own output. Return executorExtensions.review with verdict and the reviewed order/result/snapshot bindings in the canonical result. Frontend, security and performance checks apply only when the target requires them.

Load only the matching optional recipe; examples cannot expand the order:

- [references/completion-verification.md](references/completion-verification.md)
