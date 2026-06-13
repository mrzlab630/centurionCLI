---
description: Route frontend interface, animation, landing-page, and iGaming page work through UX, implementation, conversion, SEO, and safety gates.
---

# Frontend, Landing, and iGaming Workflow

Use this workflow when a task mentions frontend UI, interfaces, animation, motion, landing pages, conversion pages, casino, betting, gambling, slots, jackpots, iGaming, or game-promo pages.

## Owner Selection

Choose exactly one owner before work begins:

- PICTOR owns frontend implementation, responsive layout, animation, and browser proof.
- AEDILIS owns screen structure, hierarchy, component-system fit, accessibility, and visual review when the task is design-only.
- INDAGATOR owns SEO, schema, indexability, metadata, Core Web Vitals, and AI-search readability when those are the main request.
- MERCATOR owns audience, offer, funnel intent, conversion hypothesis, and CTA strategy when those are the main request.
- ALEATOR owns iGaming mechanics, responsible-gaming boundaries, odds/reward transparency, and dark-pattern risk when those are the main request.
- GUARDIAN owns external-source intake, payments/wallet/deposit surfaces, privacy, age-gate, and dependency safety when those are the main request.
- TESTER owns regression, e2e, screenshot, and interaction proof when the request is proof-only.

## Handoff Triggers

- Call AEDILIS only when implementation needs layout, hierarchy, component-system, or accessibility decisions.
- Call PICTOR only when a design, SEO, conversion, or iGaming decision must become frontend code.
- Call INDAGATOR only when a public page needs search, metadata, schema, or Core Web Vitals review.
- Call MERCATOR only when offer, funnel, audience, or conversion hypothesis is unresolved.
- Call ALEATOR only when rewards, odds, gambling mechanics, or dark-pattern risk appears.
- Call GUARDIAN only when external code, dependency, wallet, payment, deposit, KYC, privacy, or age-gate risk appears.
- Call TESTER only when a runnable app needs browser, responsive, screenshot, interaction, or regression proof.

## Intake

1. Detect the current stack before recommending anything: framework, router, component library, styling system, animation library, asset pipeline, and build/test scripts.
2. Inspect existing design tokens, reusable components, routes, copy patterns, metadata handling, analytics, and image conventions.
3. Decide the page type:
   - `interface`: app screen, dashboard, tool, form, settings, or data workflow.
   - `motion`: animated component, transition system, interactive scene, or microinteraction.
   - `landing`: acquisition page, campaign page, product site, waitlist, pricing, or lead form.
   - `igaming`: casino, betting, slot, jackpot, sportsbook, Web3 game, or Telegram game-promo surface.
4. For external inspiration, use `docs/FRONTEND_CATALOG.md` and `frontend_source_intake` first. Do not install, clone-run, or bulk-copy external UI packs without GUARDIAN approval.

## Execution Checklist

- Preserve the existing product style unless the task explicitly asks for a redesign.
- Use existing components and tokens before adding a new visual system.
- Keep controls complete: default, hover, active, focus, disabled, loading, empty, error, success, and permission states where relevant.
- Build mobile-first and verify no horizontal scroll at 320px.
- Respect `prefers-reduced-motion`; motion must clarify state or delight without blocking comprehension.
- Reserve hero-scale typography for true heroes; keep app panels dense, readable, and stable.
- Give fixed-format UI stable dimensions using grid tracks, aspect ratios, min/max constraints, or container-relative sizing.
- Avoid decorative one-note palettes, nested cards, fake UI depth, and text that overlaps controls.

## Landing Page Requirements

- The first viewport must communicate the brand/product/place/object and primary offer, not a generic marketing abstraction.
- Include a clear CTA path, trust signals, objection handling, proof, pricing or next-step clarity, and a measurable conversion event.
- Add or preserve title, description, canonical, Open Graph/Twitter metadata, structured data where relevant, and crawlable content.
- Protect Core Web Vitals: explicit media dimensions, optimized assets, font-display strategy, low CLS, and no unnecessary heavy animation in the LCP path.

## iGaming Requirements

- Add responsible-gaming and age-appropriateness checks to the design brief before implementation.
- Do not imply guaranteed winnings, hidden odds, fake scarcity, fake urgency, or false social proof.
- Show costs, odds/RTP/provably-fair claims, bonuses, wallet/deposit terms, and eligibility only when the product can substantiate them.
- Provide natural stopping points, cooldown/spending-limit affordances when money-like value is involved, and a visible route to terms/support.
- Route wallet, payment, deposit, withdrawal, KYC, affiliate tracking, and bonus abuse logic through GUARDIAN before shipping.

## Proof

- Run the smallest meaningful project checks: lint/typecheck/build/tests where configured.
- For a runnable UI, capture browser proof or Playwright screenshots for desktop and mobile; include reduced-motion coverage for animation-heavy work when feasible.
- For landing pages, verify metadata/schema and at least one realistic mobile viewport.
- For iGaming pages, include an explicit responsible-gaming/dark-pattern audit note from ALEATOR when ALEATOR was the owner or handoff.
- Report changed files, proof commands, external sources used, and residual risk.
