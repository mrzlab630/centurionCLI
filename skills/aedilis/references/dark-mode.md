# Dark Mode Best Practices — AEDILIS Reference

## Surface Color System (Layered Darkness)

| Layer | Purpose | Light Mode | Dark Mode |
|---|---|---|---|
| Base | App background | `#FFFFFF` | `#0F1115` |
| Surface 1 | Cards, panels | `#F8FAFC` | `#1A1D24` |
| Surface 2 | Elevated cards, modals | `#F1F5F9` | `#22262E` |
| Surface 3 | Hover states, dropdowns | `#E2E8F0` | `#2A2F38` |
| Border | Dividers, outlines | `#CBD5E1` | `#2E3440` |
| Text primary | Body text | `#1E293B` | `#E5E7EB` |
| Text secondary | Labels, hints | `#64748B` | `#9CA3AF` |
| Text disabled | Inactive | `#94A3B8` | `#4B5563` |

## Critical Rules

### NEVER
- Pure black (`#000000`) for backgrounds — too harsh, "OLED black hole" effect
- Pure white (`#FFFFFF`) for text on dark — halation on OLED screens
- Same saturation for accent colors — desaturate 10-15% in dark mode
- Shadows on dark backgrounds — use borders or subtle glows instead
- High-contrast neon colors without desaturation — causes eye strain

### ALWAYS
- Test on OLED screens (colors render differently)
- Use surface layers for depth perception (not shadows)
- Desaturate accent colors for dark mode (green-500 → green-400, red-500 → red-400)
- Semi-transparent backgrounds for colored indicators: `rgba(color, 0.12)`
- Increase icon stroke width by 0.5px in dark mode (thin lines disappear)

## OLED Optimization

- True black (`#000`) ONLY for the outermost frame (status bar, edges) — battery savings
- Content area: dark gray (`#0F1115`) for depth perception
- This dual approach saves 30-40% battery vs all-gray while avoiding "floating text"

## Chart-Specific Dark Mode

### Candlestick Charts
- Outline with 1px border in accent color
- Fill with 30% opacity version of the color
- Grid lines: `#1E2128` (barely visible — grid should not compete with data)

### Line Charts
- Line stroke: 2px in accent color
- Area fill: gradient from 30% opacity to 0% opacity
- Axis text: `--text-secondary` color

### Color Palette for Data Visualization (Dark Mode)
```
#60A5FA  Blue (primary series)
#34D399  Green (profit/positive)
#F87171  Red (loss/negative)
#FBBF24  Amber (warning/highlight)
#A78BFA  Purple (secondary series)
#FB923C  Orange (tertiary series)
#2DD4BF  Teal (quaternary series)
```

## Implementation

### CSS Strategy (Recommended)
```css
/* System preference detection */
@media (prefers-color-scheme: dark) {
  :root { /* dark tokens */ }
}

/* Manual override via class/attribute */
[data-theme="dark"] { /* dark tokens */ }
[data-theme="light"] { /* light tokens */ }
```

### Tailwind CSS
- Use `class` strategy (not `media`) for manual toggle
- `darkMode: 'class'` in tailwind.config.ts

### Telegram Mini App Bridge
```css
/* Map Telegram theme to your tokens */
:root {
  --surface-0: var(--tg-theme-bg-color);
  --surface-1: var(--tg-theme-secondary-bg-color);
  --text-primary: var(--tg-theme-text-color);
  --text-secondary: var(--tg-theme-hint-color);
  --accent: var(--tg-theme-button-color);
}
```

## Testing Checklist
- [ ] All text meets contrast ratio (4.5:1 body, 3:1 large)
- [ ] Semantic colors still distinguishable (profit vs loss)
- [ ] Images/icons visible against dark backgrounds
- [ ] Focus indicators visible
- [ ] Form inputs have visible borders
- [ ] Disabled states distinguishable from enabled
- [ ] Charts/graphs readable
- [ ] Switch between light/dark doesn't flash or flicker
