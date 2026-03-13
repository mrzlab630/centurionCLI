# Telegram Bot UI Patterns — AEDILIS Reference

> Design-level patterns only. For API details, rate limits, SDK — consult **PRAECO** skill.

## Layout Rules

### Main Menu
- **Max 3 rows** of buttons (primary actions)
- **Max 3 buttons per row** (comfortable tap targets)
- Group logically: [Navigation] [Actions] [Settings]

### Settings / Configuration
- **Edit message in-place** — never send new messages for settings changes
- Use toggle indicators: `[✅ Enabled]` / `[❌ Disabled]`
- Back button always in bottom-left position
- Hierarchical: Main Settings → Category → Individual Setting

### Lists / Pagination
- **5 items per page** maximum
- Navigation: `[◀ Prev] [1/3] [Next ▶]`
- Each item: one row, clickable, with brief info

### Confirmations
- **Always two-button row:** `[❌ Cancel] [✅ Confirm]`
- Cancel on LEFT, Confirm on RIGHT (reading direction)
- Add consequences in message text: "This will sell ALL positions"

### Error Messages
- Specific, actionable text (never "Something went wrong")
- Include retry button + fallback to menu

## Message Formatting

### Tree Block Pattern
```
╭─ 🔍 Section Header
├ Key: Value
├ Key: Value
├ ​
├ 📊 Subsection:
├    Detail: Value
╰─ Footer / Summary
```

### Data Display
- **SOL amounts:** 4 decimal places: `1.2345 SOL`
- **Percentages:** 1 decimal: `42.5%`
- **Addresses:** Truncate: `7A77...K8Dz` (4+4 chars) — full in `<code>` for copy
- **Timestamps:** Relative preferred: "2h ago"

### Emoji Conventions
- Consistent mapping: same concept = same emoji everywhere
- **Status:** ✅ success, ❌ error, ⏳ pending, ⚠️ warning
- **Navigation:** ◀️ back, ▶️ forward, 🔄 refresh, ↩️ return
- **Data:** 📊 stats, 💰 money, 📈 up, 📉 down, 🎯 target
- **Actions:** ⚙️ settings, 🔍 search, ➕ add, 🗑 delete
- Max 2 emoji per line. No decorative-only emoji.

## Design Anti-Patterns
- Sending new message when edit-in-place works
- Using ReplyKeyboard for navigation (use InlineKeyboard)
- Relying on message history for state
- Chat flooding (>3 messages in quick succession)

## Technical Reference
For Bot API constraints (limits, formatting, keyboard types, rate limits), grammY patterns,
and our codebase conventions → consult **PRAECO** skill (`/praeco`).
