---
description: Review React/Vite/TypeScript changes for correctness, accessibility, performance, security, and test coverage.
---

# React Review Workflow

1. Determine changed `.tsx`, `.jsx`, `.ts`, CSS, route, test, and Vite/config files.
2. Run typecheck and lint where available.
3. Review React-specific risks: hooks, state, effects, accessibility, rendering, responsive layout.
4. Review TypeScript risks: `any`, unsafe casts, missing boundary validation, async errors.
5. Review Vite/security risks: `VITE_*` secrets, sourcemaps, public env values.
6. Report findings first, ordered by severity with file references.
