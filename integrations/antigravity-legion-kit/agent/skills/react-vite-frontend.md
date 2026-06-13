---
name: react-vite-frontend
description: React/Vite/TypeScript implementation and review playbook adapted from ECC frontend, React, Vite, accessibility, and testing skills.
---

# React Vite Frontend Skill

## Use When

- editing `.tsx`, `.jsx`, CSS, routing, forms, or component state
- changing `vite.config.*`, `tsconfig*`, Vitest, Playwright, or ESLint config
- fixing layout, accessibility, rendering, or performance issues

## Implementation Checklist

- inspect existing components and CSS tokens before creating new patterns
- keep component state local unless multiple distant branches truly need it
- prefer composition and props over inheritance or global state
- use accessible controls and labels by default
- validate form inputs with the repository's existing schema/validation layer
- avoid premature memoization; measure or justify `memo`, `useMemo`, and `useCallback`
- use skeleton/empty/error states for async surfaces

## Review Checklist

- hook order and dependency correctness
- direct state mutation
- stale closures and missing cleanup
- unsafe `dangerouslySetInnerHTML` or unvalidated URLs
- `VITE_*` secret leakage
- form labels, ARIA usage, focus management, keyboard access
- responsive width and no horizontal scroll
- component tests use user-visible behavior, not internals

## Default Proof

Use project scripts, usually:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

Run Playwright/e2e only when the task affects browser flows, routing, responsive layout, or auth/session behavior.

