# Game Copy Playbook

Use this file for names, descriptions, prize language, CTA, onboarding text, empty/error/success states, and localization-ready game UX copy.

## Table Of Contents

- Copy Standards
- Naming Rules
- Length Budgets
- CTA Verb Bank
- Prize Copy Rules
- Screen Copy Set
- Localization Notes
- Naming Output Template

## Copy Standards

- Make the next action obvious.
- Say what the player gets and when they get it.
- Avoid hype that hides conditions: "guaranteed", "free money", "last chance", "only today" unless literally true and enforceable.
- Prefer short, concrete labels over brand poetry inside controls.
- Keep all text localizable: no concatenated strings, no embedded grammar assumptions, named placeholders, plural-ready messages.
- Write for Telegram mobile first: short labels, scannable titles, clear state notes.

## Naming Rules

| Thing | Good Pattern | Avoid |
|---|---|---|
| Main tab | Concrete noun: `Home`, `Play`, `Tasks`, `Prizes`, `Profile` | Abstract brand words that hide purpose. |
| Primary CTA | Verb + object when needed: `Play`, `Claim`, `Upgrade`, `Start Duel` | Vague actions: `Go`, `Do it`, `Continue` when state is unclear. |
| Reward | Value + type: `Daily Bonus`, `Level Reward`, `Invite Bonus` | Fake financial language or unclear tokens. |
| Feature | Player outcome: `Boosts`, `Quests`, `Leaderboard`, `Inventory` | Internal terms: `Multiplier Engine`, `Reward Processor`. |
| Error | Problem + recovery: `Connection lost. Try again.` | Blame or dead ends: `Failed`, `Invalid`. |

## Length Budgets

Use these as starting constraints, then check actual UI:

| Element | Target |
|---|---|
| Bottom tab label | 4-12 characters in English; allow longer localized variants. |
| Primary button | 1-3 words. |
| Section title | 2-5 words. |
| Card title | 20-35 characters where possible. |
| Subtitle/help text | 60-120 characters. |
| Error text | Problem + recovery in 1-2 short sentences. |
| Prize note | Conditions visible before action; keep under 180 characters if shown inline. |

## CTA Verb Bank

| Intent | CTA Options |
|---|---|
| Start play | `Play`, `Start`, `Start Round`, `Roll`, `Enter Arena`, `Begin Challenge` |
| Claim reward | `Claim`, `Collect`, `Take Reward`, `Open Reward` |
| Progress | `Upgrade`, `Unlock`, `Level Up`, `Boost`, `Train` |
| Social | `Invite`, `Challenge`, `Share Score`, `Join Team` |
| Recovery | `Try Again`, `Reconnect`, `Refresh`, `Back Home` |
| Payment/prize | `View Rules`, `Check Eligibility`, `Claim Prize`, `Connect Wallet` |

Choose verbs that match the actual state. Do not use `Claim` before eligibility is confirmed.

## Prize Copy Rules

Every prize description must answer:

1. What is the prize?
2. Is it in-game, cosmetic, promotional, redeemable, crypto, or Telegram Stars?
3. What action or condition unlocks it?
4. Is there a daily/weekly/event cap?
5. When does it arrive?
6. Can it be revoked, reviewed, or expire?

Example structure:

```
Title: Level 5 Reward
Description: Reach Level 5 to unlock 250 coins and a profile badge.
Note: Coins are added instantly. Badges are cosmetic and cannot be withdrawn.
CTA: View Progress
```

## Screen Copy Set

For each screen, produce these fields when practical:

| Key | Purpose |
|---|---|
| `title` | Orient the player. |
| `subtitle` | Explain current state or benefit. |
| `primaryCta` | One main action. |
| `secondaryCta` | Optional escape/action. |
| `emptyTitle` / `emptyMessage` | Useful zero state. |
| `successTitle` / `successMessage` | Name what changed. |
| `errorTitle` / `errorMessage` | Problem + recovery. |
| `legalNote` / `prizeNote` | Conditions, eligibility, limits. |

## Localization Notes

- Define a glossary before translating: currency names, prize names, rank names, item names, player verbs.
- Avoid idioms, jokes, puns, and cultural references in core controls.
- Use ICU plural/select or an equivalent system for counts, gender/role variants, and dynamic reward text.
- Prefer placeholders like `{amount}`, `{currency}`, `{level}`, `{timeLeft}`.
- Do not split sentences across keys if grammar changes by language.
- Review long-language expansion for German, Russian, Turkish, Spanish, and Arabic if supported.

## Naming Output Template

```
Context: [screen/feature/player state]
Goal: [what the copy must make the player do or understand]

Recommended:
1. [Name] - [why]

Alternatives:
| Option | Tone | Best For | Risk |
|---|---|---|---|

CTA:
| Button | Intent | Notes |
|---|---|---|

Microcopy:
Title: ...
Subtitle: ...
Success: ...
Error: ...
Prize note: ...
```
