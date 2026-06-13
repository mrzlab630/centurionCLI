# Content, Copywriting, UX Writing, and Product Language Sources

Generated: 2026-06-12T20:40:32.278Z

This catalog records GitHub repositories and discovery hints for content design, UX writing, product language, naming, CTA, conversion copy, and measurable copy experiments. It is a discovery aid, not an install allowlist.

## Safety Policy

- Do not copy external sales copy, style-guide phrasing, testimonials, claims, scarcity, urgency, or legal wording without a separate content and license audit.
- Prefer `adapt-only`: translate a specific inspected pattern into the product's existing voice, behavior, constraints, and component system.
- Treat FindSkills guest results as search hints only when source details are hidden.
- Public-page copy must be checked for search intent, metadata, schema, accessibility, and localization readiness.
- High-risk finance, health, legal, wallet, betting, casino, iGaming, pricing, checkout, or bonus copy requires CENSOR/GUARDIAN review before shipping.

## Categories

- `content-style-guide`: Plain-language, terminology, tone, accessibility, and localization guidance.
- `content-design-system`: Component-bound UX copy patterns, states, labels, errors, and navigation language.
- `brand-voice-system`: Voice and tone systems for deriving brand language without copying phrasing.
- `accessibility-copy`: Accessible labels, instructions, error copy, and inclusive content guidance.
- `experimentation-copy`: A/B testing and analytics references for measurable copy variants.
- `agent-copy-skill`: External agent skills or prompt packs for content/copy tasks.
- `long-form-content`: Blog, newsletter, docs, and long-form content generation references.
- `copywriting-reference`: Sales-copy references that require strict claim and ethics review.
- `prompt-copy-reference`: Prompt catalogs and prompt-engineering references for repeatable copy tasks.

## Candidates

| Repository | Category | License Signal | Safety Decision | Useful Assets | Notes |
| --- | --- | --- | --- | --- | --- |
| `18F/content-guide` | content-style-guide | NOASSERTION | adapt-only | Plain-language, inclusive, accessible government content guidance | Good baseline for clarity, accessibility, error states, and public-service tone. Stars: 83; archived: yes; pushed: 2023-12-14T21:02:02Z. |
| `alphagov/govuk-design-system` | content-design-system | MIT | adapt-only | Production design-system content patterns, error messages, form labels, and service copy | Strong model for practical UX copy tied to components and user journeys. Stars: 637; archived: no; pushed: 2026-06-12T15:05:48Z. |
| `MicrosoftDocs/microsoft-style-guide` | content-style-guide | CC-BY-4.0 | reference-only | Technical style, terminology, UI text, accessibility, and globalization guidance | Use for terminology discipline and localization-aware technical copy. Stars: 186; archived: yes; pushed: 2024-11-13T15:13:53Z. |
| `mailchimp/content-style-guide` | brand-voice-system | NOASSERTION | reference-only | Voice, tone, writing principles, and content-type guidance | Useful brand-voice reference; do not copy brand-specific phrasing. Stars: 548; archived: no; pushed: 2022-05-04T22:34:54Z. |
| `Shopify/polaris` | content-design-system | no GitHub license signal observed | adapt-only | Product content guidance, components, commerce/admin UX patterns, and empty/error states | Good for operational dashboards and merchant/admin product language. Stars: 0; archived: no; pushed: unknown. |
| `primer/design` | content-design-system | MIT | adapt-only | Design-system patterns for labels, buttons, navigation, status, and docs-like product surfaces | Use for concise developer/product UI terminology and component-bound copy. Stars: 761; archived: yes; pushed: 2025-07-02T18:45:58Z. |
| `w3c/wai-website` | accessibility-copy | NOASSERTION | reference-only | Accessibility writing, labels, errors, instructions, and inclusive design references | Use for accessibility checks and wording around disabled/error/instruction states. Stars: 133; archived: no; pushed: 2026-06-12T08:49:46Z. |
| `growthbook/growthbook` | experimentation-copy | NOASSERTION | reference-only | Feature-flag and A/B-test platform patterns for copy experiments and measurable variants | Reference for testable copy hypotheses; do not import platform code into this kit. Stars: 7880; archived: no; pushed: 2026-06-12T20:02:51Z. |
| `posthog/posthog` | experimentation-copy | NOASSERTION | reference-only | Product analytics and experimentation patterns for measuring CTA and funnel copy impact | Reference for measurement thinking; dependency surface is far outside this kit. Stars: 34999; archived: no; pushed: 2026-06-12T20:38:30Z. |
| `rmyndharis/antigravity-skills` | agent-copy-skill | no GitHub license signal observed | adapt-only | Large Antigravity skill catalog; may contain writing, marketing, content, and UX prompt examples | Discovery only; selective intake through external_skill_intake and no bulk installs. Stars: 0; archived: no; pushed: unknown. |
| `sociilabs/claude-content-writer` | agent-copy-skill | no GitHub license signal observed | needs-approval | FindSkills-discovered content writer skill for blogs, newsletters, and human-sounding long-form content | Guest FindSkills response hid source details during discovery; verify upstream before use. Stars: 0; archived: no; pushed: unknown. |
| `isaacavazquez/website` | copywriting-reference | no GitHub license signal observed | needs-approval | FindSkills-discovered Copywriting skill hint | Guest FindSkills response hid source details during discovery; verify upstream before use. Stars: 0; archived: no; pushed: unknown. |
| `uswds/uswds-site` | content-design-system | no GitHub license signal observed | adapt-only | US Web Design System site guidance for content, components, accessibility, forms, and public-service pages | Good source for content patterns tied to real components and accessibility requirements. Stars: 0; archived: no; pushed: unknown. |
| `salesforce-ux/design-system` | content-design-system | no GitHub license signal observed | adapt-only | Salesforce Lightning Design System patterns for enterprise UI labels, forms, empty states, errors, and help text | Useful for B2B/admin surfaces; adapt patterns into the target product voice. Stars: 0; archived: no; pushed: unknown. |
| `carbon-design-system/carbon` | content-design-system | no GitHub license signal observed | adapt-only | Carbon Design System component patterns, content guidance, state text, and enterprise product language references | Good for dense operational tools and component-bound UX copy. Stars: 0; archived: no; pushed: unknown. |
| `f/awesome-chatgpt-prompts` | prompt-copy-reference | no GitHub license signal observed | reference-only | Large prompt catalog with writing, editing, marketing, and ideation examples | Prompt catalog only; prompts may contain unsafe assumptions or generic output patterns. Stars: 0; archived: no; pushed: unknown. |
| `dair-ai/Prompt-Engineering-Guide` | prompt-copy-reference | no GitHub license signal observed | reference-only | Prompt engineering guide and examples useful for structuring repeatable copy tasks | Use for prompt structure, not for product claims or final copy. Stars: 0; archived: no; pushed: unknown. |

## Patterns Worth Adapting

- Product language: define user state, surface, intent, and next action before writing.
- Naming: generate 3-7 options, reject misleading patterns, and add glossary notes.
- CTA: name the action, keep one primary CTA, and verify the action exists.
- Microcopy: explain constraints and recovery paths without becoming documentation.
- Conversion copy: connect offer, proof, objection handling, and measurable event.
- Localization: avoid idioms, hidden variables, string concatenation, and fragile button labels.
- Claim safety: every promise must map to implemented behavior or a cited product fact.

## Blocked Defaults

- Copying swipe-file or sales-page text verbatim.
- Inventing review counts, testimonials, awards, guarantees, revenue outcomes, odds, scarcity, or urgency.
- Reusing brand-specific style-guide examples as product copy.
- Shipping legal, payment, wallet, medical, finance, betting, or iGaming copy without claim review.
- Adding copy that cannot fit mobile buttons, nav items, cards, or localized UI.
