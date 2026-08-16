# Source Lessons

Use this file when the user asks to ground game guidance in the GitHub repositories previously selected for Telegram Mini App game skill-building. These are pattern sources, not code sources.

## Source Rule

- Extract patterns, never copy code, screen text, branding, art, economy numbers, or distinctive feature names.
- Treat repositories without a clear license as read-only inspiration.
- Convert observed patterns into original product requirements, screen specs, copy briefs, or implementation briefs.

## Repository Pattern Map

| Repository | Use For | Caution |
|---|---|---|
| `Telegram-Mini-Apps/reactjs-template` | Baseline React/Vite/TypeScript Mini App structure, SDK integration mindset, launch hygiene. | Template only; it is not a game design source. |
| `telegram-mini-apps-dev/TelegramUI` | Telegram-native component expectations: buttons, lists, cells, theme-aware UI, mobile density. | Do not force generic web dashboard patterns into Telegram. |
| `clawvader-tech/hermes-telegram-miniapp` | Mobile-first multi-screen app flow and compact dashboard thinking. | Treat as UI inspiration, not game mechanics authority. |
| `nikandr-surkov/Hamster-Kombat-Telegram-Mini-App-Clone` | Tap/idle loop, currency visibility, boosts, tasks, invite/social hooks, frequent reward feedback. | No license observed; do not reuse code or copy. Avoid shallow tap-to-earn cloning. |
| `nikandr-surkov/Notcoin-Telegram-Mini-App-Clone` | First-action immediacy, simple progress feedback, lightweight game economy, viral mechanics. | No license observed; do not reuse code or copy. Avoid opaque token promises. |
| `pkozlov/ChessBot` | Real game flow: matchmaking, shared links, async state, observers, notifications. | Chess-specific rules do not transfer to casual tap games unchanged. |
| `Kennix88/Token-Giver` | Full-stack play-to-earn structure, admin/control surface, rewards and tasks as configurable product data. | AGPL-3.0; strong license obligations. Study concepts only unless license fit is explicit. |
| `quinnkeast/product-language-framework` | Product language system: voice, tone, naming, message consistency, copy governance. | Use as a method reference, not as ready-made game copy. |

## Synthesized Lessons

1. The first screen should make the game playable, not explain the product like a landing page.
2. The home screen should expose the current player state: energy, currency, level, next reward, and one primary action.
3. The game action should produce feedback within one tap/click: animation, number change, progress movement, or result state.
4. Rewards must have visible conditions: what is earned, when it unlocks, and whether it is cosmetic, in-game, withdrawable, or promotional.
5. Social mechanics should create a player benefit, not just ask for invites.
6. Admin/configurable copy and rewards are safer than hardcoded text when the game will be multilingual or frequently tuned.
7. Telegram-native UI matters: compact cells, clear touch targets, theme compatibility, share/invite affordances, and fast loading beat ornamental web layouts.
