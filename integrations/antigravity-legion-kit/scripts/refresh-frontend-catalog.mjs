#!/usr/bin/env node
import fs from 'node:fs';
import https from 'node:https';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const CATALOG_PATH = path.join(KIT_ROOT, 'docs', 'FRONTEND_CATALOG.md');
const CATALOG_JSON_PATH = path.join(KIT_ROOT, 'docs', 'frontend-catalog.json');
const CATALOG_VERSION = 1;

const CANDIDATES = [
  {
    repository: 'Nyx-abu/awwwards-ui-skill',
    category: 'agent-skill',
    decision: 'adapt-only',
    useful: 'Antigravity/Claude/Codex UI skill for design intent, motion, typography, color, accessibility',
    notes: 'Strong frontend taste source; adapt guidance into local workflows rather than installing wholesale.'
  },
  {
    repository: 'BekhruzTursunboev/Bexa-professional-frontend-design-skills-for-ai-agents',
    category: 'agent-skill',
    decision: 'adapt-only',
    useful: 'Senior design-engineering and animated frontend skill prompts for AI agents',
    notes: 'Useful for phrasing PICTOR/AEDILIS briefs; audit exact SKILL.md files before copying.'
  },
  {
    repository: 'crehativos/antigravity-frontend-skills',
    category: 'agent-skill',
    decision: 'reference-only',
    useful: 'Portuguese frontend instructions for Antigravity-style agents',
    notes: 'No license signal was observed during discovery; treat as reference only.'
  },
  {
    repository: 'MauroProto/mis-skills',
    category: 'agent-skill',
    decision: 'adapt-only',
    useful: 'Cross-agent frontend design skills for Claude, Codex, Cursor, Continue, and Antigravity',
    notes: 'Contains scripts and multi-agent surfaces; audit before any import.'
  },
  {
    repository: 'lucaspmarie-a11y/claude-skills-vault',
    category: 'agent-skill',
    decision: 'reference-only',
    useful: 'Large accessibility-heavy skill vault with many frontend-related entries',
    notes: 'Huge pack risk; use only to discover a specific missing skill, never bulk-install.'
  },
  {
    repository: 'ixartz/SaaS-Boilerplate',
    category: 'landing-template',
    decision: 'reference-only',
    useful: 'Next.js, Tailwind, shadcn, auth, i18n, SaaS landing and app structure',
    notes: 'Full application boilerplate; use as architecture reference, not a drop-in landing import.'
  },
  {
    repository: 'cruip/tailwind-landing-page-template',
    category: 'landing-template',
    decision: 'reference-only',
    useful: 'Popular Tailwind/React/Next landing template patterns',
    notes: 'License and template terms must be checked before reuse.'
  },
  {
    repository: 'leoMirandaa/shadcn-landing-page',
    category: 'landing-template',
    decision: 'adapt-only',
    useful: 'Shadcn, React, TypeScript, Tailwind landing-page sections',
    notes: 'Good section-pattern reference; copy only license-compatible audited fragments.'
  },
  {
    repository: 'MekuHQ/convertly',
    category: 'landing-template',
    decision: 'adapt-only',
    useful: 'React, Tailwind, Vite SaaS landing template',
    notes: 'Small enough to inspect; still adapt ideas into the target project style.'
  },
  {
    repository: 'darkmage208/business-landing-page-template',
    category: 'landing-template',
    decision: 'reference-only',
    useful: 'React, Tailwind, TypeScript business landing sections',
    notes: 'No license signal was observed during discovery; use as visual reference only.'
  },
  {
    repository: 'magicuidesign/magicui',
    category: 'motion-catalog',
    decision: 'adapt-only',
    useful: 'Animated React/shadcn/Tailwind component catalog with Framer Motion patterns',
    notes: 'Strong motion-component source; avoid bulk-copying a design system into existing apps.'
  },
  {
    repository: 'SyntaxUI/syntaxui',
    category: 'motion-catalog',
    decision: 'adapt-only',
    useful: 'Tailwind, Framer Motion, effects, and animation component patterns',
    notes: 'Good animation reference; inspect component dependencies and license before reuse.'
  },
  {
    repository: 'educlopez/smoothui',
    category: 'motion-catalog',
    decision: 'adapt-only',
    useful: 'React, Tailwind, shadcn, and Motion animated UI components',
    notes: 'Useful for microinteractions; preserve reduced-motion and performance constraints.'
  },
  {
    repository: 'anl331/goey-toast',
    category: 'motion-catalog',
    decision: 'adapt-only',
    useful: 'Focused Framer Motion toast interaction reference',
    notes: 'Narrow component reference; audit dependency and bundle impact.'
  },
  {
    repository: 'apix-js/shadix-ui',
    category: 'component-catalog',
    decision: 'adapt-only',
    useful: 'Shadcn-based animated React component catalog',
    notes: 'Use as component inspiration; keep target project tokens and accessibility patterns.'
  },
  {
    repository: 'itsjwill/motion-primitives-website',
    category: 'motion-catalog',
    decision: 'reference-only',
    useful: 'Website for motion primitives and animated React component examples',
    notes: 'License signal must be verified before code reuse.'
  },
  {
    repository: 'nyxb-ui/ui',
    category: 'component-catalog',
    decision: 'reference-only',
    useful: 'Archived UI component catalog with animated patterns',
    notes: 'Archived source; do not depend on it for production components.'
  },
  {
    repository: 'ishansh1200/StackD',
    category: 'component-catalog',
    decision: 'reference-only',
    useful: 'Component discovery engine across Aceternity, ReactBits, Magic UI, and shadcn-style sources',
    notes: 'Discovery catalog only; follow links back to audited upstream sources.'
  },
  {
    repository: 'Prowebtechnologies/TG-Casino-UI-React',
    category: 'igaming-reference',
    decision: 'reference-only',
    useful: 'Telegram casino mobile UI patterns in React/MUI',
    notes: 'Domain-risk reference; do not reuse deposit, wallet, or bonus mechanics without safety review.'
  },
  {
    repository: 'QI-D/mini-casino-frontend',
    category: 'igaming-reference',
    decision: 'needs-approval',
    useful: 'Casino frontend with deposit and bet-flow examples',
    notes: 'Money-like flows plus no clear license signal during discovery; approval and audit required.'
  },
  {
    repository: 'mooncitydev/jackpot-game-web3-onchain',
    category: 'igaming-reference',
    decision: 'needs-approval',
    useful: 'Solana jackpot app patterns with Next.js and Anchor surfaces',
    notes: 'On-chain gambling and wallet flow risk; security, legal, and responsible-gaming review required.'
  },
  {
    repository: 'marianapatcosta/js-slots-cra',
    category: 'igaming-reference',
    decision: 'reference-only',
    useful: 'Slot-machine PWA patterns with React, TypeScript, i18n, and GSAP',
    notes: 'Useful animation/UI reference; license signal must be verified before code reuse.'
  },
  {
    repository: 'PrzemoProgrammer/Slot-Machine',
    category: 'igaming-reference',
    decision: 'needs-approval',
    useful: 'Slot-machine UI with GSAP, PixiJS, Howler, PayPal, and socket.io surfaces',
    notes: 'Payment and real-time dependencies require audit before any reuse.'
  },
  {
    repository: 'dannycahyo/judol-demo',
    category: 'igaming-reference',
    decision: 'adapt-only',
    useful: 'Educational gambling-awareness slot simulator',
    notes: 'Best fit for ethical iGaming examples; preserve anti-gambling and responsible-design framing.'
  }
];

function parseArgs(argv) {
  return {
    write: argv.includes('--write'),
    check: argv.includes('--check'),
    json: argv.includes('--json')
  };
}

function githubGet(pathname) {
  const token = process.env.GITHUB_TOKEN;
  const headers = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'antigravity-legion-kit-frontend-catalog-refresh'
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  return new Promise((resolve, reject) => {
    const request = https.get({ hostname: 'api.github.com', path: pathname, headers }, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => { body += chunk; });
      response.on('end', () => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          let message = body.slice(0, 200).replace(/\s+/g, ' ').trim();
          try {
            const parsed = JSON.parse(body);
            message = parsed.message || message;
          } catch {
            // Keep the compact raw body excerpt.
          }
          reject(new Error(`GitHub API ${response.statusCode} for ${pathname}: ${message}`));
          return;
        }
        resolve(JSON.parse(body));
      });
    });
    request.on('error', reject);
    request.setTimeout(15000, () => {
      request.destroy(new Error(`GitHub API timeout for ${pathname}`));
    });
  });
}

function licenseSignal(repo) {
  return repo.license?.spdx_id || 'no GitHub license signal observed';
}

function summarizeMarkers(paths) {
  return {
    skillFiles: paths.filter((entry) => entry.endsWith('/SKILL.md') || entry === 'SKILL.md').length,
    packageManifests: paths.filter((entry) => /(^|\/)(package\.json|pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb)$/.test(entry)).length,
    installers: paths.filter((entry) => /(^|\/)(install\.(sh|py|ps1|js|mjs)|setup\.(sh|py)|bootstrap\.(sh|js|mjs))$/.test(entry)).length,
    mcpFiles: paths.filter((entry) => entry.toLowerCase().includes('mcp')).length,
    walletOrPaymentFiles: paths.filter((entry) => /wallet|payment|paypal|stripe|deposit|withdraw|kyc|anchor|solana|web3/i.test(entry)).length,
    animationFiles: paths.filter((entry) => /framer|motion|gsap|three|pixi|lottie/i.test(entry)).length
  };
}

function detectBlockers(candidate, repo, paths, treeError) {
  const blockers = [];
  const markers = summarizeMarkers(paths);
  const license = licenseSignal(repo);
  const archived = repo.archived === true;
  const isIGaming = candidate.category === 'igaming-reference';
  const isHugePack = markers.skillFiles > 50 || repo.size > 100000;

  if (candidate.decision === 'needs-approval') blockers.push('explicit user approval required before import, install, or code reuse');
  if (candidate.decision === 'reference-only') blockers.push('reference-only: do not copy code without a separate license and file audit');
  if (license === 'no GitHub license signal observed' || license === 'NOASSERTION') blockers.push('license compatibility not established');
  if (archived) blockers.push('repository is archived or read-only');
  if (treeError) blockers.push(`GitHub metadata/tree inspection failed: ${treeError}`);
  if (markers.installers) blockers.push('installer/bootstrap scripts present; do not run before audit');
  if (markers.packageManifests) blockers.push('dependency manifests present; dependency and postinstall review required');
  if (markers.mcpFiles) blockers.push('MCP/tooling files present; permission surface review required');
  if (isHugePack) blockers.push('large pack/token-load risk; selective intake only');
  if (isIGaming) blockers.push('gambling or money-like domain; responsible-gaming and regulatory review required');
  if (markers.walletOrPaymentFiles) blockers.push('wallet/payment/deposit/KYC files detected; GUARDIAN review required');

  return blockers.length ? blockers : ['no hard blocker from metadata; still audit exact files before use'];
}

function recommendedAction(candidate) {
  if (candidate.decision === 'adapt-only') {
    if (candidate.category === 'igaming-reference') {
      return 'adapt UI/education patterns only; keep responsible-gaming guardrails and avoid money-flow reuse';
    }
    return 'adapt selected patterns into the local frontend workflow; do not run external code';
  }
  if (candidate.decision === 'reference-only') return 'read for inspiration and taxonomy; do not copy code or install packages';
  if (candidate.decision === 'needs-approval') return 'hold until user approval, license review, dependency audit, and domain safety review';
  if (candidate.decision === 'blocked') return 'block by default until a new audit changes the decision';
  return 'audit before use';
}

function intakePlan(candidate) {
  if (candidate.category === 'landing-template') return {
    owner: 'GUARDIAN',
    handoffs: [
      { name: 'PICTOR', trigger: 'the audited landing pattern must be implemented' },
      { name: 'AEDILIS', trigger: 'layout, component-system fit, or accessibility needs design judgment' },
      { name: 'INDAGATOR', trigger: 'public-page SEO, schema, metadata, or Core Web Vitals matter' },
      { name: 'MERCATOR', trigger: 'offer, funnel, or conversion hypothesis is unresolved' }
    ]
  };
  if (candidate.category === 'igaming-reference') return {
    owner: 'GUARDIAN',
    handoffs: [
      { name: 'ALEATOR', trigger: 'responsible-gaming, reward, odds, or dark-pattern risk must be judged' },
      { name: 'PICTOR', trigger: 'approved iGaming UI patterns must be implemented' },
      { name: 'AEDILIS', trigger: 'mobile flow, hierarchy, or accessibility needs design judgment' },
      { name: 'INDAGATOR', trigger: 'public game-promo page SEO or metadata matters' }
    ]
  };
  if (candidate.category === 'motion-catalog') return {
    owner: 'GUARDIAN',
    handoffs: [
      { name: 'PICTOR', trigger: 'the audited motion pattern must be implemented' },
      { name: 'AEDILIS', trigger: 'motion affects hierarchy, accessibility, or interaction meaning' },
      { name: 'TESTER', trigger: 'reduced-motion, browser, or performance proof is needed' }
    ]
  };
  if (candidate.category === 'component-catalog') return {
    owner: 'GUARDIAN',
    handoffs: [
      { name: 'AEDILIS', trigger: 'component API, state model, or design-system fit must be decided' },
      { name: 'PICTOR', trigger: 'the audited component pattern must be implemented' },
      { name: 'TESTER', trigger: 'component states or interaction proof is needed' }
    ]
  };
  return {
    owner: 'GUARDIAN',
    handoffs: [
      { name: 'AEDILIS', trigger: 'source ideas must become a UI architecture decision' },
      { name: 'PICTOR', trigger: 'source ideas must become frontend code' }
    ]
  };
}

function nextWorkflow(candidate) {
  if (candidate.category === 'landing-template') return 'frontend-landing-igaming -> ui-design-pass -> browser-qa';
  if (candidate.category === 'igaming-reference') return 'frontend-landing-igaming -> external-skill-audit -> quality-gate';
  if (candidate.category === 'motion-catalog') return 'frontend-landing-igaming -> interface-polish-pass -> performance-budget-audit';
  return 'frontend-landing-igaming -> design-system-audit -> quality-gate';
}

async function inspectRepo(candidate) {
  let repo;
  let repoError = '';
  try {
    repo = await githubGet(`/repos/${candidate.repository}`);
  } catch (error) {
    repoError = error.message;
    repo = {
      html_url: `https://github.com/${candidate.repository}`,
      description: '',
      stargazers_count: 0,
      forks_count: 0,
      open_issues_count: 0,
      pushed_at: 'unknown',
      updated_at: 'unknown',
      archived: false,
      size: 0,
      license: null
    };
  }
  let paths = [];
  let treeError = repoError;
  if (!repoError) {
    try {
      const tree = await githubGet(`/repos/${candidate.repository}/git/trees/HEAD?recursive=1`);
      paths = (tree.tree || []).map((entry) => entry.path).sort();
    } catch (error) {
      treeError = error.message;
    }
  }

  const markers = summarizeMarkers(paths);
  const blockers = detectBlockers(candidate, repo, paths, treeError);
  const plan = intakePlan(candidate);
  return {
    repository: candidate.repository,
    url: repo.html_url,
    description: repo.description || '',
    category: candidate.category,
    decision: candidate.decision,
    stars: repo.stargazers_count || 0,
    forks: repo.forks_count || 0,
    openIssues: repo.open_issues_count || 0,
    pushedAt: repo.pushed_at || repo.updated_at,
    archived: repo.archived === true,
    license: licenseSignal(repo),
    metadataError: repoError || treeError || '',
    useful: candidate.useful,
    notes: candidate.notes,
    markers,
    intake: {
      action: recommendedAction(candidate),
      blockers,
      owner: plan.owner,
      handoffs: plan.handoffs,
      nextWorkflow: nextWorkflow(candidate)
    }
  };
}

function escapeCell(value) {
  return String(value).replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

function buildCatalog(entries, generatedAt = new Date().toISOString()) {
  return {
    version: CATALOG_VERSION,
    generatedAt,
    policy: {
      installAllowlist: false,
      defaultDecision: 'adapt-only',
      requiredWorkflow: 'frontend-landing-igaming',
      safetyGate: 'external-skill-audit',
      blockedDefaults: [
        'running external UI templates before audit',
        'bulk-copying component catalogs into a product',
        'copying unlicensed landing sections',
        'reusing gambling, wallet, deposit, withdrawal, bonus, or KYC flows without GUARDIAN review',
        'shipping iGaming pages without responsible-gaming and age-appropriateness checks'
      ]
    },
    categories: {
      'agent-skill': 'Frontend-specific AI-agent skills and prompt packs.',
      'landing-template': 'Landing-page and SaaS/product-page implementation references.',
      'motion-catalog': 'Animation and motion component references.',
      'component-catalog': 'Reusable UI component discovery/reference sources.',
      'igaming-reference': 'Casino, betting, slot, jackpot, and gambling-awareness UI references.'
    },
    entries
  };
}

function renderMarkdown(catalog) {
  const rows = catalog.entries.map((entry) => [
    `\`${entry.repository}\``,
    entry.category,
    entry.license,
    entry.decision,
    entry.useful,
    `${entry.notes} Stars: ${entry.stars}; archived: ${entry.archived ? 'yes' : 'no'}; pushed: ${entry.pushedAt}.`
  ]);

  const categorySections = Object.entries(catalog.categories)
    .map(([name, description]) => `- \`${name}\`: ${description}`)
    .join('\n');

  return `# Frontend, Landing, Motion, and iGaming Sources

Generated: ${catalog.generatedAt}

This catalog records GitHub repositories found during frontend, landing-page, motion, and iGaming discovery for Antigravity. It is a discovery aid, not an install allowlist.

## Safety Policy

- Do not clone-run, install, or execute external templates, component catalogs, or skill packs from this catalog without a separate audit.
- Prefer \`adapt-only\`: translate a specific inspected idea into the target project's existing design system and stack.
- Treat no-license and archived repositories as reference-only unless a later audit proves safe reuse.
- iGaming references require responsible-gaming, age-appropriateness, odds/RTP/provably-fair claim review, and GUARDIAN approval for wallet/payment/deposit/bonus flows.
- Motion sources must preserve accessibility, reduced-motion behavior, Core Web Vitals, and bundle-size discipline.

## Categories

${categorySections}

## Candidates

| Repository | Category | License Signal | Safety Decision | Useful Assets | Notes |
| --- | --- | --- | --- | --- | --- |
${rows.map((row) => `| ${row.map(escapeCell).join(' | ')} |`).join('\n')}

## Patterns Worth Adapting

- Frontend work: inspect stack, tokens, components, routes, data states, and responsive constraints before drawing a new system.
- Landing pages: pair visual polish with offer clarity, metadata, schema, Core Web Vitals, conversion tracking, and crawler-readable content.
- Motion: use animation to clarify state, create feedback, or guide attention; respect \`prefers-reduced-motion\` and avoid LCP path bloat.
- iGaming: keep costs, odds, eligibility, terms, limits, and support routes visible; never use fake scarcity, fake urgency, guaranteed-win language, or deceptive rewards.
- External sources: extract one inspected pattern at a time and route through \`frontend_source_intake\` before use.

## Blocked Defaults

- Installing a full UI library or template only because it looks good.
- Copying unlicensed landing sections or component code.
- Importing gambling, wallet, deposit, withdrawal, bonus, affiliate, or KYC flows without security and regulatory review.
- Shipping iGaming pages without responsible-gaming and dark-pattern review.
- Adding animation that breaks keyboard access, reduced-motion preferences, text fit, or mobile layout stability.
`;
}

function checkCatalog() {
  const text = fs.readFileSync(CATALOG_PATH, 'utf8');
  const missing = CANDIDATES.filter((candidate) => !text.includes(candidate.repository)).map((candidate) => candidate.repository);
  if (missing.length) {
    throw new Error(`frontend catalog missing candidate(s): ${missing.join(', ')}`);
  }
  if (!text.includes('not an install allowlist')) {
    throw new Error('frontend catalog missing install allowlist safety wording');
  }
  if (!text.includes('responsible-gaming')) {
    throw new Error('frontend catalog missing responsible-gaming safety wording');
  }
  if (!fs.existsSync(CATALOG_JSON_PATH)) {
    throw new Error(`frontend catalog JSON missing: ${CATALOG_JSON_PATH}`);
  }
  const catalog = JSON.parse(fs.readFileSync(CATALOG_JSON_PATH, 'utf8'));
  const jsonMissing = CANDIDATES.filter((candidate) => !catalog.entries?.some((entry) => entry.repository === candidate.repository)).map((candidate) => candidate.repository);
  if (jsonMissing.length) {
    throw new Error(`frontend catalog JSON missing candidate(s): ${jsonMissing.join(', ')}`);
  }
  const intakeMissing = catalog.entries.filter((entry) => !entry.intake?.action || !Array.isArray(entry.intake?.blockers) || !entry.intake?.owner || !Array.isArray(entry.intake?.handoffs));
  if (intakeMissing.length) {
    throw new Error(`frontend catalog JSON missing intake guidance: ${intakeMissing.map((entry) => entry.repository).join(', ')}`);
  }
  return { ok: true, candidates: CANDIDATES.length, json: true };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.check) {
    const result = checkCatalog();
    process.stdout.write(options.json ? `${JSON.stringify(result)}\n` : `frontend catalog check: pass (${result.candidates} candidates)\n`);
    return;
  }

  const entries = [];
  for (const candidate of CANDIDATES) {
    entries.push(await inspectRepo(candidate));
  }

  const catalog = buildCatalog(entries);

  if (options.json) {
    process.stdout.write(`${JSON.stringify(catalog, null, 2)}\n`);
    return;
  }

  const markdown = renderMarkdown(catalog);
  if (options.write) {
    fs.writeFileSync(CATALOG_PATH, markdown);
    fs.writeFileSync(CATALOG_JSON_PATH, `${JSON.stringify(catalog, null, 2)}\n`);
    process.stdout.write(`frontend catalog refreshed: ${CATALOG_PATH} and ${CATALOG_JSON_PATH}\n`);
  } else {
    process.stdout.write(markdown);
  }
}

main().catch((error) => {
  process.stderr.write(`frontend catalog refresh failed: ${error.message}\n`);
  process.exitCode = 1;
});
