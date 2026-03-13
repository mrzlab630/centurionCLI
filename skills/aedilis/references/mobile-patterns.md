# Mobile App UI Patterns — AEDILIS Reference

## Platform Guidelines

| Platform | Guideline | Key Resource |
|---|---|---|
| iOS | Human Interface Guidelines (HIG) | developer.apple.com/design |
| Android | Material Design 3 | m3.material.io |
| Cross-platform | Platform-adaptive components | Use conditional styles |

## Navigation Patterns

### Bottom Tab Bar (Primary — 3-5 tabs)
```
[Home] [Search] [Add] [Activity] [Profile]
  🏠     🔍       ➕      📊       👤
```
- Active: filled icon + label + brand color
- Inactive: outline icon + muted color
- Badge: small dot or count on icon
- iOS: no labels on inactive (Apple style) or always show (Material)

### Stack Navigation
- Push/pop with slide animation (iOS) or fade (Material)
- Back button: top-left (iOS) or system gesture (Android)
- Large title collapses on scroll (iOS pattern)

### Tab + Stack (Hybrid)
- Each tab has its own navigation stack
- Switching tabs preserves stack state
- Deep links restore correct tab + stack position

### Drawer / Sidebar
- Use for secondary navigation only (not primary)
- Swipe from left edge to open (standard gesture)
- Android: Material Navigation Drawer
- iOS: Less common, prefer bottom tabs

## Gestures

| Gesture | Action | Platform |
|---|---|---|
| Swipe left on item | Reveal actions (delete, archive) | iOS (leading), Material (trailing) |
| Swipe right on item | Secondary actions or undo | iOS |
| Pull down | Refresh content | Both (standard) |
| Long press | Context menu / selection mode | Both |
| Pinch | Zoom (maps, images, charts) | Both |
| Swipe up from bottom | Expand bottom sheet | Both |

## Safe Areas

```
┌─────── Status bar (44pt iOS / 24dp Android) ──────┐
│                                                     │
│              Content Area                           │
│              (safe zone)                            │
│                                                     │
├─────── Bottom safe area (34pt iPhone X+) ──────────┤
│          Home indicator zone                        │
└─────────────────────────────────────────────────────┘
```

- Never place interactive elements in unsafe areas
- Bottom navigation bar sits ABOVE the home indicator
- Use `env(safe-area-inset-*)` in CSS for web views

## Component Sizing

| Element | iOS | Android |
|---|---|---|
| Nav bar height | 44pt | 56dp (Material 3) |
| Tab bar height | 49pt | 80dp (Material 3) |
| Button height (min) | 44pt | 48dp |
| Touch target (min) | 44×44pt | 48×48dp |
| List item height | 44pt (compact) / 88pt (detail) | 56dp / 72dp |
| Text body | 17pt (SF Pro) | 16sp (Roboto) |

## Haptic Feedback

| Event | iOS | Android |
|---|---|---|
| Button tap | `.light` impact | `CLICK` effect |
| Success | `.success` notification | `CONFIRM` |
| Error | `.error` notification | `REJECT` |
| Selection change | `.selection` | `TICK` |
| Heavy action (delete) | `.heavy` impact | `HEAVY_CLICK` |

## Dark Mode

- Both iOS and Android have system dark mode toggle
- App MUST respect system setting by default
- Optional: manual override in app settings (3 states: System / Light / Dark)
- Test with both system themes before release

## Performance Guidelines

| Metric | Target |
|---|---|
| Cold start | <2s |
| Warm start | <1s |
| Frame rate | 60fps (no jank during scroll) |
| Memory | <150MB active |
| Battery | No background drain >2%/hour |

## Notification Design

- **Title:** Short, actionable (max 50 chars)
- **Body:** One sentence, informative (max 100 chars)
- **Action buttons:** max 3, clear verbs ("View", "Dismiss", "Reply")
- **Grouping:** Stack similar notifications (e.g., multiple trades)
- **Timing:** Never wake user for non-urgent updates. Use silent push.

## Offline Support

1. Show cached data with "Offline" indicator
2. Queue user actions, sync when online
3. Disable actions that require network (gray out + tooltip)
4. Show last-updated timestamp
5. Auto-retry on reconnect (with deduplication)

## App Store Design Requirements

### Screenshots
- iOS: 6.7" (1290×2796) + 5.5" (1242×2208) + iPad
- Android: min 2, max 8 screenshots, 16:9 or 9:16
- First screenshot is most important (shown in search results)
- Show actual UI, not marketing graphics

### Icon
- iOS: 1024×1024 (no transparency, no rounded corners — system adds them)
- Android: 512×512 (adaptive icon with foreground + background layers)
- Simple, recognizable at 29×29pt (smallest display size)
