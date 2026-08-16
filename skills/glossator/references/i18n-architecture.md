# I18n Architecture

Use this file for i18n library choice, translation key design, extraction, fallback, runtime locale handling, and implementation handoffs.

## Table Of Contents

- Library Decision Matrix
- Architecture Workflow
- Locale Negotiation
- Key Design
- Message Modeling
- Runtime Loading
- DB-Backed Copy
- Formatting
- Anti-Patterns
- Implementation Handoff

## Library Decision Matrix

| Need | Prefer | Why | Watch Out |
|---|---|---|---|
| Broad React ecosystem, JSON namespaces, mature plugins | i18next + react-i18next | Common, flexible, good lazy loading and fallback story. | Type safety needs extra setup; JSON strings can hide invalid placeholders. |
| Compile-time extraction, readable messages, product apps | Lingui | Good extraction workflow, readable catalogs, ICU support. | Requires build/extraction discipline. |
| Standards-based ICU MessageFormat, complex plurals/selects | FormatJS / react-intl | Strong ICU and formatting model. | Verbose APIs if not wrapped. |
| High-quality natural-language localization with complex grammar | Fluent | Separates grammar logic from code; strong for rich localization. | Team must learn Fluent syntax and review workflow. |
| Type-safe TypeScript projects with strict key contracts | typesafe-i18n | Prevents missing/invalid keys and gives strong DX. | Less universal than i18next ecosystem. |
| Product/admin copy edited outside deploys | DB-backed copy + typed API | Fits admin-managed content and controlled copy surfaces. | Needs versioning, fallback, cache invalidation, and editor permissions. |
| AI-assisted translation pipeline | Lingo.dev or similar tools | Useful for automation, checks, and workflow integration. | Still requires glossary, context, and human/native review. |

## Architecture Workflow

1. Audit current strings: hardcoded UI, server messages, DB copy, validation errors, emails/notifications, bot messages.
2. Classify ownership: client UI, server API, admin-managed copy, legal/compliance, generated content.
3. Choose message model: flat JSON, namespace catalogs, ICU, Fluent, DB records, or hybrid.
4. Define locale negotiation: explicit user setting, Telegram `languageCode`, browser language, account profile, fallback.
5. Define extraction/update workflow: source strings -> keys -> translator context -> review -> build/deploy.
6. Define QA gates before launch: missing keys, placeholder parity, plural coverage, pseudo-locale, screenshots, RTL if relevant.

## Locale Negotiation

Priority should be explicit and stable:

1. User-selected locale saved in profile/session.
2. Platform/user signal: Telegram `initData.user.languageCode`, browser `navigator.language`, account country only if language is not available.
3. Product default locale.
4. Hard fallback namespace/key.

Do not infer locale from IP alone for interface language. Use IP/country for regional formatting only when legally/product-relevant and disclosed.

## Key Design

Prefer semantic, stable keys tied to product meaning, not English wording.

Good:

```
wallet.balance.title
wallet.reward.claimCta
game.result.energyDepleted.message
auth.blockedUser.title
```

Avoid:

```
click_here
your_balance_is
text_12
home.subtitle2
```

Key rules:

- Namespace by feature or surface: `wallet`, `game`, `auth`, `common`, `errors`, `admin`.
- Keep CTA keys separate from titles and explanatory copy.
- Never reuse the same key for text that only happens to be identical in English.
- Do not embed HTML unless the renderer has a strict structured allowlist.
- Track message type: label, CTA, title, body, error, empty, success, legal, notification.

## Message Modeling

Use structured dynamic messages:

```
reward.claimed = You claimed {amount, number} {currency}.
energy.remaining = {count, plural, one {# energy} other {# energy}}
task.status = {status, select, pending {Pending} done {Complete} failed {Try again} other {Unknown}}
```

Rules:

- Keep placeholders named by meaning: `{amount}`, `{currency}`, `{timeLeft}`, `{playerName}`.
- Preserve placeholder parity across locales.
- Use plural/select for all count/state/gender/role variants.
- Do not split a sentence across keys if grammar changes by locale.
- Use rich-text interpolation only through safe components, not raw HTML.

## Runtime Loading

- Lazy-load locale bundles by route/namespace when bundle size matters.
- Include critical boot strings for loading/auth errors in the initial bundle or server response.
- Fallback should be visible in logs/metrics, not silently accepted forever.
- Missing keys should fail tests in CI and report in development.
- Cache locale bundles with versioned assets; invalidate DB-backed copy by revision/version.

## DB-Backed Copy

Use DB-backed copy when copy must change without deploys, but keep structure strict:

| Field | Purpose |
|---|---|
| `key` | Stable semantic key. |
| `locale` | BCP 47 locale. |
| `message` | ICU/Fluent/plain message. |
| `message_type` | title, body, cta, error, legal, etc. |
| `description` | Translator/editor context. |
| `placeholders_schema` | Allowed placeholders and types. |
| `version` | Revision or publish version. |
| `status` | draft, review, published, archived. |

Do not allow raw `<script>`, arbitrary head tags, or broad HTML in translatable copy. Use controlled rich-text slots/components.

## Formatting

Never hardcode formatting by string concatenation. Use locale APIs:

- Dates/times: `Intl.DateTimeFormat` with timezone policy.
- Numbers: `Intl.NumberFormat`.
- Currency: ISO currency and locale-aware display.
- Relative time: `Intl.RelativeTimeFormat` or library wrapper.
- Lists: `Intl.ListFormat`.
- Names/addresses: locale-specific rules when required.

## Anti-Patterns

- Translating raw English strings directly in components.
- Using English text as translation keys.
- Reusing one key across different screens without context.
- Concatenating `"You have " + count + " items"`.
- Lowercasing/uppercasing translated strings in code.
- Assuming all languages fit English button widths.
- Storing translator-visible copy only in code comments.
- Shipping locale files with missing placeholders or stale keys.

## Implementation Handoff

GLOSSATOR should hand CODER/PICTOR:

- Library/pattern decision and why.
- Namespace/key map.
- Message format requirements: ICU, Fluent, plain, rich text.
- Locale negotiation order.
- Extraction and CI checks.
- Formatting wrappers/utilities needed.
- QA gates and representative test strings.
