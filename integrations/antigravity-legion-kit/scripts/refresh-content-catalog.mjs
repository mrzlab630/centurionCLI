#!/usr/bin/env node
import fs from 'node:fs';
import https from 'node:https';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const CATALOG_PATH = path.join(KIT_ROOT, 'docs', 'CONTENT_COPY_CATALOG.md');
const CATALOG_JSON_PATH = path.join(KIT_ROOT, 'docs', 'content-copy-catalog.json');
const CATALOG_VERSION = 1;

const CANDIDATES = [
  {
    repository: '18F/content-guide',
    category: 'content-style-guide',
    decision: 'adapt-only',
    useful: 'Plain-language, inclusive, accessible government content guidance',
    notes: 'Good baseline for clarity, accessibility, error states, and public-service tone.'
  },
  {
    repository: 'alphagov/govuk-design-system',
    category: 'content-design-system',
    decision: 'adapt-only',
    useful: 'Production design-system content patterns, error messages, form labels, and service copy',
    notes: 'Strong model for practical UX copy tied to components and user journeys.'
  },
  {
    repository: 'MicrosoftDocs/microsoft-style-guide',
    category: 'content-style-guide',
    decision: 'reference-only',
    useful: 'Technical style, terminology, UI text, accessibility, and globalization guidance',
    notes: 'Use for terminology discipline and localization-aware technical copy.'
  },
  {
    repository: 'mailchimp/content-style-guide',
    category: 'brand-voice-system',
    decision: 'reference-only',
    useful: 'Voice, tone, writing principles, and content-type guidance',
    notes: 'Useful brand-voice reference; do not copy brand-specific phrasing.'
  },
  {
    repository: 'Shopify/polaris',
    category: 'content-design-system',
    decision: 'adapt-only',
    useful: 'Product content guidance, components, commerce/admin UX patterns, and empty/error states',
    notes: 'Good for operational dashboards and merchant/admin product language.'
  },
  {
    repository: 'primer/design',
    category: 'content-design-system',
    decision: 'adapt-only',
    useful: 'Design-system patterns for labels, buttons, navigation, status, and docs-like product surfaces',
    notes: 'Use for concise developer/product UI terminology and component-bound copy.'
  },
  {
    repository: 'w3c/wai-website',
    category: 'accessibility-copy',
    decision: 'reference-only',
    useful: 'Accessibility writing, labels, errors, instructions, and inclusive design references',
    notes: 'Use for accessibility checks and wording around disabled/error/instruction states.'
  },
  {
    repository: 'growthbook/growthbook',
    category: 'experimentation-copy',
    decision: 'reference-only',
    useful: 'Feature-flag and A/B-test platform patterns for copy experiments and measurable variants',
    notes: 'Reference for testable copy hypotheses; do not import platform code into this kit.'
  },
  {
    repository: 'posthog/posthog',
    category: 'experimentation-copy',
    decision: 'reference-only',
    useful: 'Product analytics and experimentation patterns for measuring CTA and funnel copy impact',
    notes: 'Reference for measurement thinking; dependency surface is far outside this kit.'
  },
  {
    repository: 'rmyndharis/antigravity-skills',
    category: 'agent-copy-skill',
    decision: 'adapt-only',
    useful: 'Large Antigravity skill catalog; may contain writing, marketing, content, and UX prompt examples',
    notes: 'Discovery only; selective intake through external_skill_intake and no bulk installs.'
  },
  {
    repository: 'sociilabs/claude-content-writer',
    category: 'agent-copy-skill',
    decision: 'needs-approval',
    useful: 'FindSkills-discovered content writer skill for blogs, newsletters, and human-sounding long-form content',
    notes: 'Guest FindSkills response hid source details during discovery; verify upstream before use.'
  },
  {
    repository: 'isaacavazquez/website',
    category: 'copywriting-reference',
    decision: 'needs-approval',
    useful: 'FindSkills-discovered Copywriting skill hint',
    notes: 'Guest FindSkills response hid source details during discovery; verify upstream before use.'
  },
  {
    repository: 'uswds/uswds-site',
    category: 'content-design-system',
    decision: 'adapt-only',
    useful: 'US Web Design System site guidance for content, components, accessibility, forms, and public-service pages',
    notes: 'Good source for content patterns tied to real components and accessibility requirements.'
  },
  {
    repository: 'salesforce-ux/design-system',
    category: 'content-design-system',
    decision: 'adapt-only',
    useful: 'Salesforce Lightning Design System patterns for enterprise UI labels, forms, empty states, errors, and help text',
    notes: 'Useful for B2B/admin surfaces; adapt patterns into the target product voice.'
  },
  {
    repository: 'carbon-design-system/carbon',
    category: 'content-design-system',
    decision: 'adapt-only',
    useful: 'Carbon Design System component patterns, content guidance, state text, and enterprise product language references',
    notes: 'Good for dense operational tools and component-bound UX copy.'
  },
  {
    repository: 'f/awesome-chatgpt-prompts',
    category: 'prompt-copy-reference',
    decision: 'reference-only',
    useful: 'Large prompt catalog with writing, editing, marketing, and ideation examples',
    notes: 'Prompt catalog only; prompts may contain unsafe assumptions or generic output patterns.'
  },
  {
    repository: 'dair-ai/Prompt-Engineering-Guide',
    category: 'prompt-copy-reference',
    decision: 'reference-only',
    useful: 'Prompt engineering guide and examples useful for structuring repeatable copy tasks',
    notes: 'Use for prompt structure, not for product claims or final copy.'
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
    'User-Agent': 'antigravity-legion-kit-content-catalog-refresh'
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
    packageManifests: paths.filter((entry) => /(^|\/)(package\.json|pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb|requirements\.txt|pyproject\.toml)$/.test(entry)).length,
    installers: paths.filter((entry) => /(^|\/)(install\.(sh|py|ps1|js|mjs)|setup\.(sh|py)|bootstrap\.(sh|js|mjs))$/.test(entry)).length,
    docs: paths.filter((entry) => /(^|\/)(docs|content|guides|patterns|components|src|packages)\//i.test(entry) && /\.(md|mdx|json|yml|yaml)$/.test(entry)).length,
    localizationFiles: paths.filter((entry) => /locale|locales|i18n|translations|lang|messages/i.test(entry)).length,
    experimentationFiles: paths.filter((entry) => /experiment|ab-test|feature-flag|analytics|event|metric/i.test(entry)).length,
    highRiskCopyFiles: paths.filter((entry) => /pricing|checkout|payment|wallet|deposit|withdraw|medical|health|legal|gambling|casino|betting|bonus/i.test(entry)).length
  };
}

function detectBlockers(candidate, repo, paths, treeError) {
  const blockers = [];
  const markers = summarizeMarkers(paths);
  const license = licenseSignal(repo);
  const archived = repo.archived === true;
  const hiddenSource = candidate.notes.toLowerCase().includes('guest findskills response hid source');

  if (candidate.decision === 'needs-approval') blockers.push('explicit user approval required before import, install, or copy reuse');
  if (candidate.decision === 'reference-only') blockers.push('reference-only: do not copy source text or brand-specific phrasing without a separate license and content audit');
  if (license === 'no GitHub license signal observed' || license === 'NOASSERTION') blockers.push('license compatibility not established');
  if (archived) blockers.push('repository is archived or read-only');
  if (treeError) blockers.push(`GitHub metadata/tree inspection failed: ${treeError}`);
  if (hiddenSource) blockers.push('FindSkills guest result hid upstream source details; verify repository identity before use');
  if (markers.installers) blockers.push('installer/bootstrap scripts present; do not run before audit');
  if (markers.packageManifests) blockers.push('dependency manifests present; dependency and postinstall review required');
  if (markers.skillFiles > 50) blockers.push('large skill pack/token-load risk; selective intake only');
  if (markers.highRiskCopyFiles) blockers.push('high-risk copy surface detected; claims, legal, money, health, or gambling wording needs CENSOR/GUARDIAN review');
  if (candidate.category === 'copywriting-reference') blockers.push('sales-copy source may contain unsupported claims or manipulative patterns; claim audit required');
  if (candidate.category === 'brand-voice-system') blockers.push('brand-specific voice; adapt principles, not phrasing');

  return blockers.length ? blockers : ['no hard blocker from metadata; still audit exact files and claims before use'];
}

function recommendedAction(candidate) {
  if (candidate.decision === 'adapt-only') return 'adapt structure, terminology rules, and content patterns into the local content workflow; do not copy brand-specific text';
  if (candidate.decision === 'reference-only') return 'read for guidance and taxonomy; do not copy source text, examples, claims, or brand phrasing';
  if (candidate.decision === 'needs-approval') return 'hold until user approval, source verification, license review, and claim-safety audit';
  if (candidate.decision === 'blocked') return 'block by default until a new audit changes the decision';
  return 'audit before use';
}

function intakePlan(candidate) {
  if (candidate.category === 'experimentation-copy') return {
    owner: 'CENSOR',
    handoffs: [
      { name: 'MERCATOR', trigger: 'copy experiment needs positioning, funnel, or metric design' },
      { name: 'NOMENCLATOR', trigger: 'approved experiment direction must become source UI copy' },
      { name: 'PICTOR', trigger: 'approved copy variants must be implemented or fit-tested' }
    ]
  };
  if (candidate.category === 'content-design-system') return {
    owner: 'CENSOR',
    handoffs: [
      { name: 'NOMENCLATOR', trigger: 'component-bound patterns must become product language' },
      { name: 'AEDILIS', trigger: 'copy placement, hierarchy, or accessibility constrains wording' },
      { name: 'GLOSSATOR', trigger: 'localization, placeholders, pluralization, or text expansion risk appears' },
      { name: 'PICTOR', trigger: 'approved copy must be wired into UI components' }
    ]
  };
  if (candidate.category === 'content-style-guide') return {
    owner: 'CENSOR',
    handoffs: [
      { name: 'NOMENCLATOR', trigger: 'style guidance must become product language rules' },
      { name: 'GLOSSATOR', trigger: 'terminology or localization readiness must be checked' }
    ]
  };
  if (candidate.category === 'accessibility-copy') return {
    owner: 'CENSOR',
    handoffs: [
      { name: 'NOMENCLATOR', trigger: 'accessible wording must become source UI copy' },
      { name: 'AEDILIS', trigger: 'labels, errors, or instructions affect interaction design' },
      { name: 'GLOSSATOR', trigger: 'translated labels, placeholders, or plural rules may break accessibility' }
    ]
  };
  if (candidate.category === 'brand-voice-system') return {
    owner: 'CENSOR',
    handoffs: [
      { name: 'NOMENCLATOR', trigger: 'voice principles must become a product language system' },
      { name: 'MERCATOR', trigger: 'voice must align with positioning or audience strategy' }
    ]
  };
  return {
    owner: 'CENSOR',
    handoffs: [
      { name: 'NOMENCLATOR', trigger: 'safe source patterns must become product UI copy' },
      { name: 'MERCATOR', trigger: 'copy needs offer, audience, funnel, or conversion framing' },
      { name: 'GUARDIAN', trigger: 'license, dependency, payment, wallet, or regulated-domain risk appears' }
    ]
  };
}

function nextWorkflow(candidate) {
  if (candidate.category === 'experimentation-copy') return 'content-copy-system -> brand-voice-pass -> quality-gate';
  if (candidate.category === 'content-design-system') return 'content-copy-system -> ui-design-pass -> browser-qa';
  if (candidate.category === 'accessibility-copy') return 'content-copy-system -> design-system-audit -> quality-gate';
  return 'content-copy-system -> brand-voice-pass -> quality-gate';
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
      requiredWorkflow: 'content-copy-system',
      safetyGate: 'external-skill-audit',
      blockedDefaults: [
        'copying sales copy without checking product truth',
        'copying testimonials, review counts, scarcity, urgency, guarantees, or revenue claims',
        'copying brand-specific phrasing from style guides',
        'using hidden-source FindSkills results as trusted install sources',
        'shipping high-risk finance, health, legal, wallet, betting, or iGaming copy without CENSOR/GUARDIAN review'
      ]
    },
    categories: {
      'content-style-guide': 'Plain-language, terminology, tone, accessibility, and localization guidance.',
      'content-design-system': 'Component-bound UX copy patterns, states, labels, errors, and navigation language.',
      'brand-voice-system': 'Voice and tone systems for deriving brand language without copying phrasing.',
      'accessibility-copy': 'Accessible labels, instructions, error copy, and inclusive content guidance.',
      'experimentation-copy': 'A/B testing and analytics references for measurable copy variants.',
      'agent-copy-skill': 'External agent skills or prompt packs for content/copy tasks.',
      'long-form-content': 'Blog, newsletter, docs, and long-form content generation references.',
      'copywriting-reference': 'Sales-copy references that require strict claim and ethics review.',
      'prompt-copy-reference': 'Prompt catalogs and prompt-engineering references for repeatable copy tasks.'
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

  return `# Content, Copywriting, UX Writing, and Product Language Sources

Generated: ${catalog.generatedAt}

This catalog records GitHub repositories and discovery hints for content design, UX writing, product language, naming, CTA, conversion copy, and measurable copy experiments. It is a discovery aid, not an install allowlist.

## Safety Policy

- Do not copy external sales copy, style-guide phrasing, testimonials, claims, scarcity, urgency, or legal wording without a separate content and license audit.
- Prefer \`adapt-only\`: translate a specific inspected pattern into the product's existing voice, behavior, constraints, and component system.
- Treat FindSkills guest results as search hints only when source details are hidden.
- Public-page copy must be checked for search intent, metadata, schema, accessibility, and localization readiness.
- High-risk finance, health, legal, wallet, betting, casino, iGaming, pricing, checkout, or bonus copy requires CENSOR/GUARDIAN review before shipping.

## Categories

${categorySections}

## Candidates

| Repository | Category | License Signal | Safety Decision | Useful Assets | Notes |
| --- | --- | --- | --- | --- | --- |
${rows.map((row) => `| ${row.map(escapeCell).join(' | ')} |`).join('\n')}

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
`;
}

function checkCatalog() {
  const text = fs.readFileSync(CATALOG_PATH, 'utf8');
  const missing = CANDIDATES.filter((candidate) => !text.includes(candidate.repository)).map((candidate) => candidate.repository);
  if (missing.length) {
    throw new Error(`content catalog missing candidate(s): ${missing.join(', ')}`);
  }
  if (!text.includes('not an install allowlist')) {
    throw new Error('content catalog missing install allowlist safety wording');
  }
  if (!text.includes('Claim safety')) {
    throw new Error('content catalog missing claim safety wording');
  }
  if (!fs.existsSync(CATALOG_JSON_PATH)) {
    throw new Error(`content catalog JSON missing: ${CATALOG_JSON_PATH}`);
  }
  const catalog = JSON.parse(fs.readFileSync(CATALOG_JSON_PATH, 'utf8'));
  const jsonMissing = CANDIDATES.filter((candidate) => !catalog.entries?.some((entry) => entry.repository === candidate.repository)).map((candidate) => candidate.repository);
  if (jsonMissing.length) {
    throw new Error(`content catalog JSON missing candidate(s): ${jsonMissing.join(', ')}`);
  }
  const intakeMissing = catalog.entries.filter((entry) => !entry.intake?.action || !Array.isArray(entry.intake?.blockers) || !entry.intake?.owner || !Array.isArray(entry.intake?.handoffs));
  if (intakeMissing.length) {
    throw new Error(`content catalog JSON missing intake guidance: ${intakeMissing.map((entry) => entry.repository).join(', ')}`);
  }
  return { ok: true, candidates: CANDIDATES.length, json: true };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.check) {
    const result = checkCatalog();
    process.stdout.write(options.json ? `${JSON.stringify(result)}\n` : `content catalog check: pass (${result.candidates} candidates)\n`);
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
    process.stdout.write(`content catalog refreshed: ${CATALOG_PATH} and ${CATALOG_JSON_PATH}\n`);
  } else {
    process.stdout.write(markdown);
  }
}

main().catch((error) => {
  process.stderr.write(`content catalog refresh failed: ${error.message}\n`);
  process.exitCode = 1;
});
