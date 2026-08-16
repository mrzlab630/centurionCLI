# Interface Microcopy

Use this file for CTA, labels, help text, tooltips, onboarding, empty states, error states, success states, confirmations, and settings copy.

## Table Of Contents

- Microcopy Principles
- CTA
- Labels And Navigation
- Empty States
- Error States
- Success States
- Confirmations
- Onboarding
- Tooltips And Help Text
- Output Template

## Microcopy Principles

- Put the user's next step first.
- Name the object/action, not the internal system.
- Be specific before being short; then make it shorter.
- Use the same term for the same concept everywhere.
- Avoid blame, shame, and fake urgency.
- Write every state: loading, empty, error, success, disabled, partial.

## CTA

CTA formula:

`Verb + object` when context is not enough. Use one verb per state.

| Intent | Strong CTA | Weak CTA |
|---|---|---|
| Start | Start game / Play / Start round | Continue |
| Claim | Claim reward / Collect coins | Get it |
| Recover | Try again / Refresh / Contact support | OK |
| Configure | Save settings / Add language | Done |
| Learn rules | View rules / Check eligibility | More |
| Destructive | Delete account / Cancel order | Yes |

Rules:

- Do not use `Claim` unless the user is eligible now.
- Do not use `Continue` if the destination is unclear.
- Destructive CTA must name the consequence.
- Disabled CTA needs helper text explaining why.

## Labels And Navigation

Navigation labels should be nouns or stable destinations: `Home`, `Play`, `Tasks`, `Prizes`, `Wallet`, `Profile`, `Settings`.

Avoid branded metaphors when the user needs orientation. Invented names can work only after the base meaning is visible.

## Empty States

Empty state formula:

`Current state -> why it matters -> useful next action.`

Examples as patterns:

- Title: `No rewards yet`
- Body: `Play a round or complete a task to earn your first reward.`
- CTA: `Start playing`

Avoid:

- `Nothing here`
- `No data`
- Empty illustration with no action.

## Error States

Error formula:

`What happened -> what remains safe -> recovery action.`

Patterns:

- Network: `Connection lost. Your progress is saved. Try again when you're back online.`
- Validation: `Enter a valid email address.`
- Permission: `You do not have access to this area.`
- Rate limit: `Too many attempts. Try again in {timeLeft}.`
- Payment/prize: `We could not verify this claim yet. Check the rules or try again later.`

Avoid:

- `Oops!`
- `Something went wrong` as the only message.
- Blaming copy like `You failed`.

## Success States

Success formula:

`What changed -> where to go next.`

Examples as patterns:

- `Reward claimed. Your balance is updated.`
- `Settings saved.`
- `Task complete. Your bonus is ready.`

Avoid confetti language for routine system actions.

## Confirmations

Confirmation copy must include:

- Action being confirmed.
- Consequence.
- Primary CTA naming the consequence.
- Safe cancel path.

Example pattern:

```
Title: Cancel this claim?
Body: You can start a new claim later, but this review will stop now.
Primary: Cancel claim
Secondary: Keep review
```

## Onboarding

- Lead with the first meaningful action.
- Avoid long feature tours before value.
- Explain one concept at a time.
- Use progressive disclosure for advanced settings.
- Ask for notifications, invites, wallet, or payments after value is delivered.

## Tooltips And Help Text

Use tooltips for extra explanation, not required instructions. Required instructions should be visible.

Good tooltip content:

- Defines unfamiliar icon or term.
- Explains constraint or calculation.
- Gives format example.

Avoid tooltips for errors, legal terms, or critical eligibility rules.

## Output Template

```
Interface Microcopy: [screen/feature]

Context:
[surface, user state, intent]

Recommended Copy:
| Element | Copy | Why |
|---|---|---|

State Copy:
| State | Title | Body | CTA |
|---|---|---|---|

Rejected Copy:
| Copy | Problem |
|---|---|

Localization Notes:
[placeholders, glossary terms, length risk]
```
