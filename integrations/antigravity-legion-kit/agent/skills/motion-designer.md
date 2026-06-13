---
name: motion-designer
description: Accessible, performance-safe UI motion direction for React/Vite interfaces and Mini Apps.
---

# Motion Designer

Use only when motion improves comprehension or interaction.

## Motion Must Do One Of These

- guide attention
- communicate state
- preserve spatial continuity

If it does none, remove it.

## Rules

- Respect `prefers-reduced-motion`.
- Animate transform and opacity, not layout properties.
- Keep UI feedback fast: button/icon feedback should feel immediate.
- Entrance and exit states should both be defined for conditional UI.
- Do not run infinite animations in ways that waste CPU/GPU.
- Do not introduce a new motion dependency unless the project already uses one or the benefit is clear.
- If using Motion for React, do not mix `motion/react` and `framer-motion` imports in the same project.

## Review Targets

- motion that hides sluggishness instead of fixing it
- animation that causes text/control overlap
- layout shift during loading or state changes
- missing reduced-motion fallback
- excessive stagger delays or decorative reveal sequences

