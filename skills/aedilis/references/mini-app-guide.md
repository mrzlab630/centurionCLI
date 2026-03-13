# Telegram Mini Apps — AEDILIS Reference

## SDK & Theming

### CSS Theme Variables (injected by Telegram)
```css
--tg-theme-bg-color              /* Main background */
--tg-theme-text-color            /* Primary text */
--tg-theme-hint-color            /* Secondary/hint text */
--tg-theme-link-color            /* Links and accents */
--tg-theme-button-color          /* CTA button background */
--tg-theme-button-text-color     /* CTA button text */
--tg-theme-secondary-bg-color    /* Cards, secondary surfaces */
```

Use `bindCssVars()` from `@telegram-apps/sdk` to auto-bind.

### Header Customization
- `web_app_set_header_color` — accepts theme key or custom RGB
- `web_app_set_background_color` — for immersive layouts

## Recommended Stack

```
React 19 + Vite 6 + TypeScript
├── @telegram-apps/sdk           (Telegram SDK integration)
├── @telegram-apps/telegram-ui   (native-feel components)
├── shadcn/ui + Radix UI         (custom components)
├── Tailwind CSS v4              (utility styling)
├── Zustand                      (state management, lightweight)
├── TanStack Query               (data fetching + caching)
└── lightweight-charts           (TradingView candlesticks)
```

## Component Libraries

| Library | Use Case |
|---|---|
| `@telegram-apps/telegram-ui` | Native Telegram look & feel |
| `Konsta UI` | CSS-variable-driven, auto-adapts to theme |
| `shadcn/ui` | Full control, own-your-code components |

## Theme Bridge (Telegram → Tailwind)

```typescript
// tailwind.config.ts
theme: {
  extend: {
    colors: {
      'tg-bg': 'var(--tg-theme-bg-color)',
      'tg-text': 'var(--tg-theme-text-color)',
      'tg-hint': 'var(--tg-theme-hint-color)',
      'tg-link': 'var(--tg-theme-link-color)',
      'tg-button': 'var(--tg-theme-button-color)',
      'tg-button-text': 'var(--tg-theme-button-text-color)',
      'tg-secondary': 'var(--tg-theme-secondary-bg-color)',
    }
  }
}
```

## Platform Capabilities (2025-2026)
- Full-screen layouts (no Telegram chrome)
- Landscape orientation support
- Home screen shortcuts
- Native share flows
- Gyroscope / accelerometer access
- Telegram Stars subscriptions (in-app payments)
- Web3 wallet integration
- Biometric authentication (fingerprint/face)
- Cloud storage (key-value, per-user)
- QR code scanner

## Navigation Pattern

### Bottom Tab Bar (Recommended for trading)
```
[Positions] [Wallet] [Trade] [Settings]
     📊        💰       🔄       ⚙️
```

- 3-5 tabs maximum
- Active tab: filled icon + label
- Inactive: outline icon, no label (optional)
- Badge for notifications/alerts

### Page Transitions
- Slide left/right for navigation depth
- Fade for same-level transitions
- Bottom sheet for actions (swipe to expand/dismiss)
- Modal for confirmations

## Performance Constraints

| Metric | Target | Why |
|---|---|---|
| First paint | <1.5s on 3G | Telegram shows loading spinner until ready |
| Bundle size | <150KB gzipped | Mobile data constraints |
| JS execution | <50ms main thread blocks | Prevents jank in Telegram WebView |

### Optimization Patterns
- Code splitting by route (React.lazy)
- Skeleton screens during data fetch
- Virtualized lists for >20 items
- Preconnect to API endpoints
- Service Worker for offline support

## Design Guidelines

### Sizing
- Follow Telegram's density (compact, information-dense)
- Padding: 16px horizontal, 12px vertical for cards
- Touch targets: 44px minimum height
- Font: System font stack (matches Telegram's native text)

### Native Feel
- Use Telegram's native transitions when possible
- Haptic feedback via `HapticFeedback` API
- Respect user's Telegram theme (light/dark/custom)
- Use `MainButton` for primary CTA (renders at bottom, native style)
- Use `BackButton` for navigation (renders in header, native style)

### Anti-Patterns
- Custom navigation that conflicts with Telegram's Back button
- Non-themed colors that clash with user's Telegram theme
- Heavy animations that lag in WebView
- Popups/alerts instead of native Telegram confirmations
- Loading spinners instead of skeleton screens
