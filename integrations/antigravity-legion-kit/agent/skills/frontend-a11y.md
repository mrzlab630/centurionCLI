---
name: frontend-a11y
description: Practical accessibility skill for React/Vite UI: semantic HTML, ARIA, labels, keyboard navigation, focus management, contrast, forms, and dialogs.
---

# Frontend Accessibility

Use for every interactive UI component, form, modal, dropdown, tab set, menu, dashboard control, or icon-only action.

## Web Baseline

- Prefer native semantics before ARIA.
- `button` for actions, `a` for navigation, `label` linked to form fields.
- Icon-only buttons need accessible names.
- Errors should be text-based and linked to inputs with `aria-describedby`.
- Use `aria-invalid` only when an input is actually invalid.
- Dynamic status changes should use a polite live region when the status matters.
- Keyboard users must be able to reach and operate every interactive element.
- Modals must contain focus, close on Escape, and restore focus to the trigger.
- Do not use color alone for status.
- Verify focus indicators and contrast.

## Review Targets

- clickable `div`/`span`
- missing labels or disconnected errors
- wrong heading order
- missing `alt` text or redundant alt text
- `target="_blank"` without `rel="noopener noreferrer"`
- custom controls without keyboard support
- focus traps or focus loss after closing UI
