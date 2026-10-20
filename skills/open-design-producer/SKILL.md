---
name: open-design-producer
description: Optional Open Design production for an explicitly requested interface task.
---

# open-design-producer

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Use scripts/open-design.mjs with an explicit JSON request and isolated absolute output/result paths. Use a proven configured bridge only when requested; do not install MCP automatically. Inspect returned HTML, screenshot and proof entries, preserving project identity on revision. Result receipts stay outside accepted artifact directories. A visual criterion remains unverified if the reviewer cannot read the image. Cleanup or project deletion follows the exact authorized lifecycle; never infer publication/deletion authority.
