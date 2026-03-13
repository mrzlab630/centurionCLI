# Telegram Mini Apps SDK — Reference

> Core patterns and constraints. For method signatures, use Context7 (`@tma.js/sdk`).

## Initialization

```typescript
import { init, backButton, mainButton, themeParams } from '@tma.js/sdk';

// Must call init() before accessing any component
const [components] = init();

// Or with error handling
try {
  const [components] = init();
} catch (e) {
  // Not running inside Telegram — show fallback UI
}
```

## Theme Variables (CSS)

Telegram injects these CSS variables. Use them for native look:

```css
:root {
  /* Primary */
  --tg-theme-bg-color              /* Main background */
  --tg-theme-text-color            /* Primary text */
  --tg-theme-hint-color            /* Secondary/muted text */
  --tg-theme-link-color            /* Links and accents */
  --tg-theme-button-color          /* Primary button background */
  --tg-theme-button-text-color     /* Primary button text */

  /* Secondary */
  --tg-theme-secondary-bg-color    /* Cards, sections */
  --tg-theme-header-bg-color       /* Header background */
  --tg-theme-bottom-bar-bg-color   /* Bottom bar */
  --tg-theme-accent-text-color     /* Accent text */
  --tg-theme-section-bg-color      /* Section background */
  --tg-theme-section-header-text-color
  --tg-theme-section-separator-color
  --tg-theme-subtitle-text-color
  --tg-theme-destructive-text-color /* Delete, danger actions */

  /* Safe areas (notch, home indicator) */
  --tg-content-safe-area-inset-top
  --tg-content-safe-area-inset-bottom
  --tg-content-safe-area-inset-left
  --tg-content-safe-area-inset-right
  --tg-safe-area-inset-top
  --tg-safe-area-inset-bottom
}
```

**RULE:** NEVER use hardcoded colors. Always use `var(--tg-theme-*)`.
This ensures the Mini App matches user's Telegram theme (light/dark/custom).

## Components Overview

| Component | Purpose | Min Version |
|---|---|---|
| `mainButton` | Primary CTA at bottom | 6.0 |
| `backButton` | Back arrow in header | 6.1 |
| `secondaryButton` | Secondary CTA | 7.10 |
| `settingsButton` | Gear icon in header | 7.0 |
| `hapticFeedback` | Vibration patterns | 6.1 |
| `cloudStorage` | Key-value cloud storage | 6.9 |
| `biometricManager` | Fingerprint/Face ID | 7.2 |
| `popup` | Native alert/confirm | 6.2 |
| `themeParams` | Read theme colors | 6.0 |
| `viewport` | Safe areas, dimensions | 6.0 |
| `closingBehavior` | Confirm before close | 6.0 |
| `fullscreen` | Fullscreen mode | 8.0 |
| `accelerometer` | Device accelerometer | 8.0 |
| `gyroscope` | Device gyroscope | 8.0 |
| `deviceOrientation` | Compass/orientation | 8.0 |
| `locationManager` | GPS location | 8.0 |
| `invoice` | Telegram Stars payment | 6.1 |
| `qrScanner` | QR code scanner | 6.4 |
| `shareStory` | Share to Stories | 7.8 |

## Storage Types

| Type | Capacity | Persistence | Encryption | Min Ver |
|---|---|---|---|---|
| CloudStorage | 1024 keys × 4096 bytes each | Cross-device, cloud-synced | No | 6.9 |
| DeviceStorage | ~5 MB | Device-only, survives reinstall | No | 8.0 |
| SecureStorage | 10 items | Device-only, OS keychain | Yes (biometric) | 8.0 |

### CloudStorage API
```typescript
cloudStorage.setItem('key', 'value');           // Set
const val = await cloudStorage.getItem('key');  // Get (async!)
cloudStorage.removeItem('key');                  // Delete
const keys = await cloudStorage.getKeys();       // List all keys
const items = await cloudStorage.getItems(keys); // Bulk get
```

### When to Use Which
- **CloudStorage:** User preferences, saved states, small data
- **DeviceStorage:** Cached API responses, large datasets
- **SecureStorage:** Private keys, auth tokens, sensitive data
- **Server-side DB:** Everything else (transactions, history, analytics)

## Platform Differences

| Feature | iOS | Android | Desktop | Web (tg.me) |
|---|---|---|---|---|
| Haptic feedback | Full | Full | None | None |
| Biometrics | Face ID / Touch ID | Fingerprint | None | None |
| Sensors | All (8.0+) | All (8.0+) | None | Limited |
| Fullscreen | Yes | Yes | Limited | No |
| QR Scanner | Native camera | Native camera | Webcam | Webcam |
| Safe areas | Dynamic (notch) | Dynamic | Fixed | Fixed |
| Performance | Good | Varies by device | Best | Good |
| File access | Limited | Limited | Full | Limited |

## Init Data & Validation

```typescript
import { initData } from '@tma.js/sdk';

// Available fields
initData.user         // { id, firstName, lastName, username, languageCode, isPremium }
initData.chat         // { id, type, title } (if opened from group)
initData.startParam   // Deep link parameter
initData.authDate     // Unix timestamp
initData.hash         // HMAC-SHA256 signature

// MUST validate on server (Ed25519 since v8.0, HMAC before)
// Never trust client-side initData without server validation
```

## Recommended Stack

```
React 18+ / Vue 3+ / Svelte 5+
├── @tma.js/sdk           # Official Telegram SDK
├── @tma.js/sdk-react     # React bindings (hooks)
├── Vite                  # Build tool (fast, <150KB bundle target)
├── Tailwind CSS          # Utility-first, purges unused
└── shadcn/ui             # Component library (customizable)
```

## Performance Constraints

| Metric | Target |
|---|---|
| Bundle size | <150 KB (gzipped) |
| Initial load | <1.5s (LCP) |
| Interaction delay | <100ms (INP) |
| Memory | <100 MB |
| Animation | 60fps |

**Why small bundle matters:** Mini Apps load inside Telegram WebView. Large bundles =
noticeable delay on mobile, especially on slow connections. Users expect instant load.

## Communication with Bot

```typescript
// Send data to bot (closes Mini App)
import { sendData } from '@tma.js/sdk';
sendData(JSON.stringify({ action: 'buy', amount: 1.5 }));
// Bot receives via web_app_data in message

// Open invoice (Telegram Stars)
import { invoice } from '@tma.js/sdk';
await invoice.open('invoice_link', 'compact'); // or 'fullscreen'

// Open link in browser
import { openLink, openTelegramLink } from '@tma.js/sdk';
openLink('https://example.com');                    // External browser
openTelegramLink('https://t.me/username/app');     // Inside Telegram
```

## Common Gotchas

1. **init() must be first** — No SDK calls before init(). Will throw.
2. **CloudStorage is async** — getItem returns Promise, not value.
3. **Theme changes at runtime** — User can switch themes. Listen to `themeChanged` event.
4. **Safe areas change** — Rotation, keyboard appearance. Use CSS variables, not fixed values.
5. **No window.alert()** — Use popup.open() instead.
6. **Closing behavior** — Set closingBehavior.enableConfirmation() to prevent accidental close.
7. **Desktop differences** — No haptics, no sensors, different viewport behavior.
8. **initData.hash** — MUST validate server-side. Client can forge data.
