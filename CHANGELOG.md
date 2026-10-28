# Changelog

## 3.0.0-rc.6 — 2026-10-28

- Prepare the local Codex, Claude and Hermes rollout of the rc.5 user-authority
  policy. Runtime behavior is unchanged from rc.5; synchronize product metadata
  while keeping native kit API versions at `1.0.0`.
- Preserve local instruction additions and selected design/web/media skills;
  Open Design stays archived. Rollout evidence is recorded after installed
  readback and Gateway verification.

## 3.0.0-rc.5 — 2026-10-28

- Make user authority decisive: risk, defect history and review advice do not veto
  the approved verification profile; retire V3's verifier and specialist gate.
- Remove Astra's residual downstream review floor and false V3 authority blockers;
  bind dispatch to the user's selected profile with V2/V3 compatibility.
- Warn about repeated Claude reads and historical tool denials without killing
  the worker or rejecting otherwise proven output; preserve warnings in Gateway
  evidence and avoid repeating them when collecting accepted results.
- Make no-progress and coverage-regression heuristics advisory. Remove the fixed
  one-switch strategy limit while preserving scope and cumulative attempt budgets.
- Let recorded owner continuation extend unfinished tasks' product-attempt budgets
  without resetting counters, rewriting evidence or replaying completed work.
- Align active instructions and routing documentation with the user-authority
  doctrine. Keep required-check outcomes, cancellation, custody and actual host
  permissions explicit; preserve Open Design as an archive.
- Verify local Gateway/lifecycle regressions and isolated native-kit installation;
  source publication does not imply rc.5 deployment or a fresh provider inference.

## 3.0.0-rc.4 — 2026-10-28

- Archived Open Design as a historical stage; removed it from active skill
  selection, bundles, installers, MCP projections and runtime routing while
  retaining general design, web-development and media skills.
- Separate malformed reporting from product defects; allow successive isolated report corrections within the approved budget with preserved evidence and duplicate-response detection.
- Add state-bound mission continuation and collection of manually reviewed reports without another model launch; retain required product proof and independent review.
- Reserve model budget for required review and enabled report recovery before dispatch.
- Roll back deployed skill trees when final configuration retirement fails, including a failure after the retirement rename.
- Integrated the project scope-lock and V3 blocker clarifications. Source publication
  does not imply installation into existing client homes or live mission recovery.

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
