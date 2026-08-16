#!/usr/bin/env node
import fs from 'node:fs';
import https from 'node:https';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const CATALOG_PATH = path.join(KIT_ROOT, 'docs', 'EXTERNAL_CATALOG.md');
const CATALOG_JSON_PATH = path.join(KIT_ROOT, 'docs', 'external-catalog.json');
const CATALOG_VERSION = 1;

const CANDIDATES = [
  'rmyndharis/antigravity-skills',
  'rominirani/antigravity-skills',
  'google-antigravity/antigravity-sdk-python',
  'bonnguyenitc/antigravity-superpowers',
  'anhtester/antigravity-testing-kit',
  'tknvstp/antigravity-skills',
  'WilkoMarketing/antigravity-n8n-skills',
  'sabahattink/antigravity-fullstack-hq',
  'krishnakanthb13/everything-antigravity',
  'adamreger/ecc-antigravity'
];

const MANUAL_NOTES = {
  'rmyndharis/antigravity-skills': {
    decision: 'adapt-only',
    useful: '`catalog.json`, `bundles.json`, 300+ `skills/*/SKILL.md`',
    notes: 'Strong discovery catalog and token-efficiency warning; do not install all skills.'
  },
  'rominirani/antigravity-skills': {
    decision: 'adapt-only',
    useful: '`skills_tutorial/*/SKILL.md`',
    notes: 'Good examples for basic routing, assets, few-shot examples, deterministic scripts.'
  },
  'google-antigravity/antigravity-sdk-python': {
    decision: 'reference-only',
    useful: '`skills/google-antigravity-sdk/SKILL.md`, SDK references/examples',
    notes: 'Future path for programmatic agents; PyPI package install needs separate approval.'
  },
  'bonnguyenitc/antigravity-superpowers': {
    decision: 'adapt-only',
    useful: '`.agent/rules`, `.agent/workflows`, focused planning/review/verification skills',
    notes: 'Useful development loop patterns; contains scripts and npm init path, so do not run installer blindly.'
  },
  'anhtester/antigravity-testing-kit': {
    decision: 'adapt-only',
    useful: 'QA rules, flaky-test workflow, automation/testing skills',
    notes: 'Strong QA patterns; scripts include Jira/Google Sheets integrations requiring credentials.'
  },
  'tknvstp/antigravity-skills': {
    decision: 'adapt-only',
    useful: '`.agent/workflows/skill-creator.md`, `.agent/workflows/skill-migrator.md`',
    notes: 'Useful Antigravity migration decision trees; language is Chinese.'
  },
  'WilkoMarketing/antigravity-n8n-skills': {
    decision: 'needs-approval',
    useful: 'seven `SKILL.md` files for n8n',
    notes: 'Domain-specific; likely useful only for n8n projects with MCP/tooling.'
  },
  'sabahattink/antigravity-fullstack-hq': {
    decision: 'needs-approval',
    useful: 'skills/workflows/agents',
    notes: 'Installer writes global `.gemini` and `.claude`; overlaps with local Legion.'
  },
  'krishnakanthb13/everything-antigravity': {
    decision: 'needs-approval',
    useful: '`.agent/workflows`, `skills`, rules docs',
    notes: 'Installer writes global directories and includes many workflows; sample selectively only.'
  },
  'adamreger/ecc-antigravity': {
    decision: 'adapt-only',
    useful: 'workflows, skills, rules, MCP configs',
    notes: 'Marked pre-production; uses `.antigravity` paths that do not match this host\'s observed `.agent` selectors.'
  }
};

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
    'User-Agent': 'antigravity-legion-kit-catalog-refresh'
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  return new Promise((resolve, reject) => {
    const request = https.get({ hostname: 'api.github.com', path: pathname, headers }, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => { body += chunk; });
      response.on('end', () => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`GitHub API ${response.statusCode} for ${pathname}: ${body.slice(0, 200)}`));
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

function classify(paths) {
  const hasDotAgent = paths.some((entry) => entry.startsWith('.agent/'));
  const hasSkills = paths.some((entry) => entry.endsWith('/SKILL.md') || entry === 'SKILL.md');
  const hasMcp = paths.some((entry) => entry.endsWith('mcp_config.json') || entry.includes('mcp-config'));
  const hasSdk = paths.some((entry) => entry.startsWith('google/') || entry.includes('sdk'));
  const hasInstaller = paths.some((entry) => /(^|\/)(install\.(sh|py|ps1|js)|package\.json)$/.test(entry));
  const hasAntigravityDir = paths.some((entry) => entry.startsWith('.antigravity/'));

  if (hasDotAgent) return 'native-agent-pack';
  if (hasMcp || hasSdk) return 'mcp-or-sdk';
  if (hasSkills) return 'skill-library';
  if (hasInstaller) return 'installer-pack';
  if (hasAntigravityDir) return 'legacy-antigravity-layout';
  return 'reference-only';
}

function licenseSignal(repo) {
  return repo.license?.spdx_id || 'no GitHub license signal observed';
}

function safetyDecision(repoName, type, paths) {
  const manual = MANUAL_NOTES[repoName];
  if (manual?.decision) return manual.decision;
  const hasGlobalInstaller = paths.some((entry) => /(^|\/)install\.(sh|py|ps1|js)$/.test(entry));
  if (hasGlobalInstaller || type === 'installer-pack') return 'needs-approval';
  if (type === 'mcp-or-sdk') return 'reference-only';
  return 'adapt-only';
}

async function inspectRepo(fullName) {
  const repo = await githubGet(`/repos/${fullName}`);
  const tree = await githubGet(`/repos/${fullName}/git/trees/HEAD?recursive=1`);
  const paths = (tree.tree || []).map((entry) => entry.path).sort();
  const type = classify(paths);
  const manual = MANUAL_NOTES[fullName] || {};
  const license = licenseSignal(repo);
  const decision = safetyDecision(fullName, type, paths);
  const markers = summarizeMarkers(paths);
  return {
    repository: fullName,
    url: repo.html_url,
    description: repo.description || '',
    stars: repo.stargazers_count || 0,
    forks: repo.forks_count || 0,
    openIssues: repo.open_issues_count || 0,
    pushedAt: repo.pushed_at || repo.updated_at,
    license,
    type,
    useful: manual.useful || inferUseful(paths),
    decision,
    notes: manual.notes || inferNotes(type, paths),
    markers,
    intake: buildIntakeGuidance({ repoName: fullName, type, decision, license, paths, markers })
  };
}

function buildIntakeGuidance({ repoName, type, decision, license, paths, markers }) {
  return {
    action: recommendedAction(decision, type),
    blockers: safetyBlockers({ repoName, type, decision, license, paths, markers }),
    owner: 'GUARDIAN',
    handoffs: [
      { name: 'ARMARIUS', trigger: 'a missing capability requires more external skill discovery' },
      { name: 'ARTIFEX', trigger: 'an accepted asset must be migrated into a local rule, workflow, skill, or MCP surface' },
      { name: 'CENSOR', trigger: 'the safety decision or assumptions need adversarial verification' },
      { name: 'OPTIO', trigger: 'the intake changes Legion routing or task ownership' }
    ],
    nextWorkflow: decision === 'blocked' ? 'external-skill-audit' : 'external-skill-audit -> skill-migrator -> smoke'
  };
}

function recommendedAction(decision, type) {
  if (decision === 'accept') return 'copy only the specific audited non-executable assets that fill a local gap';
  if (decision === 'adapt-only') return 'adapt selected ideas into local rules/workflows; do not run repository code';
  if (decision === 'reference-only') {
    return type === 'mcp-or-sdk'
      ? 'use as documentation for a future SDK/MCP track; require dependency and permission review first'
      : 'read as reference material; do not install as a pack';
  }
  if (decision === 'needs-approval') return 'hold until explicit user approval and a file-by-file safety audit';
  return 'block by default until a new audit changes the decision';
}

function safetyBlockers({ repoName, type, decision, license, paths, markers }) {
  const blockers = [];
  const installers = paths.filter((entry) => /(^|\/)(install\.(sh|py|ps1|js)|setup\.(sh|py)|bootstrap\.(sh|js))$/.test(entry));
  const manifests = paths.filter((entry) => /(^|\/)(package\.json|pyproject\.toml|requirements\.txt|uv\.lock|pnpm-lock\.yaml|package-lock\.json|yarn\.lock)$/.test(entry));
  const mcpFiles = paths.filter((entry) => entry.endsWith('mcp_config.json') || entry.toLowerCase().includes('mcp'));

  if (decision === 'needs-approval') blockers.push('explicit approval required before import or install');
  if (license === 'no GitHub license signal observed' || license === 'NOASSERTION') blockers.push('license compatibility not established');
  if (installers.length) blockers.push(`installer scripts present: ${installers.slice(0, 3).join(', ')}`);
  if (manifests.length) blockers.push(`dependency manifests present: ${manifests.slice(0, 3).join(', ')}`);
  if (mcpFiles.length && type === 'mcp-or-sdk') blockers.push('MCP/SDK runtime permissions require separate review');
  if (markers.skillFiles > 50) blockers.push('large skill pack; selective import only');
  if (repoName === 'google-antigravity/antigravity-sdk-python') blockers.push('programmatic SDK path; keep separate from static .agent pack');

  return blockers.length ? blockers : ['no hard blocker from metadata; still audit exact files before use'];
}

function inferUseful(paths) {
  const useful = [];
  if (paths.some((entry) => entry.startsWith('.agent/rules/'))) useful.push('`.agent/rules`');
  if (paths.some((entry) => entry.startsWith('.agent/workflows/'))) useful.push('`.agent/workflows`');
  if (paths.some((entry) => entry.includes('/SKILL.md'))) useful.push('`SKILL.md` packages');
  if (paths.some((entry) => entry.includes('mcp'))) useful.push('MCP references');
  return useful.length ? useful.join(', ') : 'README/reference material';
}

function inferNotes(type, paths) {
  if (paths.some((entry) => /(^|\/)install\.(sh|py|ps1|js)$/.test(entry))) {
    return 'Contains installer scripts; audit before running.';
  }
  if (type === 'mcp-or-sdk') return 'Runtime integration path; audit dependencies, credentials, and permissions before use.';
  return 'Review individual files before copying; default to adapt-only.';
}

function summarizeMarkers(paths) {
  return {
    dotAgent: paths.filter((entry) => entry.startsWith('.agent/')).length,
    skillFiles: paths.filter((entry) => entry.endsWith('/SKILL.md') || entry === 'SKILL.md').length,
    workflows: paths.filter((entry) => entry.includes('/workflows/') && entry.endsWith('.md')).length,
    rules: paths.filter((entry) => entry.includes('/rules/') && entry.endsWith('.md')).length,
    scripts: paths.filter((entry) => /\.(sh|py|js|cjs|mjs|ps1)$/.test(entry)).length
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
      requiredWorkflow: 'external-skill-audit',
      blockedDefaults: [
        'bulk install-all for large packs',
        'running external installers before audit',
        'copying credential-bearing helper scripts',
        'adopting unverified directory layouts'
      ]
    },
    entries
  };
}

function renderMarkdown(catalog) {
  const rows = catalog.entries.map((entry) => [
    `\`${entry.repository}\``,
    entry.type,
    entry.license,
    entry.useful,
    entry.decision,
    `${entry.notes} Stars: ${entry.stars}; pushed: ${entry.pushedAt}.`
  ]);

  return `# External Antigravity Skill Sources

Generated: ${catalog.generatedAt}

This catalog records GitHub repositories found during the Antigravity skill search. It is a discovery aid, not an install allowlist.

## Safety Policy

- Do not run external installers or \`npx\` commands from this catalog without a separate audit.
- Prefer \`adapt-only\` unless a repository contains a small, inspectable, license-compatible asset that fills a specific gap.
- Large skill packs can increase token load and accidental activation. Install narrowly.
- MCP servers, SDKs, and helper scripts require extra review for filesystem, shell, browser, cloud, wallet, database, and credential access.

## Candidates

| Repository | Type | License Signal | Useful Assets | Safety Decision | Notes |
| --- | --- | --- | --- | --- | --- |
${rows.map((row) => `| ${row.map(escapeCell).join(' | ')} |`).join('\n')}

## Patterns Worth Adapting

- Evidence before claims: always run fresh proof before completion claims.
- Skill creator/migrator: classify rule vs workflow vs resource vs MCP before adding assets.
- Selective catalogs: use catalogs to discover one skill, not bulk install hundreds.
- QA routing: split manual test design, automation generation, locator healing, and flaky-test analysis.
- Programmatic agents: evaluate official \`google-antigravity\` SDK separately for future multi-agent orchestration.

## Blocked Defaults

- Bulk \`install --all\` for large skill packs.
- Running external update scripts from \`.agent/.shared\` or installer scripts without review.
- Copying helper scripts that require credentials or write to third-party systems.
- Adopting \`.antigravity\` directory layouts until verified against the current Antigravity version on this host.
`;
}

function checkCatalog() {
  const text = fs.readFileSync(CATALOG_PATH, 'utf8');
  const missing = CANDIDATES.filter((repo) => !text.includes(repo));
  if (missing.length) {
    throw new Error(`catalog missing candidate(s): ${missing.join(', ')}`);
  }
  if (!text.includes('not an install allowlist')) {
    throw new Error('catalog missing install allowlist safety wording');
  }
  if (!fs.existsSync(CATALOG_JSON_PATH)) {
    throw new Error(`catalog JSON missing: ${CATALOG_JSON_PATH}`);
  }
  const catalog = JSON.parse(fs.readFileSync(CATALOG_JSON_PATH, 'utf8'));
  const jsonMissing = CANDIDATES.filter((repo) => !catalog.entries?.some((entry) => entry.repository === repo));
  if (jsonMissing.length) {
    throw new Error(`catalog JSON missing candidate(s): ${jsonMissing.join(', ')}`);
  }
  const intakeMissing = catalog.entries.filter((entry) => !entry.intake?.action || !Array.isArray(entry.intake?.blockers));
  if (intakeMissing.length) {
    throw new Error(`catalog JSON missing intake guidance: ${intakeMissing.map((entry) => entry.repository).join(', ')}`);
  }
  return { ok: true, candidates: CANDIDATES.length, json: true };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.check) {
    const result = checkCatalog();
    process.stdout.write(options.json ? `${JSON.stringify(result)}\n` : `external catalog check: pass (${result.candidates} candidates)\n`);
    return;
  }

  const entries = [];
  for (const repo of CANDIDATES) {
    entries.push(await inspectRepo(repo));
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
    process.stdout.write(`external catalog refreshed: ${CATALOG_PATH} and ${CATALOG_JSON_PATH}\n`);
  } else {
    process.stdout.write(markdown);
  }
}

main().catch((error) => {
  process.stderr.write(`external catalog refresh failed: ${error.message}\n`);
  process.exitCode = 1;
});
