# Component Interface Systems — AEDILIS Reference

Use this file when designing modern React interfaces, dashboards, admin panels,
forms, data tables, dialogs, navigation, reusable component systems, or when the
task mentions shadcn/ui, Radix UI, Cloudscape, MUI, or Ant Design.

## Table Of Contents

- Source Rule
- WAR ROOM Verdict
- Library Decision Matrix
- Design Workflow
- Component Contract
- Layout And Density
- Forms
- Data Tables
- Dialogs And Overlays
- Navigation
- Accessibility Baseline
- Handoff To PICTOR
- Output Template

## Source Rule

- Extract interface principles and architecture patterns, not code, brand style, or visual identity.
- Prefer the user's existing stack and design system before introducing a new library.
- Treat component libraries as references for behavior, state coverage, accessibility, and API ergonomics.
- Do not copy library demos as product screens. Convert them into domain-specific flows.

## WAR ROOM Verdict

Do not create a separate generic UI legionary while AEDILIS and PICTOR exist.

| Role | Responsibility |
|---|---|
| AEDILIS | Decide what the interface should be: IA, layout, components, states, accessibility, density, visual hierarchy. |
| PICTOR | Implement the interface in React/Vue/Svelte/Next/Tailwind using the chosen primitives/components. |
| PRAECO | Validate Telegram-specific UI/platform constraints for Mini Apps and bots. |
| LUDIFEX | Define game product screens and loops before AEDILIS designs the concrete UI. |

## Library Decision Matrix

| Need | Prefer | Why | Avoid |
|---|---|---|---|
| Custom React product UI with Tailwind | shadcn/ui + Radix primitives | Copy-in component ownership, Tailwind tokens, accessible primitives. | Treating shadcn defaults as final brand design. |
| Headless accessible behavior | Radix UI primitives | Strong dialogs, popovers, menus, tabs, sliders, focus handling. | Rebuilding complex ARIA widgets from scratch. |
| Enterprise console/admin | Cloudscape | Mature tables, filters, layout density, forms, side panels, status patterns. | Forcing Cloudscape visual language into consumer apps. |
| Material ecosystem or broad enterprise team | MUI | Complete styled component set, docs, theming, strong ecosystem. | Mixing MUI with Tailwind ad hoc without token strategy. |
| China/enterprise-heavy admin workflows | Ant Design | Data-heavy components, tables, forms, selectors, enterprise conventions. | Using Ant's dense defaults for small mobile experiences. |
| Telegram Mini App custom UI | Telegram UI + project tokens, or shadcn/Radix adapted to Telegram vars | Native feel and theme compatibility. | Desktop dashboard density inside Telegram. |

## Design Workflow

1. Identify the task domain: consumer app, Mini App, admin console, dashboard, form workflow, data grid, marketing surface, internal tool.
2. Audit existing components and libraries in the repo before recommending additions.
3. Choose primitive strategy: native HTML, headless primitive, copied component, or full styled kit.
4. Define screen hierarchy: primary action, secondary actions, grouped information, escape paths.
5. Specify the component contract: variants, sizes, states, accessibility, responsive behavior, content limits.
6. Define data and async states before visual polish: loading, empty, error, partial, stale, success, disabled.
7. Hand PICTOR a buildable spec: components to reuse, components to wrap, tokens, and validation gates.

## Component Contract

Every reusable component spec must include:

| Field | Requirement |
|---|---|
| Purpose | What user decision or action this component supports. |
| Variants | Primary/secondary/destructive/ghost, compact/comfortable, etc. |
| States | default, hover, focus, active, disabled, loading, error, success, empty. |
| Anatomy | Slots/parts: label, icon, helper, badge, action, content, footer. |
| Data rules | Min/max text, truncation, placeholder, skeleton, overflow behavior. |
| Accessibility | role, label, focus order, keyboard behavior, reduced motion. |
| Responsiveness | Mobile, tablet, desktop behavior and breakpoints/container queries. |
| Token hooks | Color, spacing, radius, typography, shadow variables. |

## Layout And Density

- Consumer/mobile: fewer choices, larger touch targets, stronger hierarchy, progressive disclosure.
- Admin/internal tools: compact density is acceptable when scanning/comparison is the main job.
- Telegram Mini Apps: mobile-first, fast first action, sticky primary CTA only when it does not cover content.
- Dashboards: prioritize comparison and anomaly detection; do not turn every metric into a decorative card.
- Use cards for repeated items or genuinely framed tools, not for every page section.

## Forms

- Labels are visible, not placeholder-only.
- Group fields by decision, not database table order.
- Validate inline after meaningful interaction, not on every keystroke for expensive checks.
- Show field-level error and top-level summary for long forms.
- For destructive or irreversible forms, use confirmation with clear consequence copy.
- Prefer proven form components from the selected library when they already handle accessibility and validation wiring.

## Data Tables

- Use tables only when comparison across rows/columns matters; otherwise use list or card patterns.
- Required states: loading skeleton, empty with next action, error with retry, filtered-empty, partial-data warning.
- Support sort, filter, pagination or virtualization, row selection, column visibility when the dataset demands it.
- Keep row actions predictable: rightmost actions, contextual menu for secondary actions, bulk action bar for multi-select.
- Mobile: collapse to priority columns or card/list layout; do not force horizontal scrolling as the only solution.
- Cloudscape, MUI Data Grid, or Ant Table are better references than hand-rolled enterprise tables.

## Dialogs And Overlays

- Use Radix-style primitives or library equivalents for focus trap, Escape, aria, portal, and scroll lock.
- Dialogs are for focused decisions; side panels are better for inspect/edit alongside context.
- Mobile destructive or action-heavy overlays should usually become bottom sheets.
- Every overlay needs a close path, keyboard path, and a clear title.
- Do not put nested cards inside modal cards; keep the surface simple.

## Navigation

- 3-5 top-level destinations on mobile; more belongs in secondary navigation.
- Admin apps can use sidebar + breadcrumbs + tabs, but each layer must answer a different question.
- Tabs switch peer views; steppers show ordered progress; segmented controls switch modes.
- Use icons only when they are conventional or paired with labels/tooltips.

## Accessibility Baseline

- Use native controls or proven primitives before custom ARIA.
- Focus states must be visible and not color-only.
- Icon-only actions require accessible labels and tooltips for unfamiliar icons.
- Contrast: 4.5:1 for normal text, 3:1 for large text and UI boundaries.
- Motion must respect `prefers-reduced-motion`.
- Do not hide error, status, or selection only in color.

## Handoff To PICTOR

AEDILIS should specify:

- Recommended library/primitives and why.
- Components to reuse versus custom wrappers to create.
- Token requirements and theme bridge.
- Required states and responsive rules.
- Accessibility behavior to preserve from primitives.
- Validation gates: typecheck, lint, focused component tests, Playwright/screenshot checks when visual risk is high.

## Output Template

```
AEDILIS — Component Interface Plan: [feature]

Decision:
[Use existing components / shadcn+Radix / Cloudscape / MUI / Ant / custom wrapper]

Rationale:
[Why this fits the product, density, accessibility, team ownership]

Screen Structure:
| Area | Purpose | Primary Action | Components |
|---|---|---|---|

Component Contract:
| Component | Variants | States | Accessibility | Responsive Notes |
|---|---|---|---|---|

Data States:
[loading, empty, error, success, partial, disabled]

Handoff:
→ PICTOR: [implementation notes]
→ PRAECO: [Telegram constraints if relevant]
→ TESTER: [visual/e2e checks]
```
