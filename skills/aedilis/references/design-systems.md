# Design Systems & Component Architecture — AEDILIS Reference

## Recommended Stacks by Platform (2025-2026)

| Use Case | Stack |
|---|---|
| Web (maximum flexibility) | shadcn/ui + Tailwind CSS + Radix UI |
| Web (enterprise/compliance) | MUI (Material UI) |
| Web (accessibility-first) | Chakra UI or Radix Primitives |
| Web (rapid prototype) | Bootstrap 5 |
| Telegram Mini App (native feel) | @telegram-apps/telegram-ui |
| Telegram Mini App (custom design) | shadcn/ui + Telegram CSS variable bridge |
| React Native mobile | Tamagui or NativeWind + Tailwind |
| Desktop (Electron/Tauri) | shadcn/ui + platform-specific chrome |
| CLI | chalk + ora + cli-table3 + boxen |

## Design Token Architecture

### Directory Structure
```
tokens/
  colors/
    semantic.ts     # success, error, warning, info, neutral
    brand.ts        # primary, secondary, accent
    surface.ts      # bg levels by elevation
  spacing.ts        # 4px base: 1(4) 2(8) 3(12) 4(16) 5(20) 6(24) 8(32) 10(40) 12(48) 16(64)
  typography.ts     # families, size scale, weights, line heights
  radii.ts          # none(0) sm(4) md(8) lg(12) xl(16) full(9999)
  shadows.ts        # sm, md, lg elevation shadows
  transitions.ts    # duration (150/200/300ms) + easing functions
  breakpoints.ts    # sm(640) md(768) lg(1024) xl(1280) 2xl(1536)
```

### CSS Variables Pattern
```css
:root {
  /* Surface layers */
  --surface-0: #FFFFFF;
  --surface-1: #F8FAFC;
  --surface-2: #F1F5F9;
  --surface-3: #E2E8F0;
  --border: #CBD5E1;
  --text-primary: #1E293B;
  --text-secondary: #64748B;
  --text-disabled: #94A3B8;
}

[data-theme="dark"] {
  --surface-0: #0F1115;
  --surface-1: #1A1D24;
  --surface-2: #22262E;
  --surface-3: #2A2F38;
  --border: #2E3440;
  --text-primary: #E5E7EB;
  --text-secondary: #9CA3AF;
  --text-disabled: #4B5563;
}
```

### Spacing System (8-point grid)
```
4px   — micro spacing (icon-to-text)
8px   — tight spacing (related items)
12px  — default padding (compact layouts)
16px  — standard padding (cards, inputs)
20px  — comfortable spacing
24px  — section padding
32px  — group separation
48px  — major section gaps
64px  — page-level spacing
```

### Typography Scale (1.25 ratio)
```
12px  — Caption, labels, hints
14px  — Small body, metadata
16px  — Body text (minimum for readability)
20px  — Subheadings, large body
24px  — Section headings
32px  — Page titles
40px  — Hero numbers (portfolio value)
```

## Component Hierarchy

### Atomic Design
```
Atoms → Molecules → Organisms → Templates → Pages

Atoms:       Button, Input, Badge, Icon, Avatar, Spinner
Molecules:   FormField (Label+Input+Error), ButtonGroup, Stat (Label+Value)
Organisms:   Card, Modal, DataTable, Navigation, Sidebar
Templates:   DashboardLayout, AuthLayout, SettingsLayout
Pages:       Specific instances with real data
```

### Component State Matrix (Every Component MUST Address)

| State | Visual | Behavior |
|---|---|---|
| Default | Normal appearance | Ready for interaction |
| Hover | Subtle highlight (web/desktop) | Cursor change |
| Active/Pressed | Depressed/scaled(0.97) | Action triggered |
| Focus | Visible outline (2px) | Keyboard navigable |
| Disabled | Reduced opacity (50%) | No interaction |
| Loading | Spinner or skeleton | Action in progress |
| Error | Red border/text | Show error message |
| Success | Green flash/check | Confirm completion |
| Empty | Placeholder illustration + CTA | Guide user to action |

## Responsive Breakpoints

```
Mobile:      320px — 639px   (1 column, stacked)
Tablet:      640px — 1023px  (2 columns, sidebar collapsible)
Desktop:     1024px — 1279px (full layout, sidebar visible)
Large:       1280px+         (wider content area, more columns)
```

### Mobile-First Media Queries
```css
/* Default styles = mobile */
@media (min-width: 640px) { /* tablet */ }
@media (min-width: 1024px) { /* desktop */ }
@media (min-width: 1280px) { /* large */ }
```

## Performance Targets (Web)

| Metric | Target |
|---|---|
| LCP (Largest Contentful Paint) | <2.5s |
| FID (First Input Delay) | <100ms |
| CLS (Cumulative Layout Shift) | <0.1 |
| TTI (Time to Interactive) | <3.5s |
| Initial bundle (gzipped) | <150KB |
| CSS (with Tailwind purge) | <10KB |

## Icon Systems

| Platform | Recommended |
|---|---|
| Web/Mini App | Lucide React (tree-shakeable, consistent) |
| Telegram Bot | Emoji (native, zero cost) |
| Mobile | Platform-native (SF Symbols / Material Icons) |
| CLI | Unicode box-drawing + emoji |

## Animation Principles

- **Duration:** 150ms (micro), 200ms (standard), 300ms (large elements)
- **Easing:** `ease-out` for entrances, `ease-in` for exits, `ease-in-out` for transforms
- **ALWAYS** respect `prefers-reduced-motion: reduce` — disable or simplify animations
- **Purpose:** Animations must communicate state change, not just decorate
- **Skeleton screens** > spinners > blank screens (in order of preference)
