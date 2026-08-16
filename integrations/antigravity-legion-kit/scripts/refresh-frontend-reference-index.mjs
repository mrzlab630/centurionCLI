#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const INDEX_PATH = path.join(KIT_ROOT, 'docs', 'FRONTEND_REFERENCE_INDEX.md');
const INDEX_JSON_PATH = path.join(KIT_ROOT, 'docs', 'frontend-reference-index.json');
const INDEX_VERSION = 1;

const SOURCES = [
  {
    id: 'shadcn-ui-blocks',
    name: 'shadcn/ui Blocks',
    url: 'https://ui.shadcn.com/blocks',
    sourceType: 'code-blocks',
    decision: 'adapt-only',
    license: 'verify exact block and dependency terms before reuse',
    stacks: ['react', 'nextjs', 'tailwind', 'shadcn', 'radix'],
    pageTypes: ['dashboard', 'auth', 'settings', 'sidebar-app', 'forms', 'landing'],
    styles: ['clean', 'product', 'saas', 'admin', 'neutral'],
    patterns: ['sidebar layout', 'login page', 'dashboard cards', 'data table', 'settings forms'],
    bestFor: 'Production-like React/Tailwind app pages, dashboards, auth screens, and settings layouts.',
    adaptNotes: 'Use as structural reference; keep target project tokens, routing, data states, and accessibility constraints.'
  },
  {
    id: 'shadcnblocks',
    name: 'Shadcn Blocks',
    url: 'https://www.shadcnblocks.com',
    sourceType: 'code-blocks',
    decision: 'adapt-only',
    license: 'varies by block; verify before copying',
    stacks: ['react', 'nextjs', 'tailwind', 'shadcn'],
    pageTypes: ['landing', 'pricing', 'hero', 'features', 'testimonials', 'faq', 'contact'],
    styles: ['saas', 'startup', 'marketing', 'clean'],
    patterns: ['hero section', 'pricing section', 'feature grid', 'logos row', 'faq accordion'],
    bestFor: 'SaaS and product landing sections built around shadcn/Tailwind patterns.',
    adaptNotes: 'Select sections by conversion purpose; rewrite copy and claims through content-copy-system.'
  },
  {
    id: 'flowbite-blocks',
    name: 'Flowbite Blocks',
    url: 'https://flowbite.com/blocks',
    sourceType: 'code-blocks',
    decision: 'adapt-only',
    license: 'free/pro split; verify block terms',
    stacks: ['html', 'tailwind', 'flowbite', 'react', 'vue', 'svelte'],
    pageTypes: ['marketing', 'application-ui', 'dashboard', 'ecommerce', 'auth', 'forms', 'pricing'],
    styles: ['business', 'saas', 'admin', 'ecommerce', 'neutral'],
    patterns: ['hero', 'navbar', 'pricing', 'checkout', 'dashboard', 'modal', 'form'],
    bestFor: 'Broad Tailwind block coverage across marketing, app UI, ecommerce, and dashboard pages.',
    adaptNotes: 'Good first stop for common page patterns; inspect license tier and component dependencies.'
  },
  {
    id: 'preline-examples',
    name: 'Preline Examples',
    url: 'https://preline.co/examples.html',
    sourceType: 'code-examples',
    decision: 'adapt-only',
    license: 'verify example and plugin terms',
    stacks: ['html', 'tailwind', 'preline'],
    pageTypes: ['dashboard', 'ecommerce', 'auth', 'marketing', 'forms', 'admin'],
    styles: ['business', 'admin', 'clean', 'commerce'],
    patterns: ['admin shell', 'ecommerce product page', 'login', 'landing', 'charts', 'tables'],
    bestFor: 'Tailwind page examples with practical app, admin, and commerce layouts.',
    adaptNotes: 'Use layout patterns without inheriting plugin assumptions unless the target already uses Preline.'
  },
  {
    id: 'hyperui',
    name: 'HyperUI',
    url: 'https://www.hyperui.dev',
    sourceType: 'code-blocks',
    decision: 'adapt-only',
    license: 'MIT-style project; verify exact source before reuse',
    stacks: ['html', 'tailwind'],
    pageTypes: ['marketing', 'ecommerce', 'forms', 'cta', 'cards', 'navigation'],
    styles: ['clean', 'simple', 'ecommerce', 'marketing'],
    patterns: ['product cards', 'CTA', 'newsletter form', 'header', 'stats', 'testimonial'],
    bestFor: 'Simple Tailwind sections and ecommerce/marketing building blocks.',
    adaptNotes: 'Good for lightweight section structure; add states, accessibility, and product-specific copy.'
  },
  {
    id: 'tailwind-ui',
    name: 'Tailwind UI',
    url: 'https://tailwindui.com',
    sourceType: 'paid-code-reference',
    decision: 'needs-license',
    license: 'paid commercial product; use only with valid license',
    stacks: ['html', 'react', 'vue', 'tailwind', 'headlessui'],
    pageTypes: ['marketing', 'application-ui', 'ecommerce', 'dashboard', 'auth', 'pricing'],
    styles: ['polished', 'business', 'saas', 'enterprise'],
    patterns: ['application shell', 'pricing', 'checkout', 'product page', 'dashboard', 'settings'],
    bestFor: 'High-quality benchmark for Tailwind page composition and component APIs.',
    adaptNotes: 'Reference interaction and information architecture unless the user has license access.'
  },
  {
    id: 'tailwind-awesome',
    name: 'Tailwind Awesome',
    url: 'https://www.tailwindawesome.com',
    sourceType: 'template-directory',
    decision: 'reference-only',
    license: 'varies per template',
    stacks: ['tailwind', 'react', 'nextjs', 'vue', 'astro', 'html'],
    pageTypes: ['landing', 'dashboard', 'portfolio', 'blog', 'ecommerce', 'admin'],
    styles: ['varied', 'startup', 'portfolio', 'business'],
    patterns: ['template discovery', 'starter page', 'landing page', 'dashboard template'],
    bestFor: 'Finding full-page Tailwind templates by stack and use case.',
    adaptNotes: 'Use as discovery; follow each template license and do not import full starters blindly.'
  },
  {
    id: 'magic-ui',
    name: 'Magic UI',
    url: 'https://magicui.design',
    repository: 'magicuidesign/magicui',
    sourceType: 'motion-component-catalog',
    decision: 'adapt-only',
    license: 'MIT repository; verify exact component terms',
    stacks: ['react', 'tailwind', 'framer-motion', 'shadcn'],
    pageTypes: ['landing', 'hero', 'features', 'interactive-sections', 'marketing'],
    styles: ['animated', 'saas', 'premium', 'modern'],
    patterns: ['animated hero', 'marquee', 'bento grid', 'particles', 'dock', 'shine border'],
    bestFor: 'Animated marketing sections and modern motion primitives.',
    adaptNotes: 'Keep motion purposeful, reduced-motion safe, and outside the LCP-critical path when possible.'
  },
  {
    id: 'react-bits',
    name: 'React Bits',
    url: 'https://www.reactbits.dev',
    repository: 'DavidHDev/react-bits',
    sourceType: 'motion-component-catalog',
    decision: 'adapt-only',
    license: 'verify exact component terms',
    stacks: ['react', 'css', 'animation', 'webgl'],
    pageTypes: ['hero', 'interactive-sections', 'portfolio', 'marketing'],
    styles: ['animated', 'creative', 'experimental'],
    patterns: ['text animation', 'background effect', 'interactive card', 'scroll effect'],
    bestFor: 'Creative React interactions and animated sections.',
    adaptNotes: 'Use selectively; verify performance, accessibility, and mobile behavior before shipping.'
  },
  {
    id: 'origin-ui',
    name: 'Origin UI',
    url: 'https://originui.com',
    repository: 'origin-space/originui',
    sourceType: 'component-catalog',
    decision: 'adapt-only',
    license: 'verify exact component terms',
    stacks: ['react', 'tailwind', 'shadcn'],
    pageTypes: ['forms', 'navigation', 'settings', 'dashboard', 'application-ui'],
    styles: ['clean', 'product', 'admin'],
    patterns: ['input groups', 'menus', 'filters', 'settings', 'app controls'],
    bestFor: 'Modern shadcn-compatible controls and app UI details.',
    adaptNotes: 'Use for component-level references; preserve target project design tokens and states.'
  },
  {
    id: 'tremor',
    name: 'Tremor',
    url: 'https://www.tremor.so',
    repository: 'tremorlabs/tremor',
    sourceType: 'dashboard-component-catalog',
    decision: 'adapt-only',
    license: 'Apache-2.0 repository; verify exact current terms',
    stacks: ['react', 'tailwind', 'charts', 'dashboard'],
    pageTypes: ['dashboard', 'analytics', 'reports', 'admin', 'metrics'],
    styles: ['data-heavy', 'business', 'admin', 'clean'],
    patterns: ['KPI cards', 'charts', 'tables', 'filters', 'analytics layout'],
    bestFor: 'Data dashboards, analytics pages, KPI panels, and report-like app surfaces.',
    adaptNotes: 'Match chart semantics and loading/error states to real data contracts.'
  },
  {
    id: 'daisyui',
    name: 'daisyUI Components',
    url: 'https://daisyui.com/components/',
    repository: 'saadeghi/daisyui',
    sourceType: 'component-catalog',
    decision: 'adapt-only',
    license: 'MIT repository; verify exact current terms',
    stacks: ['html', 'tailwind', 'daisyui'],
    pageTypes: ['application-ui', 'forms', 'dashboard', 'admin', 'prototype'],
    styles: ['themeable', 'rapid-prototype', 'utility'],
    patterns: ['buttons', 'cards', 'tabs', 'modal', 'drawer', 'toast', 'steps'],
    bestFor: 'Fast component references and state variants when a project can accept daisyUI conventions.',
    adaptNotes: 'Do not introduce daisyUI dependency unless it fits the existing stack.'
  },
  {
    id: 'landingfolio',
    name: 'Landingfolio',
    url: 'https://www.landingfolio.com',
    sourceType: 'visual-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source sites have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['landing', 'hero', 'pricing', 'features', 'testimonials', 'saas'],
    styles: ['saas', 'startup', 'marketing', 'premium'],
    patterns: ['hero', 'CTA', 'feature section', 'pricing', 'social proof'],
    bestFor: 'Finding polished landing-page structures and section sequencing.',
    adaptNotes: 'Rebuild from scratch; use for layout strategy, not copying assets or copy.'
  },
  {
    id: 'lapa-ninja',
    name: 'Lapa Ninja',
    url: 'https://www.lapa.ninja',
    sourceType: 'visual-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source sites have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['landing', 'portfolio', 'product', 'startup', 'app'],
    styles: ['varied', 'editorial', 'startup', 'creative'],
    patterns: ['landing gallery', 'hero composition', 'case-study layout', 'product page'],
    bestFor: 'Broad landing-page inspiration across product categories.',
    adaptNotes: 'Use to identify patterns; do not reuse screenshots, brand assets, or copy.'
  },
  {
    id: 'saas-landing-page',
    name: 'SaaS Landing Page',
    url: 'https://saaslandingpage.com',
    sourceType: 'visual-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source sites have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['saas', 'landing', 'pricing', 'features', 'integrations'],
    styles: ['saas', 'b2b', 'clean', 'conversion'],
    patterns: ['SaaS hero', 'pricing', 'feature matrix', 'integration grid', 'trust logos'],
    bestFor: 'SaaS-specific page flow, offer framing, and conversion section order.',
    adaptNotes: 'Pair with content-copy-system for claims, proof, and CTA adaptation.'
  },
  {
    id: 'mobbin',
    name: 'Mobbin',
    url: 'https://mobbin.com',
    sourceType: 'product-flow-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source apps have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['mobile-app', 'web-app', 'onboarding', 'auth', 'checkout', 'settings', 'subscription'],
    styles: ['product', 'mobile', 'app-flow', 'consumer'],
    patterns: ['onboarding flow', 'paywall', 'settings flow', 'checkout', 'profile'],
    bestFor: 'Real product flows and screen sequences for mobile/web apps.',
    adaptNotes: 'Use for flow structure; rebuild screens in the current design system.'
  },
  {
    id: 'pageflows',
    name: 'Pageflows',
    url: 'https://pageflows.com',
    sourceType: 'product-flow-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source apps have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['onboarding', 'upgrade', 'checkout', 'account', 'settings', 'activation'],
    styles: ['product', 'flow', 'conversion'],
    patterns: ['activation path', 'upgrade flow', 'trial signup', 'account settings', 'subscription'],
    bestFor: 'User journey references for conversion and onboarding workflows.',
    adaptNotes: 'Extract flow steps and decisions, not pixel/copy clones.'
  },
  {
    id: 'godly',
    name: 'Godly',
    url: 'https://godly.website',
    sourceType: 'visual-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source sites have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['landing', 'portfolio', 'product', 'agency', 'creative'],
    styles: ['premium', 'creative', 'editorial', 'animated'],
    patterns: ['high-end hero', 'editorial layout', 'visual rhythm', 'motion direction'],
    bestFor: 'Premium and creative visual direction references.',
    adaptNotes: 'Use carefully for visual language; keep target product usability and performance first.'
  },
  {
    id: 'awwwards',
    name: 'Awwwards Websites',
    url: 'https://www.awwwards.com/websites',
    sourceType: 'visual-gallery',
    decision: 'visual-reference-only',
    license: 'visual inspiration only; source sites have their own rights',
    stacks: ['visual-reference'],
    pageTypes: ['landing', 'portfolio', 'brand', 'campaign', 'creative'],
    styles: ['experimental', 'premium', 'animated', 'brand'],
    patterns: ['immersive hero', 'scroll narrative', 'brand page', 'interactive visual'],
    bestFor: 'High-end creative direction and memorable interactions.',
    adaptNotes: 'Translate intent, not heavy animation or inaccessible interaction patterns.'
  },
  {
    id: 'cruip-templates',
    name: 'Cruip Templates',
    url: 'https://cruip.com/templates/',
    repository: 'cruip/tailwind-landing-page-template',
    sourceType: 'template-directory',
    decision: 'reference-only',
    license: 'free/pro split; verify template terms',
    stacks: ['react', 'nextjs', 'tailwind', 'html'],
    pageTypes: ['landing', 'saas', 'startup', 'waitlist', 'pricing'],
    styles: ['saas', 'startup', 'dark', 'marketing'],
    patterns: ['landing template', 'waitlist page', 'pricing section', 'feature grid'],
    bestFor: 'SaaS/startup landing templates and full-page marketing references.',
    adaptNotes: 'Use structure and section order; rewrite copy and verify license before code reuse.'
  },
  {
    id: 'proweb-tg-casino-ui',
    name: 'TG Casino UI React',
    url: 'https://github.com/Prowebtechnologies/TG-Casino-UI-React',
    repository: 'Prowebtechnologies/TG-Casino-UI-React',
    sourceType: 'domain-reference',
    decision: 'reference-only',
    license: 'MIT observed previously; verify exact current terms',
    stacks: ['react', 'mui', 'telegram', 'mobile'],
    pageTypes: ['igaming', 'casino', 'telegram-mini-app', 'mobile-app'],
    styles: ['casino', 'mobile', 'game', 'telegram'],
    patterns: ['casino lobby', 'game card grid', 'mobile navigation', 'balance panel'],
    bestFor: 'Telegram casino/mobile game UI references.',
    adaptNotes: 'Do not reuse wallet, deposit, bonus, or gambling mechanics without GUARDIAN/ALEATOR review.'
  }
];

const QUERY_SYNONYMS = {
  saas: ['startup', 'b2b', 'software', 'product', 'subscription'],
  лендинг: ['landing', 'hero', 'marketing', 'saas'],
  посадочная: ['landing', 'hero', 'marketing'],
  кабинет: ['dashboard', 'admin', 'settings', 'sidebar-app'],
  дашборд: ['dashboard', 'admin', 'analytics', 'metrics'],
  админка: ['admin', 'dashboard', 'application-ui'],
  авторизация: ['auth', 'login', 'signup'],
  форма: ['forms', 'input', 'validation'],
  цена: ['pricing', 'plans', 'subscription'],
  тарифы: ['pricing', 'plans', 'subscription'],
  магазин: ['ecommerce', 'checkout', 'product page'],
  казино: ['igaming', 'casino', 'game', 'telegram-mini-app'],
  игра: ['game', 'igaming', 'interactive-sections'],
  мобильный: ['mobile-app', 'mobile', 'responsive'],
  анимация: ['animated', 'motion', 'interactive-sections'],
  premium: ['premium', 'polished', 'high-end'],
  minimal: ['clean', 'simple', 'neutral']
};

function parseArgs(argv) {
  const queryIndex = argv.indexOf('--query');
  const limitIndex = argv.indexOf('--limit');
  return {
    write: argv.includes('--write'),
    check: argv.includes('--check'),
    json: argv.includes('--json'),
    query: queryIndex >= 0 ? argv[queryIndex + 1] || '' : '',
    limit: limitIndex >= 0 ? Number(argv[limitIndex + 1] || 5) : 5
  };
}

function normalize(value) {
  return String(value || '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

function tokensFor(query) {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  const expanded = new Set(tokens);
  for (const token of tokens) {
    for (const synonym of QUERY_SYNONYMS[token] || []) expanded.add(normalize(synonym));
  }
  return [...expanded].filter(Boolean);
}

function sourceHaystack(source) {
  return normalize([
    source.id,
    source.name,
    source.url,
    source.repository || '',
    source.sourceType,
    source.decision,
    source.stacks.join(' '),
    source.pageTypes.join(' '),
    source.styles.join(' '),
    source.patterns.join(' '),
    source.bestFor,
    source.adaptNotes
  ].join(' '));
}

function searchSources({ query = '', pageType = '', stack = '', style = '', limit = 5 } = {}) {
  const queryTokens = tokensFor(query);
  const pageTokens = tokensFor(pageType);
  const stackTokens = tokensFor(stack);
  const styleTokens = tokensFor(style);

  const scored = SOURCES.map((source) => {
    const haystack = sourceHaystack(source);
    const reasons = [];
    let score = 0;

    for (const token of queryTokens) {
      if (haystack.includes(token)) {
        score += 2;
        reasons.push(`query:${token}`);
      }
    }
    for (const token of pageTokens) {
      if (source.pageTypes.some((value) => normalize(value).includes(token)) || haystack.includes(token)) {
        score += 5;
        reasons.push(`page:${token}`);
      }
    }
    for (const token of stackTokens) {
      if (source.stacks.some((value) => normalize(value).includes(token)) || haystack.includes(token)) {
        score += 4;
        reasons.push(`stack:${token}`);
      }
    }
    for (const token of styleTokens) {
      if (source.styles.some((value) => normalize(value).includes(token)) || haystack.includes(token)) {
        score += 3;
        reasons.push(`style:${token}`);
      }
    }
    if (!queryTokens.length && !pageTokens.length && !stackTokens.length && !styleTokens.length) score = 1;

    return { ...source, score, matchReasons: [...new Set(reasons)] };
  })
    .filter((source) => source.score > 0)
    .sort((left, right) => right.score - left.score || left.id.localeCompare(right.id));

  return scored.slice(0, Math.max(1, Number(limit) || 5));
}

function buildIndex(generatedAt = new Date().toISOString()) {
  return {
    version: INDEX_VERSION,
    generatedAt,
    policy: {
      installAllowlist: false,
      requiredWorkflow: 'frontend-reference-search',
      safetyGate: 'frontend_source_intake',
      blockedDefaults: [
        'copying visual-gallery pages pixel-for-pixel',
        'using paid templates without a license',
        'importing a full starter template into an existing project without architecture review',
        'copying brand assets, screenshots, or page copy from reference sites',
        'adding dependencies only because a reference uses them'
      ]
    },
    searchFields: ['query', 'pageType', 'stack', 'style'],
    sources: SOURCES
  };
}

function escapeCell(value) {
  return String(value).replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

function renderMarkdown(index) {
  const rows = index.sources.map((source) => [
    `\`${source.id}\``,
    source.name,
    source.sourceType,
    source.decision,
    source.pageTypes.slice(0, 7).join(', '),
    source.stacks.slice(0, 6).join(', '),
    source.url,
    source.bestFor
  ]);

  return `# Frontend Reference Search Index

Generated: ${index.generatedAt}

This index helps Antigravity find already implemented frontend pages, blocks, templates, and visual/product-flow references before designing a new UI. It is a discovery aid, not an install allowlist.

## Search Contract

- Use \`frontend_reference_search\` with the user's natural-language request, optional page type, stack, and style.
- Return 3-5 references before implementation.
- Prefer implemented code/block libraries for concrete UI structure and visual galleries for direction only.
- Convert references into a local brief: layout patterns, interaction states, content sections, assets needed, risks, and adaptation plan.
- Run \`frontend_source_intake\` or GUARDIAN review before copying code from any external source.

## Safety Policy

- Do not clone-run or install templates from this index without a separate audit.
- Do not copy visual-gallery pages pixel-for-pixel.
- Do not use paid templates without confirming license access.
- Do not copy brand assets, screenshots, logos, testimonials, or page copy from reference sites.
- Keep the target project's stack, design tokens, accessibility, responsive rules, and product truth as source of authority.

## Sources

| ID | Name | Type | Decision | Page Types | Stacks | URL | Best For |
| --- | --- | --- | --- | --- | --- | --- | --- |
${rows.map((row) => `| ${row.map(escapeCell).join(' | ')} |`).join('\n')}

## Query Examples

- \`SaaS landing with pricing and testimonials\` -> shadcn blocks, Landingfolio, SaaS Landing Page, Cruip.
- \`admin dashboard with charts and filters React Tailwind\` -> shadcn/ui Blocks, Tremor, Preline, Flowbite.
- \`mobile onboarding subscription flow\` -> Mobbin, Pageflows, shadcn auth/settings references.
- \`animated premium hero for AI product\` -> Magic UI, React Bits, Godly, Awwwards.
- \`Telegram casino lobby mobile UI\` -> TG Casino UI React plus iGaming safety workflow.

## Adaptation Rules

- Extract structure and interaction ideas, not assets or copy.
- Map every reference section to a target component, state, and data source.
- Rebuild using the target stack and existing component system.
- Check 320px mobile, keyboard access, reduced motion, color contrast, and text fit.
- For public pages, route copy through \`content-copy-system\` and SEO through INDAGATOR.
`;
}

function checkIndex() {
  const text = fs.readFileSync(INDEX_PATH, 'utf8');
  const missing = SOURCES.filter((source) => !text.includes(source.id)).map((source) => source.id);
  if (missing.length) throw new Error(`frontend reference index missing source(s): ${missing.join(', ')}`);
  if (!text.includes('not an install allowlist')) throw new Error('frontend reference index missing install allowlist safety wording');
  if (!fs.existsSync(INDEX_JSON_PATH)) throw new Error(`frontend reference index JSON missing: ${INDEX_JSON_PATH}`);
  const index = JSON.parse(fs.readFileSync(INDEX_JSON_PATH, 'utf8'));
  const jsonMissing = SOURCES.filter((source) => !index.sources?.some((entry) => entry.id === source.id)).map((source) => source.id);
  if (jsonMissing.length) throw new Error(`frontend reference JSON missing source(s): ${jsonMissing.join(', ')}`);
  const searchResult = searchSources({ query: 'SaaS landing pricing testimonials', pageType: 'landing', stack: 'tailwind', limit: 5 });
  if (!searchResult.some((source) => source.id === 'shadcnblocks' || source.id === 'flowbite-blocks')) {
    throw new Error('frontend reference search sanity check did not return expected landing sources');
  }
  return { ok: true, sources: SOURCES.length, json: true };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.check) {
    const result = checkIndex();
    process.stdout.write(options.json ? `${JSON.stringify(result)}\n` : `frontend reference index check: pass (${result.sources} sources)\n`);
    return;
  }

  if (options.query) {
    const result = searchSources({ query: options.query, limit: options.limit });
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    return;
  }

  const index = buildIndex();
  if (options.json) {
    process.stdout.write(`${JSON.stringify(index, null, 2)}\n`);
    return;
  }

  const markdown = renderMarkdown(index);
  if (options.write) {
    fs.writeFileSync(INDEX_PATH, markdown);
    fs.writeFileSync(INDEX_JSON_PATH, `${JSON.stringify(index, null, 2)}\n`);
    process.stdout.write(`frontend reference index refreshed: ${INDEX_PATH} and ${INDEX_JSON_PATH}\n`);
  } else {
    process.stdout.write(markdown);
  }
}

main();
