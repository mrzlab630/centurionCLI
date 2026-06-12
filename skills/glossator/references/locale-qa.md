# Locale QA

Use this file for localization testing, pseudo-localization, RTL, screenshots, formatting, and regression checks.

## Table Of Contents

- QA Layers
- Static Checks
- Runtime Checks
- Pseudo-Localization
- Screenshot Review
- RTL And Bidirectional Text
- Locale Formatting
- Telegram-Specific Checks
- Release Gate

## QA Layers

| Layer | Goal | Examples |
|---|---|---|
| Static | Catch broken catalogs before runtime. | Missing keys, placeholder mismatch, invalid ICU syntax. |
| Unit | Verify formatting helpers and selection logic. | Plurals, date/currency wrappers, fallback. |
| Integration | Verify screens load correct namespaces. | Route-level locale bundles, DB copy fallback. |
| Visual | Verify translated UI fits. | Screenshots, truncation, wrapping, RTL. |
| Native review | Verify language quality. | Context, tone, grammar, market terminology. |

## Static Checks

Check in CI:

- Missing keys compared with source locale.
- Unused keys and stale namespaces.
- Placeholder parity: same placeholder names and compatible types.
- ICU/Fluent syntax validity.
- Duplicate keys.
- Forbidden raw HTML or unapproved rich text.
- Locale filename and BCP 47 tag consistency.

## Runtime Checks

- Locale negotiation follows documented priority.
- Fallback is deterministic and logged.
- Missing keys are visible in development.
- User-selected locale persists across sessions/devices where expected.
- Server and client agree on locale for server-rendered or API-owned messages.
- Lazy-loaded namespaces do not create blank screens.

## Pseudo-Localization

Use pseudo-locales before real translation:

- Expand text by 30-50%.
- Add accents or brackets to reveal hardcoded strings.
- Preserve placeholders exactly.
- Simulate RTL separately.

Pseudo examples:

```
Claim reward -> [Çļåîṁ ŕêŵåŕđ !!!]
You have {count} coins -> [Ýôû ĥåṽê {count} çôîñš !!!]
```

If pseudo text does not appear on a screen, the screen likely has hardcoded strings or missing namespace loading.

## Screenshot Review

Review at least:

- Small mobile width.
- Common desktop width.
- Long-text locale.
- Pseudo-locale.
- RTL locale if supported.
- Empty, loading, error, success, and edge states.

Look for:

- Truncated buttons.
- Text overlap.
- Layout shift.
- Broken tables/cards.
- Tooltips/popovers clipped by viewport.
- Icons that imply the wrong direction in RTL.

## RTL And Bidirectional Text

- Set `dir="rtl"` at the document or app root for RTL locales.
- Use logical CSS properties (`margin-inline-start`) instead of left/right where possible.
- Mirror directional icons only when their meaning is directional.
- Keep numbers, codes, usernames, hashes, and URLs readable with bidi isolation.
- Test mixed Arabic/Hebrew + Latin placeholders.

## Locale Formatting

Verify:

- Date order and calendar expectations.
- 12h/24h time.
- Timezone policy.
- Decimal and thousands separators.
- Currency symbol placement and precision.
- Percent formatting.
- Lists and conjunctions.
- Relative time and countdown grammar.

## Telegram-Specific Checks

- Telegram `languageCode` is treated as a hint, not an irreversible setting.
- Mini App theme and locale initialize before final paint where possible.
- Bot and Mini App copy use the same glossary.
- Button labels fit Telegram mobile surfaces.
- WebView safe areas and bottom buttons do not hide expanded translations.
- Server-owned copy and client-owned copy fall back consistently.

## Release Gate

Do not call a locale production-ready until:

- Static catalog checks pass.
- Placeholder and plural checks pass.
- Pseudo-locale visual smoke passes.
- Screenshots reviewed for core flows.
- Native reviewer or accountable owner signs off target-language copy.
- Legal/payment/prize copy is reviewed when applicable.
- Fallback behavior is documented and tested.
