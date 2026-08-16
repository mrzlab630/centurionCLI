# grammY Framework — Patterns Reference

> Core patterns for our stack. For method signatures and edge cases, use Context7.

## Plugin Selection Matrix

| Need | Plugin | Key Benefit |
|---|---|---|
| Multi-step forms/wizards | **Conversations v2** | Replay engine, async/await flow |
| Hierarchical menus | **Menu** | Stateless, dynamic, fingerprints |
| Persistent user state | **Session** | Multi-backend (memory, Redis, PG) |
| Auto-retry on errors | **Auto-retry** | Handles 429, network errors |
| Rate limit compliance | **Transformer Throttler** | Per-chat/global throttling |
| Concurrent polling | **Runner** | Multi-worker, graceful shutdown |
| Rich context methods | **Hydrate** | ctx.editMessageText() shortcut |
| Command parsing | **Commands** | Localized commands, deep links |
| Internationalization | **I18n (Fluent)** | Type-safe, pluralization |
| File handling | **Files** | getFile + download helper |
| Chat members tracking | **Chat Members** | Join/leave events |

## Conversations v2 (Multi-Step Flows)

### Core Pattern
```typescript
import { conversations, createConversation } from '@grammyjs/conversations';

// 1. Register middleware
bot.use(conversations());

// 2. Define conversation
async function buyFlow(conversation, ctx) {
  // Step 1: Ask for amount
  await ctx.reply('Enter amount in SOL:');
  const amountCtx = await conversation.waitFor('message:text');
  const amount = parseFloat(amountCtx.message.text);

  if (isNaN(amount) || amount <= 0) {
    await ctx.reply('Invalid amount. Try again.');
    return; // Exit conversation
  }

  // Step 2: Confirm
  await ctx.reply(`Buy ${amount} SOL? [Yes/No]`);
  const confirmCtx = await conversation.waitFor('message:text');

  if (confirmCtx.message.text.toLowerCase() === 'yes') {
    await executeBuy(amount);
    await ctx.reply('Done!');
  } else {
    await ctx.reply('Cancelled.');
  }
}

// 3. Register
bot.use(createConversation(buyFlow));

// 4. Enter conversation
bot.command('buy', async (ctx) => {
  await ctx.conversation.enter('buyFlow');
});
```

### Key Concepts
- **Replay engine:** On each message, conversation replays from start. Side effects (DB writes) must be inside `conversation.external()`.
- **conversation.external():** Wraps side effects that should only run once.
- **conversation.waitFor():** Returns ctx matching filter. Conversation suspends.
- **Timeout:** `conversation.waitFor('message:text', { timeout: 60_000 })` — auto-exit after 60s.
- **Parallel:** Multiple conversations can run per user (use unique names).
- **Form fields:** `conversation.form.text()`, `.number()`, `.select()` — built-in validation.

### Gotchas
- **No closures over mutable state** — Replay will re-execute outer scope.
- **Side effects in external()** — DB writes, API calls MUST be wrapped.
- **Session access** — Use `conversation.session` not `ctx.session`.
- **Error handling** — Wrap in try/catch, conversation exits on unhandled error.

## Menu Plugin (Stateless Menus)

### Core Pattern
```typescript
import { Menu } from '@grammyjs/menu';

const settingsMenu = new Menu('settings')
  .text('Language', (ctx) => ctx.reply('Select language'))
  .row()
  .text(
    (ctx) => ctx.session.notifications ? '🔔 ON' : '🔕 OFF',
    async (ctx) => {
      ctx.session.notifications = !ctx.session.notifications;
      ctx.menu.update(); // Re-render with new state
    }
  )
  .row()
  .back('← Back');  // Navigate to parent menu

const mainMenu = new Menu('main')
  .submenu('⚙️ Settings', 'settings')
  .row()
  .text('ℹ️ Help', (ctx) => ctx.reply('Help text'));

// Register hierarchy
mainMenu.register(settingsMenu);
bot.use(mainMenu);
```

### Key Concepts
- **Stateless:** Menu state lives in message markup, not server.
- **Fingerprints:** Menu detects outdated keyboards and auto-refreshes.
- **Dynamic ranges:** `.dynamic()` for variable-length button lists (pagination).
- **Payload:** `.text({ text: 'btn', payload: 'data' })` — embed data in callback.
- **Submenu navigation:** `.submenu()` pushes, `.back()` pops.
- **ctx.menu.update():** Re-renders current menu (for toggle state changes).
- **ctx.menu.close():** Removes keyboard entirely.

### Dynamic Range (Pagination)
```typescript
const listMenu = new Menu('items')
  .dynamic((ctx, range) => {
    const page = ctx.session.page || 0;
    const items = getItems(page, 5);
    for (const item of items) {
      range.text(item.name, (ctx) => handleItem(ctx, item.id)).row();
    }
    // Navigation
    if (page > 0) range.text('◀️', (ctx) => { ctx.session.page--; ctx.menu.update(); });
    range.text(`${page + 1}`, () => {});
    if (hasMore) range.text('▶️', (ctx) => { ctx.session.page++; ctx.menu.update(); });
  });
```

## Session Plugin

### Multi-Session Pattern
```typescript
bot.use(session({
  type: 'multi',
  custom: {
    // Per-key session configs
    user: {
      initial: () => ({ language: 'en', notifications: true }),
      storage: redisAdapter,  // Persistent
    },
    temp: {
      initial: () => ({ step: 0 }),
      storage: new MemorySessionStorage(),  // Volatile
    },
  },
}));

// Access: ctx.session.user.language, ctx.session.temp.step
```

### Key Concepts
- **Lazy sessions:** `lazy: true` — only fetched if accessed. Saves DB reads.
- **TTL:** `storage: redisAdapter({ ttl: 3600 })` — auto-expire idle sessions.
- **Migration:** `migrate: (old) => ({ ...old, newField: 'default' })` — schema updates.
- **Redis adapter:** `@grammyjs/storage-redis` — production standard.

## Error Handling

### Bot-Level Error Handler
```typescript
bot.catch((err) => {
  const ctx = err.ctx;
  const e = err.error;

  if (e instanceof GrammyError) {
    // Telegram API error
    if (e.error_code === 403) {
      // Bot blocked by user — remove from DB
    } else if (e.error_code === 429) {
      // Rate limited — auto-retry handles this
    }
  } else if (e instanceof HttpError) {
    // Network error — transient
  } else {
    // Application error — log and alert
    console.error('Unhandled error:', e);
  }
});
```

### Per-Handler Error Pattern
```typescript
async function safeHandler(ctx) {
  try {
    await riskyOperation();
  } catch (e) {
    await ctx.reply('❌ Something went wrong. Please try again.', {
      reply_markup: errorKeyboard,
    });
    // Log error for debugging
    logger.error('Handler failed', { userId: ctx.from?.id, error: e });
  }
}
```

## TypeScript Context

### Custom Context
```typescript
import { Context, SessionFlavor } from 'grammy';
import { ConversationFlavor } from '@grammyjs/conversations';
import { HydrateFlavor } from '@grammyjs/hydrate';

interface SessionData {
  page: number;
  language: string;
  walletId: number | null;
}

type BotContext = HydrateFlavor<
  Context &
  SessionFlavor<SessionData> &
  ConversationFlavor
>;

const bot = new Bot<BotContext>(token);
```

## Middleware Order (Critical)

```typescript
// Order matters! Top = first executed
bot.use(autoRetry());           // 1. Retry failed API calls
bot.use(hydrate());             // 2. Rich context methods
bot.use(session({ ... }));      // 3. Load session
bot.use(conversations());       // 4. Conversation engine (needs session)
bot.use(mainMenu);              // 5. Menu handlers
bot.use(createConversation(f)); // 6. Register conversations
// ... then command handlers, callback handlers, etc.
```

## Filter Queries (Common)

```typescript
bot.on('message:text')           // Text messages
bot.on('callback_query:data')    // Inline button presses
bot.on('message:photo')          // Photo messages
bot.on(':contact')               // Contact shared
bot.on(':location')              // Location shared
bot.on('chat_member')            // Join/leave events
bot.on('pre_checkout_query')     // Payment pre-checkout
bot.on('message:web_app_data')   // Mini App data received
bot.hears(/regex/)               // Regex match on text
bot.command('start')             // /start command
bot.callbackQuery('exact_match') // Exact callback_data
bot.callbackQuery(/^prefix_/)    // Regex callback_data
```
