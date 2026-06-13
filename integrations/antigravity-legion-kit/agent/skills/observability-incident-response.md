---
name: observability-incident-response
description: Triage incidents and runtime failures with evidence-first logs, health checks, process ownership, root cause, proof, and follow-up prevention.
---

# Observability Incident Response

Use when the user reports downtime, broken runtime, bad deploy, suspicious logs, stuck worker, failed provider, database issue, browser-visible outage, or asks for WAR ROOM incident handling.

## Triage Order

1. Preserve context: current branch, dirty tree, recent changes, user-reported symptom, exact time window.
2. Identify layer: browser, API, DB, worker/queue, provider, process manager, proxy, host/network.
3. Inspect owners before action: processes, ports, PM2/tmux/systemd/Docker where relevant.
4. Inspect health and logs with redaction discipline.
5. Form one root-cause hypothesis and test it.
6. Apply the smallest fix or restart that matches the evidence.
7. Prove recovery with the failing path, health endpoint, logs, and process/port state.

## Incident Report Format

- symptom
- impact
- timeline
- evidence collected
- root cause
- fix applied
- proof of recovery
- follow-up prevention

