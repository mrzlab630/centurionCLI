# Telegram Bot API — Essentials Cheat Sheet

> Stable reference. For method signatures and new features, use Context7.

## Rate Limits

| Scope | Limit | Consequence |
|---|---|---|
| Global (all chats) | 30 messages/sec | 429 Too Many Requests |
| Per chat (private) | 1 message/sec | 429, retry after N seconds |
| Per group chat | 20 messages/min | 429 |
| Inline query results | 50 results max | Silently truncated |
| Bulk notifications | 30 users/sec | Use Bot API server for >1K users |
| editMessage* | ~1/sec per message | 429, edits may be dropped |
| answerCallbackQuery | Must call within 30s | "Loading..." spinner stuck |
| File download | 20 MB max | Use getFile() + download URL |
| File upload | 50 MB max (by URL: 20 MB) | 413 Payload Too Large |
| Webhook | Max 40 connections | Set in setWebhook() |

## Message Constraints

| Element | Limit |
|---|---|
| Text message | 4096 chars (UTF-8) |
| Caption | 1024 chars |
| Inline keyboard buttons | 200 per message |
| editMessageReplyMarkup | 100 buttons |
| callback_data | 1-64 bytes |
| Button text | ~64 chars (practical, no hard limit) |
| input_field_placeholder | 64 chars |
| Deep link parameter | 64 chars (a-zA-Z0-9_-) |
| Message entities | 100 per message |
| Poll options | 2-10 options, 100 chars each |

## HTML Formatting (parse_mode: "HTML")

### Supported Tags
```html
<b>bold</b>
<i>italic</i>
<u>underline</u>
<s>strikethrough</s>
<code>inline code</code>
<pre>code block</pre>
<pre><code class="language-python">highlighted code</code></pre>
<a href="URL">link</a>
<a href="tg://user?id=123">mention by ID</a>
<tg-spoiler>spoiler</tg-spoiler>
<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
<blockquote>quote</blockquote>
<blockquote expandable>expandable quote</blockquote>
```

### Escaping (MUST escape in text content)
```
& → &amp;
< → &lt;
> → &gt;
```

### Rules
- Tags cannot be nested of same type (`<b><b>no</b></b>`)
- Different tags CAN nest: `<b><i>bold italic</i></b>`
- Unclosed tags → entire message fails to send
- Empty tags are allowed: `<b></b>` (renders nothing)
- `<a>` without href → parse error

## MarkdownV2 (Alternative)

### Special Characters (MUST escape with `\`)
```
_ * [ ] ( ) ~ ` > # + - = | { } . !
```

### Formatting
```
*bold*
_italic_
__underline__
~strikethrough~
||spoiler||
`inline code`
```pre block```
[link](URL)
[mention](tg://user?id=123)
> blockquote
**> expandable blockquote
```

**Recommendation:** Use HTML for programmatic generation (easier escaping).
Use MarkdownV2 only for simple static text.

## Keyboard Types

### InlineKeyboardMarkup
- Attached to message
- Buttons trigger callback_data or open URLs
- Can be edited in-place
- Persists until message is edited/deleted

### ReplyKeyboardMarkup
- Replaces default keyboard
- Buttons send text message (not callback)
- Can request phone/location/poll
- Use `resize_keyboard: true` (always)
- Use `one_time_keyboard: true` for single-use

### ForceReply
- Forces user to reply to specific message
- Best for: text input prompts
- Combine with `input_field_placeholder`
- `selective: true` — only for mentioned user

### ReplyKeyboardRemove
- Hides custom keyboard
- Use after ForceReply flow completes

## Button Types (InlineKeyboard)

| Type | Field | Use Case |
|---|---|---|
| Callback | `callback_data` | Most interactions, settings, navigation |
| URL | `url` | External links, Solscan, explorer |
| Web App | `web_app.url` | Launch Mini App |
| Login URL | `login_url` | OAuth-style login |
| Switch Inline | `switch_inline_query` | Switch to inline mode |
| Switch Inline Current | `switch_inline_query_current_chat` | Inline in same chat |
| Copy Text | `copy_text.text` | Copy to clipboard (v7.10+) |
| Pay | `pay: true` | Payment button (MUST be first) |

## Critical Gotchas

1. **answerCallbackQuery()** — MUST call immediately, even if you plan to edit the message later. Otherwise: perpetual loading spinner.

2. **editMessageText with same text** — API returns error "message is not modified". Always track if text actually changed.

3. **Message not found after edit** — User deleted message. Catch and re-send.

4. **HTML entity in callback_data** — callback_data is NOT HTML. Don't escape `&<>` in it.

5. **Webhook vs Polling** — Webhook: must have HTTPS, public IP. Polling: simpler, no server needed. Bot API local server: for files >20MB.

6. **getUpdates offset** — Must send `offset = update_id + 1` to acknowledge. Missing this = duplicate processing.

7. **Group privacy mode** — Bot only receives messages that mention it or are replies to it (unless privacy disabled via BotFather).

8. **Inline keyboard after ForceReply** — Cannot combine. ForceReply replaces keyboard.

9. **File IDs are bot-specific** — Cannot reuse file_id between different bots.

10. **Chat member updates** — Must be explicitly enabled in BotFather or via allowed_updates.

## API Versioning

Bot API version is independent of client versions. New features:
- v9.0+ (Dec 2024): Business accounts, story posting
- v9.1+ (Jan 2025): Checklists, accepted gift types
- v9.2+ (Feb 2025): Gift management improvements
- v9.3+ (Feb 2025): Message streaming (sendMessageDraft → editRawMessageText)
- v9.4+ (Feb 2025): Button styling (style field, icon_custom_emoji_id)
- v9.5+ (Mar 2025): Paid reactions, improved stars

**Use Context7 to check current version and new features.**
