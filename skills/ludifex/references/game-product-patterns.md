# Game Product Patterns

Use this file for Telegram Mini App game concepts, screen maps, first-session flows, logic, and implementation briefs.

## Product Frame

Define these before proposing screens:

| Field | Question |
|---|---|
| Player fantasy | What does the player feel they are becoming or mastering? |
| Primary action | What is the repeatable action that creates progress? |
| Reward | What does the player receive immediately and later? |
| Progression | What changes after repeated play? |
| Social layer | Why would a player invite, challenge, compare, or cooperate? |
| Economy boundary | What is cosmetic, in-game utility, redeemable, paid, or crypto-linked? |
| Session length | What is satisfying in 30 seconds, 3 minutes, and one day? |

## Core Loop Patterns

| Pattern | Best For | Loop | Watch Out |
|---|---|---|---|
| Tap/idle | Casual mass-market TMA | Open -> tap/action -> earn -> upgrade -> return when energy/refill resets | Boredom if progress is only numbers. |
| Session challenge | Skill/puzzle/arcade | Start round -> perform -> score -> reward -> retry/share | Needs quick restart and fair failure feedback. |
| Async PvP | Chess, duels, turn games | Invite/match -> move -> notify -> respond -> result | Needs robust state, reminders, timeout rules. |
| Collection | Cards, items, characters | Earn/drop -> collect -> complete set -> unlock utility/status | Avoid opaque odds and paywalled completion traps. |
| Quest/referral | Growth support layer | Task -> proof/action -> reward -> next task | Must not overwhelm the main game. |

## Essential Screens

| Screen | Purpose | Primary Action | Required States |
|---|---|---|---|
| Launch/Auth | Initialize Telegram context, session, language, theme, server state. | Continue automatically or retry. | loading, unsupported client, auth failed, maintenance. |
| First Action | Let the player do the core action before reading long explanations. | Play / Tap / Start Round / Claim Starter Reward. | new user, returning user, blocked/limited user. |
| Home | Show player state and next best action. | Main play action. | ready, depleted, reward available, upgrade available, offline gain. |
| Game | Execute the core mechanic. | Perform the action. | active, paused, failed, completed, disconnected. |
| Result | Close the loop and explain what changed. | Claim / Upgrade / Play Again. | win, loss, partial reward, capped, anti-abuse review. |
| Progression | Make long-term growth legible. | Upgrade / Unlock / View Next. | affordable, locked, maxed, insufficient resource. |
| Tasks | Optional growth and habit layer. | Complete task. | available, in progress, verifying, complete, expired. |
| Social | Invite, challenge, team, share, leaderboard. | Invite / Challenge / Share Result. | no friends, invite pending, ranked, opt-out. |
| Prizes/Wallet | Explain prize balance, eligibility, claim path. | Claim / Connect / View Rules. | eligible, not eligible, pending, rejected, limit reached. |
| Settings | Language, notifications, support, legal, privacy. | Change setting / Contact support. | saved, failed, unavailable. |

## First Session Blueprint

1. Load in under the smallest practical bundle budget and show a skeleton, not a blank page.
2. Detect language and Telegram theme before rendering final UI.
3. Show one sentence of context only if the action is not obvious.
4. Let the player complete the first action within 10-20 seconds.
5. Show a result screen that names the reward and the next step.
6. Introduce progression after the first reward, not before it.
7. Ask for invite/notification/payment only after the player has received value.

## Game Logic Checklist

- Server owns balances, energy, rewards, prizes, quests, cooldowns, and anti-abuse decisions.
- Client owns animation, optimistic feedback, and display, but must reconcile with server state.
- Every economy mutation has an idempotency key or transaction boundary.
- Rewards are typed: soft currency, hard currency, XP, item, access, prize eligibility, off-chain/on-chain value.
- Every cap has user-facing copy: daily cap, energy cap, claim cap, task limit, anti-fraud review.
- Randomness that affects value must be auditable or clearly cosmetic.
- Referral rewards should prevent self-referral, farming, and unverifiable task completion.
- Admin-tuned copy/rewards should use structured fields, not raw HTML.

## Screen Spec Template

```
Screen: [name]
Purpose: [one sentence]
Player state: [new/returning/capped/eligible/etc.]
Primary action: [button label]
Secondary actions: [max 2]
Visible data: [balances, timer, reward, rank, progress]
States: [loading, empty, error, success, disabled]
Copy keys: [title, subtitle, CTA, success, error, note]
Telemetry: [viewed, action clicked, completed, failed]
Risks: [abuse, confusion, ethical issue]
Delegation: [PRAECO/AEDILIS/ALEATOR/CODER/PICTOR]
```
