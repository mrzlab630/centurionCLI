# Translation Quality

Use this file for professional interface translation, glossary, tone, context, review, and translator handoff.

## Table Of Contents

- Quality Standard
- Translation Workflow
- Glossary
- Context Notes
- UI Copy Rules
- CTA Translation
- Error And Empty States
- Game And Reward Copy
- Review Checklist
- Output Template

## Quality Standard

Professional interface translation must be:

- Accurate to product intent, not word-for-word source order.
- Natural for the target locale.
- Consistent with glossary and tone.
- Short enough for the component.
- Safe for placeholders and dynamic values.
- Clear about costs, rewards, limits, eligibility, and irreversible actions.
- Reviewed in the actual UI or screenshots, not only in a spreadsheet.

## Translation Workflow

1. Gather source strings with screen names, screenshots, states, and character limits.
2. Define product voice: formal/casual, playful/serious, expert/simple, region-specific terms.
3. Build glossary and non-translatable list.
4. Translate by message context and user intent.
5. Check placeholder parity and plural/select rules.
6. Review in UI with long text, narrow widths, and real data.
7. Mark native-review or legal-review flags before launch.

## Glossary

Every multilingual product should have a glossary:

| Term | Meaning | Translate? | Notes |
|---|---|---|---|
| Energy | Resource spent to play. | Yes | Keep consistent across game, wallet, errors. |
| Stars | Telegram Stars payment unit. | Usually no | Follow Telegram terminology per locale. |
| Reward | Earned in-game value. | Yes | Do not imply cash-out unless true. |
| Claim | User takes an available reward. | Yes | Only use when eligibility is confirmed. |
| Wallet | In-app balance area or crypto wallet. | Depends | Disambiguate product wallet vs blockchain wallet. |

Rules:

- Include forbidden translations for legal/product terms.
- Document abbreviations and capitalization.
- Define whether terms are formal, playful, technical, or user-friendly.
- Keep glossary near translation workflow, not buried in code.

## Context Notes

Translator context should include:

- Screen or component name.
- User state: new user, blocked user, winner, empty wallet, failed payment, admin.
- Action intent: inform, warn, confirm, recover, sell, reward.
- Variables and examples: `{amount}=250`, `{currency}=coins`, `{timeLeft}=03:15`.
- Length limit and UI surface: button, tab, toast, modal title, table header.
- Tone notes and terms not to translate.

## UI Copy Rules

- Keep button labels action-oriented.
- Preserve severity in warning/error copy.
- Avoid idioms, sarcasm, puns, and culture-specific jokes in core UI.
- Avoid fake urgency, fake scarcity, and exaggerated reward language.
- Do not translate brand names, product names, URLs, or code-like identifiers unless required.
- Do not use punctuation or casing as the only way to communicate importance.

## CTA Translation

CTA should match state:

| State | Good CTA Intent | Avoid |
|---|---|---|
| User can start | Start/Play/Open | Continue when destination is unclear. |
| Reward available | Claim/Collect | Claim if reward still needs review. |
| User lacks resource | Get energy/View tasks | Pay now as only path unless true. |
| Error happened | Try again/Refresh/Contact support | Failed/OK as dead ends. |
| Destructive action | Delete/Confirm cancel | Ambiguous Yes/No without consequence. |

## Error And Empty States

Error copy formula:

`What happened -> why if useful -> what the user can do now.`

Empty state formula:

`Current state -> value of next action -> CTA.`

Do not blame the user unless the input is clearly invalid and recoverable.

## Game And Reward Copy

- Separate in-game value from real-world/withdrawable value.
- Make eligibility and caps explicit before the action.
- Do not promise money, winnings, guaranteed value, or scarcity unless the system enforces it.
- Use consistent verbs for earning, claiming, upgrading, unlocking, and withdrawing.
- Localize rank/level/reward terms through glossary before translating screens.

## Review Checklist

- [ ] Glossary terms consistent.
- [ ] Placeholders preserved and typed.
- [ ] Plural/select variants correct for the target locale.
- [ ] Tone matches product and audience.
- [ ] CTA matches actual user state.
- [ ] Errors provide recovery.
- [ ] Legal/prize/payment claims are not overstated.
- [ ] Text fits target UI with likely expansion.
- [ ] Native review flags are listed.

## Output Template

```
Translation Quality Brief: [feature]

Voice:
[tone, audience, formality]

Glossary:
| Source Term | Meaning | Target Term | Notes |
|---|---|---|---|

Translations:
| Key | Source | Target | Context | QA Notes |
|---|---|---|---|---|

Review Flags:
[native review, legal review, product decision, UI fit]
```
