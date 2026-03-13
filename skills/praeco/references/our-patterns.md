# Our Telegram Bot — Codebase Patterns

> Project-specific conventions. ALWAYS follow these when modifying our bot.
> Base path: `/home/yokinaboy/sniper/telegram/base/src/`

## Navigation System (NavigationManager)

### Architecture
Our bot uses a custom **NavigationManager** — NOT grammY Menu plugin.

```
NavigationManager (singleton)
├── NavigationState (per user)
│   ├── userId, chatId, messageId
│   ├── stack: NavigationFrame[]    ← screen history
│   ├── inputMode: InputContext     ← waiting for text?
│   └── locked: boolean            ← prevents concurrent edits
├── navTo(ctx, screen, data)        ← push screen
├── navBack(ctx)                    ← pop stack
├── navRefresh(ctx)                 ← re-render current
├── navRequestInput(ctx, prompt, field, validator) ← text input
└── navReply(ctx, options)          ← smart edit/send
```

**Files:**
- `navigation/NavigationManager.ts` — State management
- `navigation/navReply.ts` — Smart reply (edit-or-send), input handling
- `navigation/renderer.ts` — Screen registry and rendering

### Screen Registration Pattern
```typescript
// In each command file:
async function renderMyScreen(ctx: BotContext, data: Record<string, any>): Promise<void> {
  const keyboard = new InlineKeyboard()
    .text('Action', 'callback_data')
    .row()
    .text('🚀 Menu', CallbackAction.START);

  await navReply(ctx, { text: 'Screen content', keyboard, parseMode: 'HTML' });
}

registerScreen('myScreen', renderMyScreen);
registerInputProcessor('myScreen', async (ctx, field, value) => {
  // Handle text input result
});
```

### navReply Behavior
1. Tries to **edit** existing message (if messageId tracked and not modified)
2. Falls back to **send new** if edit fails or `forceNew: true`
3. Auto-adds **🔙 Back** button if `addBackButton !== false` and stack has history
4. Calls `answerCallbackQuery()` to clear loading spinner

## Callback Data Conventions

### Format
```
[PREFIX]_[ID]               → wallet_manage_view_123
[PREFIX]_[KEY]_[ID]         → copy_trading_wallets_w_456
[PREFIX]_[param1]_[param2]  → copy_trading_settings_buys_toggle_s1_t2_u3
```

### CallbackAction Enum
Defined in `types/index.ts`. All callback prefixes are enum values:
```typescript
export enum CallbackAction {
  START = 'start',
  WALLET = 'wallet',
  WALLETview = 'wallet_manage_view',
  WALLETcreate = 'wallet_manage_create',
  WALLETrename = 'wallet_manage_rename',
  WALLETdelete = 'wallet_manage_delete',
  WALLETdeleteConfirm = 'wallet_manage_delete_confirm',
  WALLETtokensPagination = 'wallet_tokens_pagination',
  COPYTRADING = 'copy_trading',
  COPYTRADINGwallets = 'copy_trading_wallets',
  COPYTRADINGwalletsForWallet = 'copy_trading_wallets_w',
  COPYTRADINGsettingsBuy = 'copy_trading_settings_buys_toggle',
  COPYTRADINGsettingsSEll = 'copy_trading_settings_sell_toggle',
  RENT_RECLAIM = 'rent_reclaim',
  RENT_RECLAIM_CONFIRM = 'rent_reclaim_confirm',
  // ... more in types/index.ts
}
```

### ID Extraction Utilities (`utilities/callbackUtils.ts`)
```typescript
extractCallbackId(callbackData, prefix)     // → number | null
extractCallbackValue(callbackData, prefix)  // → string | null
buildCallbackWithId(prefix, id)             // → string
```

### Multi-Parameter Encoding
```typescript
const idparams = [`s${settingsId}`, `t${targetWalletId}`, `u${userWalletId}`].join('_');
const callback = CallbackAction.COPYTRADINGsettingsBuy + '_' + idparams;
// Result: 'copy_trading_settings_buys_toggle_s1_t2_u3'
```

**RULE:** Always use CallbackAction enum. Never hardcode callback strings.
**RULE:** Keep callback_data under 40 bytes (leave room for IDs).

## Message Formatting

### formatTreeBlock (`utilities/formatTreeBlock.ts`)
```typescript
formatTreeBlock({
  header: '🪙 <b>Token Name</b>',
  lines: [
    '💰 Balance: 1.234 SOL',
    '📊 Value: $123.45',
    null,  // null/undefined → skipped
    '🔗 <a href="https://solscan.io/token/...">Solscan</a>',
  ],
  footer: '⚡Buy ▫️ Sell ▫️ Withdraw',
});
// Output:
// ╭─ 🪙 <b>Token Name</b>
// ├ 💰 Balance: 1.234 SOL
// ├ 📊 Value: $123.45
// ├ 🔗 <a href="...">Solscan</a>
// ╰─ ⚡Buy ▫️ Sell ▫️ Withdraw
```

### sendMessage (`utilities/sendMessage.ts`)
- Auto-splits at 4096 char limit
- Breaks at newlines or spaces for readability
- Keyboard attached only to last chunk
- Retry logic for 429 rate limiting

### Number Formatting
- SOL amounts: `1.2345 SOL` (4 decimals)
- Percentages: `42.5%` (1 decimal)
- Addresses: `7A77...K8Dz` (4+4 chars), full in `<code>` for copy
- USD: `$1,234.56`

## Keyboard Building

### createInlineKeyboard (`utilities/createInlineKeyboard.ts`)
```typescript
const keyboard = createInlineKeyboard([
  [{ text: '🚀 Menu', action: CallbackAction.START }],
  [
    { text: '💰 Buy', callback_data: 'swap_buy_token' },
    { text: '💸 Sell', callback_data: 'swap_sell_token' },
  ],
]);
```

### createErrorKeyboard (`utilities/createErrorKeyboard.ts`)
```typescript
const kb = createErrorKeyboard(CallbackAction.WALLET);
// Returns: [[Menu button, Back button]]
```

### Dynamic Grid Pattern
```typescript
// From copyTradinWalletsKeyboard.ts
interface IButtonGroup {
  group: string;
  buttons: IButtonItem[];  // { condition, button, separateRow }
}
// Filter by condition → 2-button rows → separateRow = full width
```

### Main Menu (`commands/start/getMainMenuButtons.ts`)
```typescript
[
  [{ text: "💰 Wallet", action: CallbackAction.WALLET }],
  [
    { text: "🔍 Analyze", action: CallbackAction.ANALYZE },
    { text: "👥 Copy Trading", action: CallbackAction.COPYTRADING },
  ],
  [
    { text: "⚙️ Settings", action: CallbackAction.SETTINGS },
    { text: "📩 Support", action: CallbackAction.SUPPORT },
  ],
]
```

## Process Indicators (`utilities/processIndicator.ts`)

```typescript
// Quick loading animation
await quickIndicator(ctx, asyncOperation, "Loading...");

// Multi-step with progress messages
await steppedIndicator(ctx, asyncOperation, [
  "Step 1: Validating...",
  "Step 2: Processing...",
  "Step 3: Finalizing...",
]);

// Simple emoji animation
await emojiIndicator(ctx, asyncOperation, ["⏳", "⌛"]);
```

## Message Helpers (`utilities/messageHelpers.ts`)

Pre-defined navigation objects:
```typescript
NAV_ACTIONS.MENU         // { text: '🚀 Menu', callback_data: 'start' }
NAV_ACTIONS.WALLET       // { text: '👛 Wallets', callback_data: 'wallet' }
NAV_ACTIONS.BACK_WALLET  // { text: '🔙 Back', callback_data: 'wallet' }
NAV_ACTIONS.BACK_MENU    // { text: '🔙 Menu', callback_data: 'start' }

sendErrorMessage(ctx, error, backAction?)
sendSuccessMessage(ctx, message, actions?)
sendConfirmationMessage(ctx, message, confirmAction, cancelAction?)
```

## Callback Handler (`handlers/callbackHandler.ts`)

```typescript
// CRITICAL: answerCallbackQuery IMMEDIATELY
try { await ctx.answerCallbackQuery(); } catch {}

// Then route by callback_data
if (callbackData === NAV_BACK) { ... }
const commandExecuted = await executeCommand(callbackData, ctx);
```

## Input Handling

### navRequestInput (text input with validation)
```typescript
await navRequestInput(ctx, 'Enter slippage %:', 'slippage:5', (text) => ({
  valid: !isNaN(parseFloat(text)) && parseFloat(text) > 0,
  error: 'Enter a positive number',
  value: parseFloat(text),
}));
// Prompt message sent, cleaned up after response
// Result goes to registerInputProcessor handler
```

### Force Reply (legacy pattern, still used for rename)
```typescript
await ctx.reply('Enter new name:', {
  reply_markup: {
    force_reply: true,
    selective: true,
    input_field_placeholder: 'Wallet name...',
  },
});
```

## Deep Links (`utilities/creatActionLink.ts`)

```typescript
creatActionLink({
  botUsername: 'mybot',
  mint: 'TokenMint123',
  command: 'swap_tb',  // swap_tb | swap_ts | wth_t | wth_s
  lable: 'Buy',
});
// Result: <a href="https://t.me/mybot?start=swap_tb_TokenMint123">Buy</a>
```

## Emoji Conventions (Mandatory)

| Concept | Emoji | Usage |
|---|---|---|
| Main menu | 🚀 | Menu button |
| Wallet | 💰 👛 | Wallet section |
| Buy | 💰 ⚡ | Buy actions |
| Sell | 💸 | Sell actions |
| Analyze | 🔍 | Analysis |
| Copy trading | 👥 | Copy trading |
| Settings | ⚙️ | Settings |
| Success | ✅ | Confirmation |
| Error | ❌ | Error state |
| Warning | ⚠️ | Warning |
| Back | 🔙 | Navigation back |
| Previous/Next | ◀️ ▶️ | Pagination |
| Loading | ⏳ ⌛ | Process indicator |
| ON/OFF | 🟢 🔴 | Toggle state |
| Delete | 🗑 | Destructive action |
| Refresh | 🔄 | Retry/refresh |

## New Command Checklist

When adding a new command/screen:
1. [ ] Define CallbackAction enum values in `types/index.ts`
2. [ ] Create render function with `registerScreen()`
3. [ ] Add input processor if text input needed
4. [ ] Use `navReply()` for all message sending
5. [ ] Use `createInlineKeyboard()` or grammY `InlineKeyboard` for buttons
6. [ ] Call `answerCallbackQuery()` in callback handler
7. [ ] Add error handling with `createErrorKeyboard()`
8. [ ] Keep callback_data under 40 bytes
9. [ ] Test on mobile (touch targets, text overflow)
10. [ ] Add to callback router in `callbackHandler.ts`
