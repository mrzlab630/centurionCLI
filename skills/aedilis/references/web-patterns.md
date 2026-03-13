# Web App UI Patterns — AEDILIS Reference

## Responsive Layout Strategy

### Mobile-First Breakpoints
```
320px  — Small mobile (min supported)
640px  — Large mobile / Small tablet
768px  — Tablet portrait
1024px — Tablet landscape / Small desktop
1280px — Desktop
1536px — Large desktop
```

### Layout Patterns by Breakpoint

**Mobile (320-639):**
- Single column, full-width cards
- Bottom navigation (fixed), 3-5 tabs
- Hamburger menu for secondary nav
- Collapsible sections for dense content
- Sticky CTA at bottom

**Tablet (640-1023):**
- Two-column layout for list + detail
- Side panel slides in (not replaces content)
- Navigation moves to sidebar (collapsible)

**Desktop (1024+):**
- Multi-column dashboard
- Persistent sidebar navigation
- Split views (list + detail side-by-side)
- Hover states for tooltips and previews

## Modern CSS Patterns (2025-2026)

### Container Queries (Preferred over Media Queries)
```css
.card-container {
  container-type: inline-size;
}
@container (min-width: 400px) {
  .card { flex-direction: row; }
}
```

### CSS Grid for Dashboards
```css
.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}
```

### Scroll-Driven Animations
```css
.hero { animation: fade-in linear; animation-timeline: view(); }
```

## Core Web Vitals

| Metric | Target | How to Achieve |
|---|---|---|
| LCP | <2.5s | Optimize hero image, preload fonts, SSR |
| FID/INP | <200ms | Code split, defer non-critical JS |
| CLS | <0.1 | Set explicit dimensions, reserve space for async content |

## Form Design

### Rules
- Labels ABOVE inputs (not inside as placeholder)
- Error messages below the field, in red, with icon
- Success validation: green checkmark inline
- Submit button: disabled until valid (with tooltip explaining why)
- Tab order: logical, top-to-bottom, left-to-right

### Input States
```
Default  → Gray border
Focus    → Blue border + shadow
Valid    → Green border + ✓
Error    → Red border + error text
Disabled → Gray background, reduced opacity
```

## Data Table Best Practices

- Sticky header row
- Alternating row colors (subtle) or horizontal rules
- Sortable columns with sort indicator (▲/▼)
- Row hover highlight
- Pagination or infinite scroll (not both)
- Responsive: hide less-important columns on mobile, or switch to card layout
- Action buttons: rightmost column, or revealed on hover

## Toast / Notification System

- Position: top-right (desktop), top-center (mobile)
- Auto-dismiss: 5s for info, persistent for errors
- Max 3 visible simultaneously (queue the rest)
- Types: success (green), error (red), warning (amber), info (blue)
- Include dismiss button (×)
- Accessible: `role="alert"` for errors, `role="status"` for info

## Modal / Dialog

- Backdrop: semi-transparent dark overlay
- Close: × button + Escape key + backdrop click
- Focus trap: Tab cycles within modal only
- Scroll: modal body scrolls, header/footer stay fixed
- Size: max-width 560px (small), 720px (medium), 960px (large)
- Mobile: bottom sheet instead of centered modal

## Loading Patterns (Priority Order)

1. **Skeleton screen** — placeholder shapes matching content layout
2. **Progressive loading** — show content as it arrives
3. **Spinner** — only for small inline elements
4. **Progress bar** — for determinate operations (file upload, batch process)
5. **Never** — blank white screen

## PWA Considerations

- Service Worker for offline fallback page
- App manifest with icons (192×192, 512×512)
- Install prompt: show after 2+ visits, dismissible
- Push notifications: request permission contextually (not on first visit)
- Cache strategy: Network-first for API, Cache-first for static assets
