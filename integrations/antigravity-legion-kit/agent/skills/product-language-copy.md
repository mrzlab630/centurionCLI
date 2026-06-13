---
name: product-language-copy
description: Product language, UX copy, naming, CTA, section titles, hints, descriptions, and conversion-copy brief for Antigravity agents.
---

# Product Language Copy

Use when writing or auditing product text: page names, section titles, menu labels, buttons, CTA, hero copy, feature descriptions, helper text, placeholders, tooltips, empty/error/success states, onboarding, pricing copy, and conversion blocks.

## Source Priority

1. Existing UI strings and route/page names.
2. Product behavior and implemented feature facts.
3. README, docs, changelog, strategy notes, screenshots, and analytics/funnel notes.
4. User-supplied brand examples and forbidden wording.
5. External examples only after `content_source_intake` marks them safe to reference.

## Copy Doctrine

- Clarity beats cleverness.
- One screen/message gets one primary action.
- Every state text should tell the user what happened and what to do next.
- CTA labels should name the action, not the product team's intention.
- Tooltips explain one unfamiliar control or constraint; they are not docs pages.
- Empty states should orient, explain why the space is empty, and offer one next step.
- Error copy should avoid blame, name the problem when known, and give a recovery route.
- Selling copy must carry a concrete offer, proof, objection handling, and a measurable next action.

## Hard Bans

- Unsupported claims, fake scarcity, fake urgency, fake testimonials, fake social proof, and guaranteed outcomes.
- Generic AI filler: `seamless`, `unlock your potential`, `powerful solution`, `revolutionary`, unless quoted from the user's actual brand system.
- CTA labels like `Submit`, `Click here`, `Learn more` when a specific action is known.
- Long button labels that break mobile layouts.
- Copy embedded only in images.
- String concatenation that blocks localization.

## Required Handoffs

- MERCATOR for positioning, funnel, offer, campaign, and conversion hypothesis.
- NOMENCLATOR for final source copy, naming system, glossary, and voice consistency.
- AEDILIS for placement, hierarchy, and scannability.
- GLOSSATOR for localization, placeholders, plural rules, and text expansion.
- INDAGATOR for public-page headings, metadata, schema, FAQ, and search intent.
- CENSOR for claims, dark patterns, ambiguity, and high-risk wording.
- PICTOR for component fit, responsive wrapping, and implementation.

## Output Shape

For most tasks, produce:

| Element | Recommended | Alternatives | Intent | Risk |
| --- | --- | --- | --- | --- |

For UI states, produce:

| State | Title | Body | CTA | Recovery |
| --- | --- | --- | --- | --- |

For naming, produce a recommendation, 3-7 alternatives, rejected patterns, and a glossary note.

## Proof Checklist

- Product facts checked against source material or marked as assumptions.
- CTA hierarchy checked.
- Mobile/text-fit risk checked.
- Accessibility and screen-reader label risk checked.
- Localization and glossary risk checked.
- Legal, money, iGaming, health, finance, or safety claims flagged for review.
