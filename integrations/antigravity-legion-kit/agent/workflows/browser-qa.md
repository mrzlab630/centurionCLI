---
description: Verify browser-visible React/Vite behavior with real route checks and responsive proof.
---

# Browser QA Workflow

1. Identify route/component/state owner and test fixture.
2. Verify runtime ownership before starting or restarting dev servers.
3. Run the closest unit/component/e2e command.
4. Use Playwright or the repo's browser smoke for the affected route.
5. Check desktop and mobile 320-390px widths.
6. Verify keyboard focus, loading, empty, error, disabled, and success paths when applicable.
7. Report evidence: command result, URL, screenshot path, console/log findings, or exact reason browser proof was not run.

