---
name: design-system-auditor
description: Audit and improve design-system consistency: tokens, colors, typography, spacing, components, states, dark mode, and AI-slop patterns.
---

# Design System Auditor

Use when a UI feels inconsistent, generic, visually noisy, hard to scan, or when a PR touches styling/components.

## Audit Areas

Score and report concrete examples for:

- color consistency and semantic usage
- typography hierarchy and line height
- spacing rhythm and layout density
- border radius, borders, shadows, and surface layering
- component consistency and duplicated patterns
- responsive behavior at mobile and desktop widths
- dark mode completeness where applicable
- interaction states: hover, active, focus, disabled, loading, error, empty, success
- accessibility: contrast, labels, keyboard, focus, touch targets
- AI-slop signals: generic gradients, decorative blobs, needless glass, oversized cards, vague hero copy

## Output Contract

Return findings with file references where possible, prioritized fixes, and a small token/component action plan. Do not propose a full redesign when local component cleanup is enough.

