#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const CANONICAL_SKILLS = path.join(REPO_ROOT, 'skills');
const PLUGIN_ROOT = path.join(KIT_ROOT, 'plugin');
const EXPECTED = [
  'aedilis','aleator','architect','artifex','augur','capabilities','censor','coder','context-optimizer','documenter','error-handler','evocate-ad-opus','git-master','glossator','haruspex','indagator','ludifex','mercator','nomenclator','orator','orchestrator','pictor','planner','pontifex','praeco','praemonitor','prompt-engineer','quaestor','refactorer','researcher','reviewer','security','sicarius','skill-quartermaster','tabularius','tester','velites'
];

const REQUIRED_AGENT_PHRASES = [
  'Own only tasks explicitly routed',
  'Do not claim adjacent specialties',
  'If missing capability is required, name the needed Legionary and stop or hand back',
  'Keep scope bounded to the user\'s task, allowed files, and declared proof',
  'For implementation work, follow CLAUDE_ORDER v1 when provided',
  'Report facts, changed files, proof commands, remaining risks, and handoffs actually used'
];

const REQUIRED_PROTOCOL_FILES = [
  'scripts/external-skill-scan.mjs',
  'scripts/frontend-sweep-plan.mjs',
  'plugin/references/opus-4-8-profile.md',
  '../../skills/tester/references/frontend-sweep.md',
  '../../skills/reviewer/references/completion-verification.md',
  '../../skills/security/references/external-skill-security.md',
  '../../skills/context-optimizer/references/opus-dossier.md'
];

const REQUIRED_PROTOCOL_LINKS = [
  { file: '../../skills/tester/SKILL.md', phrase: 'references/frontend-sweep.md' },
  { file: '../../skills/reviewer/SKILL.md', phrase: 'references/completion-verification.md' },
  { file: '../../skills/security/SKILL.md', phrase: 'external-skill-scan.mjs' },
  { file: '../../skills/skill-quartermaster/SKILL.md', phrase: 'external-skill-scan.mjs' },
  { file: '../../skills/context-optimizer/SKILL.md', phrase: 'references/opus-dossier.md' },
  { file: 'plugin/SKILL.md', phrase: 'references/opus-4-8-profile.md' }
];

const ROUTING_EVALS = [
  { id: 'orchestrate-complex-task', owner: 'orchestrator', handoffs: ['planner','researcher','praemonitor'] },
  { id: 'durable-plan', owner: 'planner', handoffs: ['orchestrator','tester'] },
  { id: 'local-or-web-research', owner: 'researcher', handoffs: ['skill-quartermaster','documenter'] },
  { id: 'premortem', owner: 'praemonitor', handoffs: ['planner','censor'] },
  { id: 'external-skill-discovery', owner: 'skill-quartermaster', handoffs: ['security','researcher'] },
  { id: 'production-code', owner: 'coder', handoffs: ['tester','reviewer','security'] },
  { id: 'runtime-debug', owner: 'error-handler', handoffs: ['coder','tester'] },
  { id: 'test-suite', owner: 'tester', handoffs: ['coder','reviewer'] },
  { id: 'code-review', owner: 'reviewer', handoffs: ['security','tester'] },
  { id: 'security-gate', owner: 'security', handoffs: ['haruspex','sicarius','reviewer'] },
  { id: 'devops-db-service-health', owner: 'pontifex', handoffs: ['security','tester'] },
  { id: 'mini-app-game-product', owner: 'ludifex', handoffs: ['praeco','aleator','pictor'] },
  { id: 'ux-architecture', owner: 'aedilis', handoffs: ['pictor','nomenclator','glossator'] },
  { id: 'product-language', owner: 'nomenclator', handoffs: ['mercator','glossator','aedilis'] },
  { id: 'interface-localization', owner: 'glossator', handoffs: ['nomenclator','pictor'] },
  { id: 'telegram-platform', owner: 'praeco', handoffs: ['ludifex','pictor','security'] },
  { id: 'gamification', owner: 'aleator', handoffs: ['ludifex','mercator','censor'] },
  { id: 'growth-positioning', owner: 'mercator', handoffs: ['nomenclator','orator','indagator'] },
  { id: 'frontend-implementation', owner: 'pictor', handoffs: ['aedilis','nomenclator','tester','reviewer'] },
  { id: 'social-content', owner: 'orator', handoffs: ['mercator','nomenclator'] },
  { id: 'seo-search', owner: 'indagator', handoffs: ['mercator','documenter','pictor'] },
  { id: 'system-architecture', owner: 'architect', handoffs: ['coder','security','pontifex'] },
  { id: 'behavior-preserving-refactor', owner: 'refactorer', handoffs: ['tester','reviewer'] },
  { id: 'documentation', owner: 'documenter', handoffs: ['coder','reviewer'] },
  { id: 'prompt-specification', owner: 'prompt-engineer', handoffs: ['orchestrator','tester'] },
  { id: 'context-surface-audit', owner: 'context-optimizer', handoffs: ['tester','documenter'] },
  { id: 'agent-skill-packaging', owner: 'artifex', handoffs: ['tester','security'] },
  { id: 'git-operations', owner: 'git-master', handoffs: ['tester','reviewer'] },
  { id: 'adversarial-war-room', owner: 'censor', handoffs: ['praemonitor','reviewer','security'] },
  { id: 'active-recon', owner: 'velites', handoffs: ['security','haruspex'] },
  { id: 'static-vulnerability-analysis', owner: 'haruspex', handoffs: ['security','sicarius'] },
  { id: 'exploit-verification', owner: 'sicarius', handoffs: ['security','velites'] },
  { id: 'pool-intelligence', owner: 'augur', handoffs: ['quaestor','tabularius'] },
  { id: 'onchain-intelligence', owner: 'quaestor', handoffs: ['augur','security'] },
  { id: 'external-model-delegation', owner: 'evocate-ad-opus', handoffs: ['orchestrator','reviewer'] },
  { id: 'report-publishing', owner: 'tabularius', handoffs: ['documenter','indagator'] },
  { id: 'capability-reference', owner: 'capabilities', handoffs: ['orchestrator'] }
];

const STOPWORDS = new Set([
  'agent','analysis','and','architecture','audit','code','component','data','development','external','implementation','interface','legionary','local','management','project','proof','review','risk','specialist','strategy','system','task','tasks','testing','tools','when','with'
]);

function parseArgs(argv) {
  const options = {
    claudeHome: process.env.CLAUDE_HOME || path.join(os.homedir(), '.claude'),
    repoOnly: false,
    json: false,
    pluginValidate: true,
    pluginList: true,
    overlapThreshold: 0.72
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--claude-home') options.claudeHome = path.resolve(argv[++index]);
    else if (arg === '--repo-only') options.repoOnly = true;
    else if (arg === '--json') options.json = true;
    else if (arg === '--no-plugin-validate') options.pluginValidate = false;
    else if (arg === '--no-plugin-list') options.pluginList = false;
    else if (arg === '--overlap-threshold') options.overlapThreshold = Number(argv[++index]);
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node scripts/claude-surface-audit.mjs [options]\n\nOptions:\n  --claude-home <dir>      Claude Code config root. Default: ~/.claude\n  --repo-only              Audit repository plugin surface only\n  --json                   Print full JSON report\n  --no-plugin-validate     Skip claude plugin validate\n  --no-plugin-list         Skip claude plugin list loaded-status check\n  --overlap-threshold <n>  Fail on role-description Jaccard similarity above n. Default: 0.72\n`;
}

function normalizeSlash(value) {
  return value.split(path.sep).join('/');
}

function readText(file) {
  return fs.readFileSync(file, 'utf8');
}

function readJson(file) {
  return JSON.parse(readText(file));
}

function stripQuotes(value) {
  return String(value || '').trim().replace(/^['"]|['"]$/g, '');
}

function parseFrontmatter(text) {
  const result = { tools: [] };
  if (!text.startsWith('---\n')) return result;
  const end = text.indexOf('\n---', 4);
  if (end === -1) return result;
  const lines = text.slice(4, end).split('\n');
  let currentKey = null;
  for (const line of lines) {
    const listItem = line.match(/^\s*-\s*(.+)$/);
    if (listItem && currentKey === 'tools') {
      result.tools.push(stripQuotes(listItem[1]));
      continue;
    }
    const pair = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!pair) continue;
    currentKey = pair[1];
    if (currentKey === 'tools') result.tools = [];
    else result[currentKey] = stripQuotes(pair[2]);
  }
  return result;
}

function listSkillSlugs(directory) {
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(directory, entry.name, 'SKILL.md')))
    .map((entry) => entry.name)
    .sort();
}

function listAgentSlugs(directory) {
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory)
    .filter((name) => name.endsWith('.md'))
    .map((name) => name.replace(/\.md$/, ''))
    .sort();
}

function sortedUnique(values) {
  return [...new Set(values)].sort();
}

function sameList(left, right) {
  const a = sortedUnique(left);
  const b = sortedUnique(right);
  return a.length === b.length && a.every((item, index) => item === b[index]);
}

function walkFiles(root, directory = root) {
  if (!fs.existsSync(root)) return [];
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walkFiles(root, full));
    else files.push(normalizeSlash(path.relative(root, full)));
  }
  return files.sort();
}

function treeHashes(root) {
  const hashes = new Map();
  for (const file of walkFiles(root)) {
    const digest = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex');
    hashes.set(file, digest);
  }
  return hashes;
}

function compareTrees(leftRoot, rightRoot) {
  const left = treeHashes(leftRoot);
  const right = treeHashes(rightRoot);
  const files = sortedUnique([...left.keys(), ...right.keys()]);
  const mismatches = [];
  for (const file of files) {
    if (!left.has(file)) mismatches.push({ file, reason: 'extra-installed' });
    else if (!right.has(file)) mismatches.push({ file, reason: 'missing-installed' });
    else if (left.get(file) !== right.get(file)) mismatches.push({ file, reason: 'hash-mismatch' });
  }
  return mismatches;
}

function tokens(text) {
  return new Set(String(text).toLowerCase().match(/[a-z0-9-]{4,}/g)?.filter((word) => !STOPWORDS.has(word)) || []);
}

function canonicalBrief(description) {
  const text = String(description || '').trim();
  return text.split(/\.\s+Use when\b/)[0].trim();
}

function jaccard(left, right) {
  const a = tokens(left);
  const b = tokens(right);
  const union = new Set([...a, ...b]);
  if (!union.size) return 0;
  let intersection = 0;
  for (const item of a) if (b.has(item)) intersection += 1;
  return intersection / union.size;
}

function run(command, args, options = {}) {
  return spawnSync(command, args, { cwd: KIT_ROOT, encoding: 'utf8', ...options });
}

function addFailure(report, message, details = {}) {
  report.failures.push({ message, ...details });
}

function addWarning(report, message, details = {}) {
  report.warnings.push({ message, ...details });
}

function auditRepo(options, report) {
  const pluginManifest = path.join(PLUGIN_ROOT, '.claude-plugin', 'plugin.json');
  const rootSkill = path.join(PLUGIN_ROOT, 'SKILL.md');
  const claudeOrder = path.join(PLUGIN_ROOT, 'skills', 'claude-order', 'SKILL.md');
  const outputStyle = path.join(PLUGIN_ROOT, 'output-styles', 'centurion-legion.md');
  const agentsDir = path.join(PLUGIN_ROOT, 'agents');

  for (const file of [pluginManifest, rootSkill, claudeOrder, outputStyle]) {
    if (!fs.existsSync(file)) addFailure(report, 'required plugin file missing', { file: normalizeSlash(path.relative(KIT_ROOT, file)) });
  }

  for (const relative of REQUIRED_PROTOCOL_FILES) {
    const file = path.resolve(KIT_ROOT, relative);
    if (!fs.existsSync(file)) addFailure(report, 'required Opus 4.8 protocol file missing', { file: normalizeSlash(path.relative(REPO_ROOT, file)) });
  }

  for (const item of REQUIRED_PROTOCOL_LINKS) {
    const file = path.resolve(KIT_ROOT, item.file);
    if (!fs.existsSync(file)) addFailure(report, 'required protocol link file missing', { file: normalizeSlash(path.relative(REPO_ROOT, file)) });
    else if (!readText(file).includes(item.phrase)) addFailure(report, 'required protocol link missing', { file: normalizeSlash(path.relative(REPO_ROOT, file)), phrase: item.phrase });
  }

  if (fs.existsSync(pluginManifest)) {
    const manifest = readJson(pluginManifest);
    report.repo.pluginName = manifest.name;
    report.repo.pluginVersion = manifest.version;
    if (manifest.name !== 'centurion-legion') addFailure(report, 'plugin name mismatch', { actual: manifest.name });
    if (!manifest.skills?.includes('./')) addFailure(report, 'plugin must expose root skill', { file: normalizeSlash(path.relative(KIT_ROOT, pluginManifest)) });
  }

  const canonical = listSkillSlugs(CANONICAL_SKILLS);
  const agents = listAgentSlugs(agentsDir);
  report.repo.canonicalSkillCount = canonical.length;
  report.repo.agentCount = agents.length;
  report.repo.routingEvalCount = ROUTING_EVALS.length;

  if (!sameList(canonical, EXPECTED)) addFailure(report, 'canonical skill surface drift', { expected: EXPECTED, actual: canonical });
  if (!sameList(agents, canonical)) addFailure(report, 'plugin agents must be one-to-one with canonical skills', { canonical, agents });

  const names = [];
  const ownerAliases = [];
  const descriptions = new Map();

  for (const slug of canonical) {
    const canonicalFile = path.join(CANONICAL_SKILLS, slug, 'SKILL.md');
    const agentFile = path.join(agentsDir, `${slug}.md`);
    if (!fs.existsSync(agentFile)) {
      addFailure(report, 'agent missing for canonical skill', { slug });
      continue;
    }

    const canonicalFrontmatter = parseFrontmatter(readText(canonicalFile));
    const agentText = readText(agentFile);
    const agentFrontmatter = parseFrontmatter(agentText);
    names.push(agentFrontmatter.name);
    descriptions.set(slug, agentFrontmatter.description || '');

    if (agentFrontmatter.name !== slug) addFailure(report, 'agent frontmatter name must match slug', { slug, actual: agentFrontmatter.name });
    const brief = canonicalBrief(canonicalFrontmatter.description);
    if (!brief || !agentFrontmatter.description?.includes(brief)) {
      addFailure(report, 'agent description must include canonical role brief', { slug, brief });
    }
    if (!agentText.includes(`Canonical skill source: \`skills/${slug}/SKILL.md\``)) {
      addFailure(report, 'agent missing canonical source link', { slug });
    }
    for (const phrase of REQUIRED_AGENT_PHRASES) {
      if (!agentText.includes(phrase)) addFailure(report, 'agent missing operating-contract phrase', { slug, phrase });
    }
    const owner = agentText.match(/Own only tasks explicitly routed to ([A-Z-]+)/)?.[1];
    if (!owner) addFailure(report, 'agent missing explicit owner alias', { slug });
    else ownerAliases.push(owner);
  }

  const duplicateNames = names.filter((name, index) => names.indexOf(name) !== index);
  const duplicateAliases = ownerAliases.filter((name, index) => ownerAliases.indexOf(name) !== index);
  if (duplicateNames.length) addFailure(report, 'duplicate agent names found', { duplicateNames: sortedUnique(duplicateNames) });
  if (duplicateAliases.length) addFailure(report, 'duplicate owner aliases found', { duplicateAliases: sortedUnique(duplicateAliases) });

  const overlapHits = [];
  for (let leftIndex = 0; leftIndex < agents.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < agents.length; rightIndex += 1) {
      const left = agents[leftIndex];
      const right = agents[rightIndex];
      const score = jaccard(descriptions.get(left), descriptions.get(right));
      if (score > options.overlapThreshold) overlapHits.push({ left, right, score: Number(score.toFixed(3)) });
    }
  }
  report.repo.highOverlapPairs = overlapHits;
  for (const hit of overlapHits) addFailure(report, 'agent descriptions are too similar; possible role overlap', hit);

  for (const item of ROUTING_EVALS) {
    if (!canonical.includes(item.owner)) addFailure(report, 'routing eval owner missing from canonical skills', item);
    if (item.handoffs.includes(item.owner)) addFailure(report, 'routing eval handoff includes primary owner', item);
    for (const handoff of item.handoffs) {
      if (!canonical.includes(handoff)) addFailure(report, 'routing eval handoff missing from canonical skills', { id: item.id, owner: item.owner, handoff });
    }
  }
  const evalOwners = sortedUnique(ROUTING_EVALS.map((item) => item.owner));
  const missingEvalOwners = canonical.filter((slug) => !evalOwners.includes(slug));
  if (missingEvalOwners.length) addFailure(report, 'canonical skills missing from routing eval matrix', { missingEvalOwners });

  if (fs.existsSync(rootSkill)) {
    const text = readText(rootSkill);
    for (const phrase of ['One task has one primary Legionary owner', 'Other Legionaries are conditional handoffs or gates, not co-owners', 'If the owner lacks a needed capability, call or name the exact missing Legionary']) {
      if (!text.includes(phrase)) addFailure(report, 'root skill missing one-owner routing rule', { phrase });
    }
  }

  if (options.pluginValidate) {
    const validation = run('claude', ['plugin', 'validate', PLUGIN_ROOT, '--strict']);
    report.repo.pluginValidation = { ok: validation.status === 0, status: validation.status, output: `${validation.stdout || ''}${validation.stderr || ''}`.trim() };
    if (validation.status !== 0) addFailure(report, 'repo plugin validation failed', report.repo.pluginValidation);
  }
}

function auditInstalled(options, report) {
  const skillsRoot = path.join(options.claudeHome, 'skills');
  const pluginTarget = path.join(skillsRoot, 'centurion-legion');
  report.installed.claudeHome = options.claudeHome;
  report.installed.pluginTarget = pluginTarget;

  if (!fs.existsSync(skillsRoot)) {
    addFailure(report, 'Claude skills directory missing', { skillsRoot });
    return;
  }
  if (!fs.existsSync(pluginTarget)) {
    addFailure(report, 'installed centurion-legion plugin missing', { pluginTarget });
    return;
  }

  const installedSlugs = listSkillSlugs(skillsRoot).filter((slug) => slug !== 'centurion-legion');
  const extraLegionSlugs = installedSlugs.filter((slug) => !EXPECTED.includes(slug));
  const missingInstalled = EXPECTED.filter((slug) => !installedSlugs.includes(slug));
  report.installed.standaloneSkillCount = installedSlugs.length;
  report.installed.extraSkillDirs = extraLegionSlugs;
  if (missingInstalled.length) addFailure(report, 'installed standalone canonical skills missing', { missingInstalled });
  if (extraLegionSlugs.length) addWarning(report, 'extra installed skill dirs are present outside canonical Legion surface', { extraLegionSlugs });

  const pluginMismatches = compareTrees(PLUGIN_ROOT, pluginTarget);
  report.installed.pluginTreeMismatches = pluginMismatches;
  if (pluginMismatches.length) addFailure(report, 'installed plugin differs from repository plugin', { mismatches: pluginMismatches.slice(0, 20), total: pluginMismatches.length });

  const skillDrift = [];
  for (const slug of EXPECTED) {
    const source = path.join(CANONICAL_SKILLS, slug);
    const target = path.join(skillsRoot, slug);
    if (!fs.existsSync(target)) continue;
    const mismatches = compareTrees(source, target);
    if (mismatches.length) skillDrift.push({ slug, total: mismatches.length, sample: mismatches.slice(0, 10) });
  }
  report.installed.skillTreeDrift = skillDrift;
  if (skillDrift.length) addFailure(report, 'installed standalone skills differ from repository canonical skills', { skillDrift });

  if (options.pluginValidate) {
    const validation = run('claude', ['plugin', 'validate', pluginTarget, '--strict']);
    report.installed.pluginValidation = { ok: validation.status === 0, status: validation.status, output: `${validation.stdout || ''}${validation.stderr || ''}`.trim() };
    if (validation.status !== 0) addFailure(report, 'installed plugin validation failed', report.installed.pluginValidation);
  }

  if (options.pluginList) {
    const listed = run('claude', ['plugin', 'list']);
    const output = `${listed.stdout || ''}${listed.stderr || ''}`;
    const loaded = listed.status === 0 && output.includes('centurion-legion@skills-dir') && output.includes('Status: ✔ loaded');
    report.installed.pluginList = { ok: loaded, status: listed.status, output: output.trim() };
    if (!loaded) addFailure(report, 'centurion-legion plugin is not reported as loaded', { status: listed.status });
  }
}

function printTextReport(report) {
  const status = report.ok ? 'pass' : 'fail';
  process.stdout.write(`claude-surface-audit: ${status}\n`);
  process.stdout.write(`repo canonical skills: ${report.repo.canonicalSkillCount}\n`);
  process.stdout.write(`repo plugin agents: ${report.repo.agentCount}\n`);
  process.stdout.write(`routing evals: ${report.repo.routingEvalCount}\n`);
  process.stdout.write(`high-overlap pairs: ${report.repo.highOverlapPairs?.length || 0}\n`);
  if (report.installed.claudeHome) {
    process.stdout.write(`installed claude home: ${report.installed.claudeHome}\n`);
    process.stdout.write(`installed standalone skills: ${report.installed.standaloneSkillCount}\n`);
    process.stdout.write(`installed plugin drift files: ${report.installed.pluginTreeMismatches?.length || 0}\n`);
    process.stdout.write(`installed skill drift dirs: ${report.installed.skillTreeDrift?.length || 0}\n`);
  }
  if (report.warnings.length) {
    process.stdout.write(`warnings:\n`);
    for (const warning of report.warnings) process.stdout.write(`- ${warning.message}\n`);
  }
  if (report.failures.length) {
    process.stdout.write(`failures:\n`);
    for (const failure of report.failures) process.stdout.write(`- ${failure.message}\n`);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  const report = {
    ok: true,
    failures: [],
    warnings: [],
    repo: {},
    installed: {},
    routingEvals: ROUTING_EVALS
  };

  auditRepo(options, report);
  if (!options.repoOnly) auditInstalled(options, report);
  report.ok = report.failures.length === 0;

  if (options.json) process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  else printTextReport(report);
  if (!report.ok) process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
