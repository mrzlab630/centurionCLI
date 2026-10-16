---
name: velites
description: Targeted reconnaissance only for explicitly authorized hosts and interfaces.
---

# velites

Follow [the functional contract](../orchestrator/SKILL.md). This recipe grants no
additional authority; use it only for the assigned task.

Use scripts/recon.py for the bounded port/header/file probes actually approved. Record target/interface, command, time and results. Open ports and HTTP responses are fingerprints, not vulnerability or host-identity proof. Do not expand target ranges or execute exploits.
