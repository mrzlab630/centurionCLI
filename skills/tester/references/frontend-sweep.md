# Frontend Sweep Protocol

Use this reference when TESTER verifies frontend/UI work after PICTOR implementation.

## Ownership

- Primary owner: TESTER.
- Fix owner: PICTOR.
- UX ambiguity: AEDILIS.
- Copy/CTA issue: NOMENCLATOR.
- SEO issue: INDAGATOR.
- Security issue: GUARDIAN.

TESTER does not redesign or implement UI. TESTER proves what fails and routes fixes.

## Minimum Sweep

1. Confirm the app owner and running URL.
2. Detect available commands: lint, test, build, Playwright/e2e.
3. Plan browser checks with `integrations/claude-legion-kit/scripts/frontend-sweep-plan.mjs`.
4. Check at least 320, 768, 1440, and 1920px for touched screens.
5. Verify loading, empty, error, and success states for the touched flow when reachable.
6. Capture console/runtime/hydration errors.
7. Check keyboard navigation and visible focus on primary controls.
8. Run accessibility checks if the project already has Playwright/axe or equivalent.

## Reject Conditions

- Horizontal scroll at 320px.
- Text overlap, clipped labels, or controls that cannot be read/clicked.
- Primary flow has uncaught console/runtime errors.
- Critical accessibility violation on a touched screen.
- Missing state coverage without a documented blocker.
- Claim of visual correctness without screenshot, DOM, or browser evidence.

## Report Shape

```yaml
frontend_sweep:
  owner: TESTER
  url: "http://localhost:3000"
  commands:
    - command: "npm run build"
      result: "passed|failed|blocked"
  viewports:
    - width: 320
      result: "passed|failed|blocked"
      evidence: "path-or-summary"
  issues:
    - severity: "critical|major|minor"
      owner: "PICTOR|AEDILIS|NOMENCLATOR|INDAGATOR|GUARDIAN"
      evidence: "file:line, screenshot, console line, or selector"
      fix_gate: "command or browser check"
  remaining_risks: []
```
