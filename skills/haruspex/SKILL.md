---
name: haruspex
description: Static vulnerability candidate triage in authorized source paths.
---

# haruspex

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Use scripts/scan_code.py as a regex-based candidate finder, not a complete SAST verdict. Trace the sink, source, guards and reachability in code. Return evidence and false-positive limits; exploit execution requires separate trusted authorization.
