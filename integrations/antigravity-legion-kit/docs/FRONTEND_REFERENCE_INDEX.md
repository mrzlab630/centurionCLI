# Frontend Reference Search Index

Generated: 2026-06-12T20:10:38.638Z

This index helps Antigravity find already implemented frontend pages, blocks, templates, and visual/product-flow references before designing a new UI. It is a discovery aid, not an install allowlist.

## Search Contract

- Use `frontend_reference_search` with the user's natural-language request, optional page type, stack, and style.
- Return 3-5 references before implementation.
- Prefer implemented code/block libraries for concrete UI structure and visual galleries for direction only.
- Convert references into a local brief: layout patterns, interaction states, content sections, assets needed, risks, and adaptation plan.
- Run `frontend_source_intake` or GUARDIAN review before copying code from any external source.

## Safety Policy

- Do not clone-run or install templates from this index without a separate audit.
- Do not copy visual-gallery pages pixel-for-pixel.
- Do not use paid templates without confirming license access.
- Do not copy brand assets, screenshots, logos, testimonials, or page copy from reference sites.
- Keep the target project's stack, design tokens, accessibility, responsive rules, and product truth as source of authority.

## Sources

| ID | Name | Type | Decision | Page Types | Stacks | URL | Best For |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `shadcn-ui-blocks` | shadcn/ui Blocks | code-blocks | adapt-only | dashboard, auth, settings, sidebar-app, forms, landing | react, nextjs, tailwind, shadcn, radix | https://ui.shadcn.com/blocks | Production-like React/Tailwind app pages, dashboards, auth screens, and settings layouts. |
| `shadcnblocks` | Shadcn Blocks | code-blocks | adapt-only | landing, pricing, hero, features, testimonials, faq, contact | react, nextjs, tailwind, shadcn | https://www.shadcnblocks.com | SaaS and product landing sections built around shadcn/Tailwind patterns. |
| `flowbite-blocks` | Flowbite Blocks | code-blocks | adapt-only | marketing, application-ui, dashboard, ecommerce, auth, forms, pricing | html, tailwind, flowbite, react, vue, svelte | https://flowbite.com/blocks | Broad Tailwind block coverage across marketing, app UI, ecommerce, and dashboard pages. |
| `preline-examples` | Preline Examples | code-examples | adapt-only | dashboard, ecommerce, auth, marketing, forms, admin | html, tailwind, preline | https://preline.co/examples.html | Tailwind page examples with practical app, admin, and commerce layouts. |
| `hyperui` | HyperUI | code-blocks | adapt-only | marketing, ecommerce, forms, cta, cards, navigation | html, tailwind | https://www.hyperui.dev | Simple Tailwind sections and ecommerce/marketing building blocks. |
| `tailwind-ui` | Tailwind UI | paid-code-reference | needs-license | marketing, application-ui, ecommerce, dashboard, auth, pricing | html, react, vue, tailwind, headlessui | https://tailwindui.com | High-quality benchmark for Tailwind page composition and component APIs. |
| `tailwind-awesome` | Tailwind Awesome | template-directory | reference-only | landing, dashboard, portfolio, blog, ecommerce, admin | tailwind, react, nextjs, vue, astro, html | https://www.tailwindawesome.com | Finding full-page Tailwind templates by stack and use case. |
| `magic-ui` | Magic UI | motion-component-catalog | adapt-only | landing, hero, features, interactive-sections, marketing | react, tailwind, framer-motion, shadcn | https://magicui.design | Animated marketing sections and modern motion primitives. |
| `react-bits` | React Bits | motion-component-catalog | adapt-only | hero, interactive-sections, portfolio, marketing | react, css, animation, webgl | https://www.reactbits.dev | Creative React interactions and animated sections. |
| `origin-ui` | Origin UI | component-catalog | adapt-only | forms, navigation, settings, dashboard, application-ui | react, tailwind, shadcn | https://originui.com | Modern shadcn-compatible controls and app UI details. |
| `tremor` | Tremor | dashboard-component-catalog | adapt-only | dashboard, analytics, reports, admin, metrics | react, tailwind, charts, dashboard | https://www.tremor.so | Data dashboards, analytics pages, KPI panels, and report-like app surfaces. |
| `daisyui` | daisyUI Components | component-catalog | adapt-only | application-ui, forms, dashboard, admin, prototype | html, tailwind, daisyui | https://daisyui.com/components/ | Fast component references and state variants when a project can accept daisyUI conventions. |
| `landingfolio` | Landingfolio | visual-gallery | visual-reference-only | landing, hero, pricing, features, testimonials, saas | visual-reference | https://www.landingfolio.com | Finding polished landing-page structures and section sequencing. |
| `lapa-ninja` | Lapa Ninja | visual-gallery | visual-reference-only | landing, portfolio, product, startup, app | visual-reference | https://www.lapa.ninja | Broad landing-page inspiration across product categories. |
| `saas-landing-page` | SaaS Landing Page | visual-gallery | visual-reference-only | saas, landing, pricing, features, integrations | visual-reference | https://saaslandingpage.com | SaaS-specific page flow, offer framing, and conversion section order. |
| `mobbin` | Mobbin | product-flow-gallery | visual-reference-only | mobile-app, web-app, onboarding, auth, checkout, settings, subscription | visual-reference | https://mobbin.com | Real product flows and screen sequences for mobile/web apps. |
| `pageflows` | Pageflows | product-flow-gallery | visual-reference-only | onboarding, upgrade, checkout, account, settings, activation | visual-reference | https://pageflows.com | User journey references for conversion and onboarding workflows. |
| `godly` | Godly | visual-gallery | visual-reference-only | landing, portfolio, product, agency, creative | visual-reference | https://godly.website | Premium and creative visual direction references. |
| `awwwards` | Awwwards Websites | visual-gallery | visual-reference-only | landing, portfolio, brand, campaign, creative | visual-reference | https://www.awwwards.com/websites | High-end creative direction and memorable interactions. |
| `cruip-templates` | Cruip Templates | template-directory | reference-only | landing, saas, startup, waitlist, pricing | react, nextjs, tailwind, html | https://cruip.com/templates/ | SaaS/startup landing templates and full-page marketing references. |
| `proweb-tg-casino-ui` | TG Casino UI React | domain-reference | reference-only | igaming, casino, telegram-mini-app, mobile-app | react, mui, telegram, mobile | https://github.com/Prowebtechnologies/TG-Casino-UI-React | Telegram casino/mobile game UI references. |

## Query Examples

- `SaaS landing with pricing and testimonials` -> shadcn blocks, Landingfolio, SaaS Landing Page, Cruip.
- `admin dashboard with charts and filters React Tailwind` -> shadcn/ui Blocks, Tremor, Preline, Flowbite.
- `mobile onboarding subscription flow` -> Mobbin, Pageflows, shadcn auth/settings references.
- `animated premium hero for AI product` -> Magic UI, React Bits, Godly, Awwwards.
- `Telegram casino lobby mobile UI` -> TG Casino UI React plus iGaming safety workflow.

## Adaptation Rules

- Extract structure and interaction ideas, not assets or copy.
- Map every reference section to a target component, state, and data source.
- Rebuild using the target stack and existing component system.
- Check 320px mobile, keyboard access, reduced motion, color contrast, and text fit.
- For public pages, route copy through `content-copy-system` and SEO through INDAGATOR.
