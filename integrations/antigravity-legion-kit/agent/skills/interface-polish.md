---
name: interface-polish
description: Apply concrete UI polish details: alignment, spacing, radius, shadows, text wrapping, numeric stability, hit areas, icons, and motion scope.
---

# Interface Polish

Use when a component works but feels cramped, flat, jumpy, generic, or unfinished.

## Polish Checklist

- visual hierarchy is obvious without explanatory text
- spacing follows a consistent rhythm
- nested radii are optically coherent
- icon buttons are visually centered and have labels/tooltips where needed
- borders and shadows are used for separation/focus, not decoration everywhere
- text wraps cleanly with no clipping or overlap
- dynamic numbers use tabular numerals
- controls keep stable dimensions across hover/active/loading/error states
- touch targets are at least 40x40px, ideally 44x44px
- transitions list exact properties, never `all`
- motion uses transform/opacity and respects reduced motion

## Output Format

Use before/after rows when reviewing:

| Principle | Before | After |
| --- | --- | --- |
| Text fit | Label overflows on mobile | Label wraps within stable button width |
