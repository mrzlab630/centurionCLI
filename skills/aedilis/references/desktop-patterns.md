# Desktop App UI Patterns — AEDILIS Reference

## Framework Options

| Framework | Best For | Stack |
|---|---|---|
| Electron | Full web stack, large ecosystem | Chromium + Node.js |
| Tauri | Lightweight, Rust backend, smaller binary | System WebView + Rust |
| Flutter Desktop | Cross-platform with mobile | Dart + Skia |
| .NET MAUI | Windows + macOS (Microsoft ecosystem) | C# + XAML |
| Qt | High-performance, native feel | C++ / Python |

## Window Management

### Standard Window Chrome
```
┌─[Icon] App Name ─────────────── [_] [□] [×]─┐
├─ Menu Bar ──────────────────────────────────────┤
│  File  Edit  View  Help                        │
├─ Toolbar ───────────────────────────────────────┤
│  [New] [Open] [Save] | [Undo] [Redo] | Search │
├─ Sidebar ─┬─ Main Content ─────────────────────┤
│            │                                     │
│  Nav items │  Content area                       │
│            │                                     │
├────────────┴─────────────────────────────────────┤
│  Status Bar          | Line 42, Col 12 | UTF-8  │
└──────────────────────────────────────────────────┘
```

### Multi-Window Patterns
- **MDI (Multiple Document Interface):** Tabs within single window (VS Code style)
- **SDI (Single Document Interface):** One document per window (TextEdit style)
- **Hybrid:** Main window + floating panels (Photoshop style)

### Window Sizing
- Remember last position and size
- Sensible defaults: 1024×768 minimum, centered on primary monitor
- Minimum size constraints to prevent broken layouts
- Snap-to-edge support (Windows Snap, macOS Split View)

## Keyboard Shortcuts

### Standard (Cross-Platform)
| Action | Windows/Linux | macOS |
|---|---|---|
| New | Ctrl+N | Cmd+N |
| Open | Ctrl+O | Cmd+O |
| Save | Ctrl+S | Cmd+S |
| Undo | Ctrl+Z | Cmd+Z |
| Redo | Ctrl+Y / Ctrl+Shift+Z | Cmd+Shift+Z |
| Find | Ctrl+F | Cmd+F |
| Quit | Alt+F4 | Cmd+Q |
| Preferences | Ctrl+, | Cmd+, |
| Full Screen | F11 | Ctrl+Cmd+F |

### Custom Shortcuts
- Discoverable: show in menus and tooltips
- Configurable: allow user rebinding
- No conflicts with OS-level shortcuts
- Document in Help > Keyboard Shortcuts

## Menu Bar

### Standard Menu Order
```
File | Edit | View | [App-specific menus] | Window | Help
```

### Menu Rules
- Use standard names for standard actions (File > Save, not File > Store)
- Show keyboard shortcuts right-aligned in menu items
- Separator lines between logical groups
- Disabled items: gray out (don't hide — helps discoverability)
- Submenu depth: max 2 levels
- Recent items: File > Open Recent (max 10 items)

## Context Menus (Right-Click)

- Keep to 5-10 items maximum
- Most common actions first
- Separator lines between groups
- Include keyboard shortcuts
- Disabled items shown grayed (not hidden)

## System Tray / Menu Bar Icon

- Minimal: icon + dropdown menu only
- Left-click: show/hide main window
- Right-click: context menu (Quit, Settings, Status)
- Badge/overlay for notifications or status (green dot = connected)
- Tooltip on hover: app name + status

## Drag and Drop

- Visual feedback during drag (ghost image, drop target highlight)
- Cursor change: copy (+ badge), move (no badge), denied (🚫)
- Drop zones: highlighted border/background on valid targets
- Cancel: Escape key or drop outside valid zone
- Accessibility: keyboard alternative for all drag operations

## Notifications

### OS-Native (Preferred)
- Use system notification center (Windows Toast, macOS Notification Center)
- Respect Do Not Disturb mode
- Group related notifications
- Click notification opens relevant window/section

### In-App
- Toast/snackbar for non-critical info
- Modal dialog for critical confirmations
- Badge on app icon for unread count

## Performance

- Cold start: <3s to usable state
- Memory: <200MB idle, <500MB active
- CPU: <5% idle
- Smooth scroll: 60fps in lists and content areas
- Background: minimize resource usage when not focused

## Cross-Platform Considerations

- Use system fonts (Segoe UI / San Francisco / system-ui)
- Respect platform conventions (OK/Cancel order reversed macOS vs Windows)
- File paths: handle `/` vs `\`, spaces, unicode
- High DPI: support 2x and 3x scaling
- Theme: follow system light/dark preference
