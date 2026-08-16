# Accessibility (a11y) — AEDILIS Reference

## Standards

| Standard | Scope | Level |
|---|---|---|
| WCAG 2.1 AA | Baseline for all interfaces | Required |
| WCAG 2.1 AAA | Enhanced (large text, extended contrast) | Aspirational |
| APCA | Perceptual contrast (supplements WCAG) | For data viz |
| Section 508 | US federal | If applicable |
| EAA (EN 301 549) | EU financial products | If applicable |

## Contrast Ratios (WCAG 2.1 AA)

| Element | Minimum Ratio |
|---|---|
| Normal text (<18px / <14px bold) | 4.5:1 |
| Large text (>=18px / >=14px bold) | 3:1 |
| UI components (buttons, inputs, icons) | 3:1 |
| Focus indicators | 3:1 |
| Decorative elements | No requirement |

### Tools
- **WebAIM Contrast Checker** — manual ratio verification
- **axe DevTools** (browser extension) — automated WCAG audit
- **Stark** (Figma plugin) — contrast + colorblind simulation
- **NVDA / VoiceOver / TalkBack** — screen reader manual testing

## Touch Targets

| Platform | Minimum Size |
|---|---|
| Apple (iOS) | 44×44 pt |
| Google (Android) | 48×48 dp |
| Critical actions (Buy/Sell) | 56px+ height |
| Spacing between targets | 8px minimum |

## Keyboard Navigation (Web/Desktop)

- **Tab order** must match visual order (left-to-right, top-to-bottom)
- **Focus indicator:** visible 2px outline, 3:1 contrast against background
- **Skip links:** "Skip to main content" as first focusable element
- **Escape** closes modals, dropdowns, popups
- **Enter/Space** activates buttons and links
- **Arrow keys** navigate within composite widgets (tabs, menus, grids)
- **No keyboard traps** — Tab must always move forward

## Screen Readers

### ARIA Essentials
```html
<!-- Buttons with icons only -->
<button aria-label="Close dialog">✕</button>

<!-- Loading states -->
<div aria-live="polite" aria-busy="true">Loading...</div>

<!-- Dynamic content updates -->
<div aria-live="polite">Portfolio: $1,234.56 (+2.3%)</div>

<!-- Form errors -->
<input aria-invalid="true" aria-describedby="email-error" />
<span id="email-error" role="alert">Invalid email address</span>

<!-- Navigation landmarks -->
<nav aria-label="Main navigation">...</nav>
<main aria-label="Dashboard">...</main>
```

### Common Mistakes
- Image buttons without `aria-label`
- `div` used as button without `role="button"` and `tabindex="0"`
- Dynamic content updates without `aria-live`
- Form errors not programmatically associated with inputs
- Decorative images missing `aria-hidden="true"` or `alt=""`

## Motion & Animation

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- Always check `prefers-reduced-motion` before animations
- Essential animations (loading spinners) can remain but must be subtle
- Never rely on animation to convey information

## Financial App Specific (WCAG 3.3.4)

For financial transactions, at least ONE must be true:
1. **Reversible** — user can undo the action
2. **Checked** — data is validated for input errors before submission
3. **Confirmed** — review step exists before finalizing
4. **Contextual help** — available during the process

### Practical Checklist for Trading UI
- [ ] Profit/Loss: green/red + arrow icon (▲/▼) + numeric sign (+/-)
- [ ] All token symbols have text alternative ("SOL" reads as "Solana")
- [ ] No auto-logout during active trading sessions
- [ ] Error messages: specific, actionable, linked to the field
- [ ] Forms: visible labels (not placeholder-only)
- [ ] Tables: `<th scope="col/row">` for screen readers
- [ ] Charts: alternative tabular data available
- [ ] Time limits: warning before session expiry

## Color Blindness

~8% of males, ~0.5% of females have color vision deficiency.

| Type | Affected Colors | Solution |
|---|---|---|
| Deuteranopia (most common) | Red/Green | Use shape + color (▲ green, ▼ red) |
| Protanopia | Red/Green (shifted) | Same as above |
| Tritanopia | Blue/Yellow | Avoid blue-only vs yellow-only |

### Rules
- Never use color as the ONLY differentiator
- Add icons, patterns, labels, or position as secondary cue
- Test with colorblind simulation (Stark, Chrome DevTools)
- Use color pairs that remain distinct: blue/orange, purple/yellow

## Testing Checklist (Before Ship)

### Automated
- [ ] axe DevTools scan: 0 critical/serious violations
- [ ] Lighthouse accessibility score: 90+
- [ ] HTML validator: no semantic errors

### Manual
- [ ] Tab through entire page — logical order, no traps
- [ ] Screen reader (NVDA/VoiceOver) — all content announced
- [ ] Zoom to 200% — no content loss or overlap
- [ ] Colorblind simulation — all information still conveyed
- [ ] Keyboard-only operation — all actions achievable
- [ ] `prefers-reduced-motion` enabled — no jarring animations
