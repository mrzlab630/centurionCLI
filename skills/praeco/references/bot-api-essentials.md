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

## Rich Messages (Bot API 10.1+)

Rich Messages are a separate structured-message API, not a replacement name for
`parse_mode: "Markdown"` in normal text messages.

Use Rich Messages when the bot needs document-like output: headings, lists,
tables, media blocks, block/pull quotations, collapsible details blocks,
footnotes/references, formulas, maps, collages, slideshows, or streamed AI
responses with richer formatting.

### API Surface

| Feature | Contract |
|---|---|
| Received content | `Message.rich_message: RichMessage` |
| Send final message | `sendRichMessage({ chat_id, rich_message, ... })` |
| Stream draft | `sendRichMessageDraft({ chat_id, draft_id, rich_message })` |
| Edit message | `editMessageText({ ..., rich_message })` instead of `text` |
| Inline/Web App/guest result content | `InputRichMessageContent.rich_message` |
| Input payload | `InputRichMessage` with exactly one of `html` or `markdown` |

`sendRichMessageDraft` is ephemeral: it creates a temporary 30-second preview.
After generation finishes, always call `sendRichMessage` with the complete
message to persist it in chat. `draft_id` must be non-zero; using the same
`draft_id` animates draft changes.

### InputRichMessage Fields

| Field | Notes |
|---|---|
| `html` | Rich HTML content. Mutually exclusive with `markdown`. |
| `markdown` | Rich Markdown content. Mutually exclusive with `html`. |
| `is_rtl` | Force right-to-left rendering. |
| `skip_entity_detection` | Disable auto-detection of URLs, emails, mentions, hashtags, cashtags, commands, phone numbers, etc. |

### Rich Message Limits

| Limit | Value |
|---|---|
| Text | 32768 UTF-8 chars, including custom emoji alt text and formula source |
| Blocks | 500 total, including nested blocks/list items/table rows/quotes/details |
| Nesting | 16 levels |
| Media attachments | 50 total photos/videos/audio files |
| Table columns | 20 |

### Rich Markdown

Rich Markdown is passed in `InputRichMessage.markdown`. It is compatible with
GitHub Flavored Markdown where possible and can contain supported Rich HTML tags.

Supported/high-value syntax includes:
- `#`-`######` headings
- `**bold**`, `__bold__`, `*italic*`, `_italic_`, `~~strike~~`, `==mark==`, `||spoiler||`
- inline code, fenced code blocks, and fenced `math` blocks
- links, email/phone/user links, custom emoji links, and date-time links
- unordered, ordered, and task lists
- block quotations
- media blocks via HTTP/HTTPS URLs
- tables with inline formatting only inside cells
- footnotes/references
- `$inline math$`, `$$block math$$`, and raw LaTeX formula source

For features without Markdown syntax, embed supported Rich HTML tags such as
`<u>`, `<sub>`, `<sup>`, `<a name="...">`, `<details>`, `<summary>`,
`<tg-map>`, `<tg-collage>`, and `<tg-slideshow>`.

### Rich HTML

Rich HTML is passed in `InputRichMessage.html`. It supports normal inline tags
plus document/media tags such as headings, paragraphs, pre/code blocks, footer,
divider, lists, blockquotes with `<cite>`, pull quotes via `<aside>`, figures,
tables, details blocks, maps, collages, slideshows, and math blocks.

Rich HTML named entities currently include: `&lt;`, `&gt;`, `&amp;`, `&quot;`,
`&apos;`, `&nbsp;`, `&hellip;`, `&mdash;`, `&ndash;`, `&lsquo;`, `&rsquo;`,
`&ldquo;`, and `&rdquo;`. Numerical entities are supported.

### Practical Rules

- Keep using basic `sendMessage`/`editMessageText.text` with HTML for compact bot
  UI messages, navigation, settings, errors, and short status screens.
- Use `sendRichMessage` for report-like or AI-generated content that benefits
  from document structure.
- Do not pass Rich Markdown through `parse_mode`; `parse_mode` only controls
  basic message formatting (`HTML`, `MarkdownV2`, legacy `Markdown`).
- For generated user content, prefer `InputRichMessage.html` with explicit
  escaping unless the source is already validated Markdown.
- Media in Rich Messages must be separate media blocks and only supports HTTP
  and HTTPS URLs.
- If a rich message contains media, the bot must have the right to send that
  media type to the target chat.
- `<tg-thinking>` / `RichBlockThinking` is draft-only and may be used only with
  `sendRichMessageDraft`; it is not received in persisted messages.

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

## Legacy Markdown (parse_mode: "Markdown")

Legacy `parse_mode: "Markdown"` is retained only for backward compatibility.
It does not support nested entities, underline, strikethrough, spoiler,
blockquote, expandable blockquote, custom emoji, or date-time entities. Use
`MarkdownV2` for basic messages, or `InputRichMessage.markdown` for Bot API
10.1+ Rich Messages.

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
- v10.1 (Jun 11 2026): Rich Messages (`sendRichMessage`, `sendRichMessageDraft`, `InputRichMessage.markdown/html`), join request queries, poll links
- v10.0 (May 8 2026): Guest mode, media/live photos in polls, live photos, bot-to-bot communication, managed bot access settings
- v9.6 (Apr 3 2026): Managed bots, prepared keyboard buttons, multiple correct quiz answers, richer poll controls
- v9.5 (Mar 1 2026): `date_time` message entity, `sendMessageDraft` for all bots, chat member tags
- v9.4 (Feb 9 2026): Button styling (`style`, `icon_custom_emoji_id`), custom emoji in bot messages, profile media methods
- v9.3 (Dec 31 2025): Message draft streaming, private chat topics, gift API updates

**Use Context7 to check current version and new features.**
