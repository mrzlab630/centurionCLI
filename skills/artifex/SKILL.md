---
name: artifex
description: Maintenance-only authoring and validation of explicitly requested skills.
---

# artifex

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Write only the named skill in the authorized staging path. Use scripts/init.js and scripts/validate.js only with explicit isolated targets after checking their output behavior. Creation, global installation and publication each need their own authority.
