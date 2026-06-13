---
name: browser-qa
description: ECC-adapted browser verification skill for React/Vite UI, routing, forms, responsive layout, and Mini App flows.
---

# Browser QA

Use this skill when the user reports a visible UI bug or the task changes routing, layout, forms, auth/session UX, dashboards, Mini App screens, or game surfaces.

## Workflow

1. Identify the route, component, state, fixture, and server/API dependency that owns the visible behavior.
2. Run unit/component checks first if the repo has them.
3. Start or reuse the local dev/runtime only after verifying who owns the ports.
4. Open the real route with Playwright or the repo's e2e/smoke command.
5. Check desktop and mobile widths, especially 320-390px.
6. Interact with the actual controls: click, keyboard tab/enter/escape, submit, cancel, disabled/loading/error paths.
7. Capture evidence through test output, screenshot path, HTTP response, or console/log result.

## UI Review Checklist

- semantic controls instead of clickable `div`/`span`
- visible focus state and keyboard reachability
- stable dimensions for toolbars, boards, cards, counters, and tiles
- no text overflow, overlap, or clipped labels
- loading, empty, error, permission-denied, and disabled states are present where needed
- route/state derives from the server-owned read model when the feature has one

## Completion Standard

Do not say a visible UI issue is fixed without either browser proof or a clear explanation of why browser proof was not feasible.

