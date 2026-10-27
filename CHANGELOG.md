# Changelog

## Unreleased

- Archived Open Design as a historical stage; removed it from active skill
  selection, bundles, installers, MCP projections and runtime routing while
  retaining general design, web-development and media skills.
- Separate malformed reporting from product defects; allow successive isolated report corrections within the approved budget with preserved evidence and duplicate-response detection.
- Add state-bound mission continuation and collection of manually reviewed reports without another model launch; retain required product proof and independent review.
- Reserve model budget for required review and enabled report recovery before dispatch.
- Roll back deployed skill trees when final configuration retirement fails, including a failure after the retirement rename.

## 3.0.0-rc.3 — 2026-10-21

- Clarified the installed instruction template: Luna handles simple, routine, low-risk work; `high` and `xhigh` are reasoning effort settings, not task-complexity requirements. Increasing effort never permits Luna to take work reserved for Sol.
- Corrected the routing reference example to use `complexity=low` with Luna and removed obsolete Luna `medium` effort guidance.
- Synchronized product version metadata across the native kits and installer readback expectation; native kit API versions remain `1.0.0`.
- Recorded that live acceptance remains on rc.2. The rc.3 Hermes update is pending reconciliation of an existing modified orchestration skill; the installer preserves that local change.

## 3.0.0-rc.2 — 2026-10-20

- Fixed bounded Gateway stdout capture after an oversized frame: later chunks no longer grow the incomplete receipt beyond `MAX_FRAME_BYTES + 65536`.
- Revalidated the v3 Gateway, routing, skill surface, installer fixtures, Open Design, and Python regression gates.
- Completed the live Codex → Claude → Hermes rollout with installed hash/mode readback and rollback artifacts.
- Verified a real-provider no-write Gateway canary with controller acceptance and proof.
