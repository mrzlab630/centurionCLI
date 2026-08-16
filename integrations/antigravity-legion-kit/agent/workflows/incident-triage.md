---
description: Evidence-first incident triage for runtime, API, DB, worker, provider, browser, and process-manager failures.
---

# Incident Triage Workflow

1. Capture symptom, time window, affected user path, and recent changes.
2. Check branch/dirty state and local instructions.
3. Identify process/runtime ownership before changing state.
4. Inspect health endpoints and logs with secret redaction.
5. Classify layer: browser, API, DB, worker/queue, provider, process manager, proxy, host/network.
6. Test one root-cause hypothesis at a time.
7. Apply the smallest evidence-backed fix.
8. Prove recovery with the failing path plus health/log/process evidence.
9. Write a short incident report with follow-up prevention.
