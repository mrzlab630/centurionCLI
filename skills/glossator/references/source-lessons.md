# Source Lessons

Use this file when grounding i18n/l10n advice in the open-source projects selected as learning sources. These are pattern sources, not code sources.

## Source Rule

- Extract patterns and decision criteria; do not copy code, translation strings, or project-specific workflows blindly.
- Verify current library APIs from project docs before implementation.
- Keep project conventions first: if a repo already uses i18next, do not migrate to Fluent only because Fluent is elegant.

## Repository Pattern Map

| Repository | Use For | Lesson |
|---|---|---|
| `i18next/react-i18next` | Mature React i18n integration. | Namespaces, lazy loading, fallback, hooks, ecosystem plugins. |
| `lingui/js-lingui` | Extraction and compile-time catalog workflow. | Good for product apps where messages need review and compilation. |
| `formatjs/formatjs` | ICU MessageFormat and locale formatting. | Strong model for plural/select, dates, numbers, currency. |
| `projectfluent/fluent.js` | Natural-language localization with complex grammar. | Keep grammar choices in translation files instead of code. |
| `codingcommons/typesafe-i18n` | Type-safe translation access. | Prevent missing keys and invalid access in TypeScript-heavy projects. |
| `lingodotdev/lingo.dev` | Localization engineering automation. | Automation helps, but glossary/context/human review remain required. |
| `unicode-org/cldr-json` | Locale data and plural/formatting rules. | Do not invent plural or date/currency rules manually. |

## Synthesized Lessons

1. Professional i18n starts with message modeling, not translation spreadsheets.
2. Plural/select support is mandatory for dynamic UI, games, counters, rewards, and notifications.
3. Formatting is localization too: numbers, dates, currencies, relative time, and lists must be locale-aware.
4. Type safety and extraction reduce broken keys, but cannot replace translation context.
5. Fluent/ICU-style messages are better than concatenated fragments for languages with different grammar.
6. Automation is useful for draft translation and consistency checks, but final product copy needs review in UI.
7. DB-backed copy needs schema, workflow, and fallback rules; otherwise it becomes untestable content debt.
