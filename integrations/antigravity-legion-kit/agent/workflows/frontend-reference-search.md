---
description: Search implemented frontend references, page libraries, block catalogs, templates, and product-flow galleries before designing or building UI.
---

# Frontend Reference Search Workflow

Use this workflow before building a new page, screen, landing page, dashboard, onboarding flow, checkout flow, settings area, auth page, product page, mobile flow, iGaming UI, or visually distinctive frontend section.

## Goal

Find 3-5 relevant existing references, extract the useful structure, and rebuild the requested UI inside the target project's stack, design system, product truth, and safety constraints.

## Owner

EXPLORATOR owns the reference search and returns the reference brief. Reference search is complete when the selected references, roles, adaptation notes, and risks are clear.

## Handoff Triggers

- Call AEDILIS only after references must become layout, hierarchy, flow, state, or component-system decisions.
- Call PICTOR only when the approved reference brief must become frontend implementation.
- Call NOMENCLATOR only when labels, CTA, page sections, or user-facing text must be rewritten.
- Call INDAGATOR only when the target is a public page needing SEO, metadata, schema, or crawlable structure.
- Call GUARDIAN only when license, dependency, paid-template, wallet/payment, iGaming, or external-code risk appears.
- Call TESTER only when a runnable app needs browser behavior, screenshot, responsive, or regression proof.

## Search Steps

1. Detect the target surface: page type, platform, stack, audience, domain, style, interaction needs, and constraints.
2. Call `frontend_reference_search` with the user's request plus any known `pageType`, `stack`, and `style`.
3. Select 3-5 references with different strengths: one structural reference, one component/block reference, one visual direction reference, and one flow reference when relevant.
4. For code/block sources, run `frontend_source_intake` or GUARDIAN review before copying any external code.
5. For visual galleries and product-flow references, extract only layout, flow, interaction, and section ideas. Do not copy screenshots, assets, brand identity, or copy.

## Reference Brief

Before implementation, produce a compact brief:

| Reference | Use For | Keep | Change | Risk |
| --- | --- | --- | --- | --- |

Then define:

- Target stack and existing components to reuse.
- Page/screen structure and section order.
- Required states: loading, empty, error, success, disabled, permission, mobile.
- Motion scope and `prefers-reduced-motion` behavior.
- Copy handoff to `content-copy-system` when text matters.
- SEO handoff for public pages.
- License/dependency risks and what will not be copied.

## Adaptation Rules

- Use references to speed judgment, not to override project conventions.
- Rebuild in the target stack and design tokens.
- Preserve accessibility and mobile fit over visual novelty.
- Keep one primary action per screen or section.
- Avoid importing full starters into existing apps unless the user explicitly asks and architecture review approves it.
- Treat paid templates as unavailable unless the user confirms license access.
- For iGaming, betting, wallet, payment, checkout, or bonus surfaces, add GUARDIAN and ALEATOR review before implementation.

## Proof

- Include the selected references and why each matched.
- State what was adapted versus what was intentionally not copied.
- Run build/lint/tests where configured.
- For runnable UI, verify desktop and mobile screenshots or browser smoke.
- Report residual license, dependency, accessibility, copy, SEO, and domain risks.
