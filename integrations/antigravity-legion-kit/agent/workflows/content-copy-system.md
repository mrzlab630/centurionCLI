---
description: Create or audit product language, UX copy, conversion copy, naming, CTA, page sections, descriptions, hints, and state text.
---

# Content and Copy System Workflow

Use this workflow when a task mentions content, copywriting, продающий текст, оффер, value proposition, naming, названия, CTA, кнопки, tabs, pages, sections, descriptions, hints, tooltips, onboarding, empty/error/success states, modals, pricing copy, feature descriptions, help text, or conversion blocks.

## Owner Selection

Choose exactly one owner before work begins:

- NOMENCLATOR owns product language, naming, labels, CTA, microcopy, state text, hints, glossary, and voice consistency.
- MERCATOR owns positioning, audience, offer, funnel intent, objection handling, proof, and conversion hypothesis when those are the main request.
- AEDILIS owns copy placement, hierarchy, scannability, and accessibility constraints when the task is interface-structure-first.
- GLOSSATOR owns localization readiness, placeholders, plural rules, text expansion, RTL risk, and glossary handoff when localization is the main request.
- INDAGATOR owns search-intent fit, metadata, headings, FAQ/schema, and AI-search readability when public-page search is the main request.
- CENSOR owns claim audit, dark-pattern checks, ambiguity, unsupported urgency/scarcity, and legal-risk wording when verification is the main request.
- PICTOR owns implementation fit only when the task is to wire approved copy into UI components.

## Handoff Triggers

- Call MERCATOR only when positioning, audience, offer, funnel, objection, or conversion hypothesis is unresolved.
- Call AEDILIS only when copy placement, hierarchy, accessibility, or component fit constrains wording.
- Call GLOSSATOR only when localization, placeholders, plural rules, text expansion, RTL, or glossary risk appears.
- Call INDAGATOR only when a public page needs search-intent, metadata, headings, FAQ/schema, or AI-search review.
- Call CENSOR only when claims, urgency, scarcity, legal, finance, health, betting, iGaming, or dark-pattern risk appears.
- Call PICTOR only when approved text must be implemented or checked for responsive fit.

## Intake

1. Collect source material first: current UI strings, docs, README, analytics or funnel notes, user-supplied examples, product behavior, pricing, eligibility, and legal constraints.
2. Identify the copy surface:
   - `naming`: product, feature, menu, page, section, tab, plan, status, role, or glossary term.
   - `cta`: buttons, links, action bars, modal actions, checkout/deposit/submit flows.
   - `microcopy`: hints, placeholders, tooltips, helper text, validation, confirmations.
   - `state-copy`: empty, loading, error, blocked, permission, success, warning, pending.
   - `conversion-copy`: hero, offer, value proposition, benefits, proof, objections, pricing, FAQ.
   - `content-page`: landing, onboarding, docs-like page, product page, game/iGaming page, or campaign page.
3. Define user state, intent, and next action before writing: new, returning, blocked, eligible, ineligible, admin, buyer, player, creator, operator, or support user.
4. Use `brand-voice-pass` only after source copy exists; do not invent a voice from nothing.
5. For external inspiration, use `docs/CONTENT_COPY_CATALOG.md` and `content_source_intake` first. Do not copy templates, swipe files, prompt packs, or sales pages without source and license review.

## Writing Rules

- Write for action: every UI string should clarify what is happening, what changed, what the user can do next, or how to recover.
- Prefer concrete nouns and verbs over clever abstractions.
- Keep one primary CTA per screen or message.
- Use variants when naming or CTA matters: 3-7 options with best fit, risk, and localization notes.
- Match copy length to the component: buttons stay short, tooltips answer one question, empty states give one recovery path, hero copy carries one offer.
- Use claims only when the product can prove them. Do not invent performance, revenue, odds, availability, testimonials, reviews, scarcity, urgency, guarantees, or eligibility.
- Keep source copy localization-ready: avoid idioms, hidden wordplay, unmarked variables, text embedded in images, and concatenated fragments.
- For iGaming, finance, wallet, betting, medical, legal, or other high-risk surfaces, add explicit risk/claim review before implementation.

## Output Contract

For writing tasks, return a copy table:

| Element | Recommended | Alternatives | Intent | Risk |
| --- | --- | --- | --- | --- |

For state-heavy UI, return a state table:

| State | Title | Body | CTA | Recovery |
| --- | --- | --- | --- | --- |

For naming tasks, return:

- Recommended name and rationale.
- Alternatives with tone and risk.
- Rejected patterns and why.
- Glossary note: capitalization, do-not-translate terms, and meaning.

## Proof

- Verify copy against implemented behavior or explicit product facts.
- Check CTA hierarchy: one primary action, secondary actions clearly lower priority.
- Check text fit constraints for buttons, nav items, cards, and mobile widths.
- Check accessibility: labels, actionable errors, non-color-only meaning, screen-reader names for icon buttons.
- Check localization readiness: placeholders, pluralization, expansion, glossary terms, and no fragile string concatenation.
- Check conversion copy for measurable event, source of proof, objection coverage, and unsupported claims.
- Report source material used, changed surfaces, claim risks, localization risks, and required implementation follow-up.
