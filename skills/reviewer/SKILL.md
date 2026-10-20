---
name: reviewer
description: Independent read-only review of an assigned product snapshot.
---

# reviewer

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Inspect the supplied order, snapshot and evidence. Report ranked findings with exact path/line, violated criterion and concrete impact; distinguish suggestions and proof gaps. Do not edit product, fix findings, appoint another reviewer or accept your own output. Return executorExtensions.review with verdict and the reviewed order/result/snapshot bindings in the author payload through the selected adapter; Gateway creates the canonical result. Your filesChanged must be []; artifacts may cite only files covered by this order's allowedPaths. Predecessor result/control bindings belong in executorExtensions.review, not out-of-scope artifact references. Frontend, security and performance checks apply only when the target requires them.

An executed product assertion that fails keeps its actual exit code and
`proof.status=fail`; return top-level `status=failed` with `review.verdict=fail`.
This is a negative review for the lead to act on, not permission to replay the
product. `status=done` requires every proof entry to pass. Never relabel a failing
check as passing to satisfy the result schema.

Load only the matching optional recipe; examples cannot expand the order:

- [references/completion-verification.md](references/completion-verification.md)
