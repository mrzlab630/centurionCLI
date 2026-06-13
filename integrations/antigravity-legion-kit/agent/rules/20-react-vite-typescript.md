---
description: Global React, Vite, and TypeScript engineering rules for Antigravity.
---

# React + Vite + TypeScript Rules

## TypeScript

- Prefer precise types over `any`; use `unknown` plus narrowing at external boundaries.
- Do not weaken `tsconfig` strictness to make a change pass.
- Public functions, API DTOs, schemas, and exported utilities should have explicit types.
- Runtime inputs must be validated at boundaries with the repository's existing schema/validation library.

## React

- Render must remain a pure function of props and state.
- Do not store derived state in `useEffect`; derive during render unless there is a measured reason.
- Use effects only for external synchronization: network, subscriptions, timers, DOM integration.
- Clean up listeners, intervals, subscriptions, and abortable fetches.
- Do not suppress `react-hooks/exhaustive-deps` without a nearby justification.
- For `.tsx` changes, review both React-specific issues and generic TypeScript issues.

## Vite

- `vite build` is not enough by itself; run the project typecheck as a separate gate unless the build script already runs it.
- Only public values may use `VITE_*`. API tokens, private keys, database URLs, bot tokens, and service credentials must stay server-side.
- Prefer the project's pinned package manager and scripts over ad hoc `npx` installs.
- Keep production source maps disabled unless a configured error tracker consumes them and artifacts are not publicly served.

## UI Implementation

- Use the project's existing component layer and design tokens first.
- Semantic HTML first: use `button`, `a`, `label`, `form`, `nav`, `main` instead of clickable `div`/`span`.
- Every interactive control needs default, hover, active, disabled, loading, error, and focus states where applicable.
- Verify mobile width around 320-390px when changing layout.
- Avoid raw inline styles when the project has a shared CSS/token system.

## Tests

- For React component tests, prefer user-visible behavior and accessible queries: role, label, text.
- Use Playwright only for browser/user journeys, routing, layout, auth, or integration behavior that unit tests cannot prove.
- Bug fixes should add a regression test when the failure can be reproduced locally.

