---
description: ECC-adapted creative UI, UX, design-system, accessibility, motion, and brand voice rules.
---

# Creative UI And Design Rules

These rules adapt the useful ECC UI/UX and creativity skills for JavaScript/TypeScript projects under `/home/mrz/projects/js`.

## Design Direction First

Before building or redesigning UI, choose a concrete direction:

- purpose: what job the interface must do
- audience: who repeats this workflow and what they need to scan first
- tone: utilitarian, calm, playful, technical, premium, operational, editorial, or another explicit direction
- memorable detail: one intentional visual or interaction idea
- constraints: existing components, tokens, accessibility, performance, browser/mobile proof

Match the interface to the product. Operational SaaS/admin surfaces should be dense, quiet, and scannable. Games, launch pages, demos, and playful products can be more expressive.

## Anti-Generic UI Rules

- Do not default to purple/blue gradients, decorative blobs, generic centered hero copy, stock-like atmospheric backgrounds, or card-heavy layouts.
- Do not put cards inside cards or style page sections as floating cards.
- Do not use a single hue family for the whole UI unless the existing brand system requires it.
- Do not describe the UI's own features inside the UI when controls can be self-explanatory.
- Do not add a new dependency for a visual flourish unless it clearly improves the product.

## Design System Discipline

- Use existing tokens, components, icon libraries, route patterns, and CSS architecture before creating new patterns.
- Keep spacing on a consistent 4px or 8px rhythm.
- Keep fixed-format UI stable with explicit dimensions, aspect ratios, min/max constraints, and predictable grid tracks.
- Use contextual typography. Hero-scale type belongs only in true hero contexts, not compact dashboards, cards, sidebars, or toolbars.
- Interactive controls need default, hover, active, focus, disabled, loading, error, and success states where applicable.

## Interface Polish

- Use icons for familiar tool actions when an icon library exists.
- Touch/click targets should be at least 40x40px, ideally 44x44px where layout allows.
- Use `font-variant-numeric: tabular-nums` for counters, prices, timers, balances, and changing numeric values.
- Prefer explicit transition properties over `transition: all`.
- Use motion to clarify state, guide attention, or preserve spatial continuity. Remove decorative motion that does none of those.
- Respect `prefers-reduced-motion` and avoid animating layout properties such as width, height, top, left, margin, and padding.
- Text must fit its container on mobile and desktop. No clipped labels, overlapping controls, or horizontal overflow.

## Accessibility Baseline

- Prefer semantic HTML: `button`, `a`, `label`, `form`, `nav`, `main`, `section`, and heading levels that match the document structure.
- Icon-only controls need accessible labels.
- Forms need connected labels, error messages linked with `aria-describedby`, and useful validation text.
- Modals and dialogs need focus containment, Escape close, focus restoration, and `aria-modal` semantics.
- Color must not be the only status signal. Pair color with text, icon, shape, or pattern.
- Text contrast should meet WCAG AA: 4.5:1 for normal text and 3:1 for large text/UI components.

## Creative Output Discipline

- For landing copy, onboarding, empty states, and product text, derive tone from existing project copy before inventing a new voice.
- Prefer specific mechanisms and concrete outcomes over abstract adjectives.
- Keep one primary action per screen or message.
- Use exploratory variants when the goal is creative direction, then choose one direction before implementation.

