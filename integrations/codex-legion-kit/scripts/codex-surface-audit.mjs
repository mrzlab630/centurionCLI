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
const EXPECTED = [
  'aedilis','aleator','architect','artifex','augur','capabilities','censor','coder','context-optimizer','documenter','error-handler','evocate-ad-opus','git-master','glossator','haruspex','indagator','ludifex','mercator','nomenclator','orator','orchestrator','pictor','planner','pontifex','praeco','praemonitor','prompt-engineer','quaestor','refactorer','researcher','reviewer','security','sicarius','skill-quartermaster','tabularius','tester','velites'
];

const IGNORED_GENERATED_DIRS = new Set([
  '.git',
  '.next',
  '.venv',
  'build',
  'coverage',
  'dist',
  'node_modules',
  'reports',
  'vendor'
]);

const REQUIRED_CONFIG = [
  { key: 'model', value: 'gpt-5.5', severity: 'failure' },
  { key: 'model_reasoning_effort', value: 'xhigh', severity: 'warning' }
];

const REQUIRED_FEATURES = [
  { key: 'memories', value: true, severity: 'warning' }
];

const REQUIRED_POINTERS = [
  { file: 'tester/SKILL.md', phrase: 'references/frontend-sweep.md' },
  { file: 'reviewer/SKILL.md', phrase: 'references/completion-verification.md' },
  { file: 'security/SKILL.md', phrase: 'external-skill-scan.mjs' },
  { file: 'skill-quartermaster/SKILL.md', phrase: 'external-skill-scan.mjs' },
  { file: 'context-optimizer/SKILL.md', phrase: 'references/opus-dossier.md' }
];

const SENSITIVE_KEY_RE = /(?:TOKEN|SECRET|KEY|PASSWORD|PASS|PRIVATE|CREDENTIAL)/i;
const URL_REMOTE_MCP_RE = /^https?:\/\//i;

function parseArgs(argv) {
  const options = {
    codexHome: process.env.CODEX_HOME || path.join(os.homedir(), '.codex'),
    agentsHome: process.env.AGENTS_HOME || path.join(os.homedir(), '.agents'),
    repoOnly: false,
    json: false,
    strictSecrets: false,
    runCodexFeatures: true
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--codex-home') options.codexHome = path.resolve(argv[++index]);
    else if (arg === '--agents-home') options.agentsHome = path.resolve(argv[++index]);
    else if (arg === '--repo-only') options.repoOnly = true;
    else if (arg === '--json') options.json = true;
    else if (arg === '--strict-secrets') options.strictSecrets = true;
    else if (arg === '--no-codex-features') options.runCodexFeatures = false;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node scripts/codex-surface-audit.mjs [options]\n\nOptions:\n  --codex-home <dir>      Codex config root. Default: ~/.codex\n  --agents-home <dir>     Agent skills root parent. Default: ~/.agents\n  --repo-only             Audit repository files only\n  --json                  Print full JSON report\n  --strict-secrets        Treat inline secret-like config values as failures\n  --no-codex-features     Skip codex features list check\n`;
}

function normalizeSlash(value) {
  return value.split(path.sep).join('/');
}

function readText(file) {
  return fs.readFileSync(file, 'utf8');
}

function listSkillSlugs(directory) {
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(directory, entry.name, 'SKILL.md')))
    .map((entry) => entry.name)
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
    if (entry.isDirectory()) {
      if (IGNORED_GENERATED_DIRS.has(entry.name)) continue;
      files.push(...walkFiles(root, full));
    }
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
    if (!left.has(file)) mismatches.push({ file, reason: 'extra-active' });
    else if (!right.has(file)) mismatches.push({ file, reason: 'missing-active' });
    else if (left.get(file) !== right.get(file)) mismatches.push({ file, reason: 'hash-mismatch' });
  }
  return mismatches;
}

function parseTomlLite(text) {
  const root = {};
  let current = root;
  for (const rawLine of text.split('\n')) {
    const line = rawLine.replace(/#.*/, '').trim();
    if (!line) continue;
    const section = line.match(/^\[([^\]]+)\]$/);
    if (section) {
      current = root;
      for (const part of section[1].split('.')) {
        const key = part.replace(/^['"]|['"]$/g, '');
        current[key] ||= {};
        current = current[key];
      }
      continue;
    }
    const pair = line.match(/^([A-Za-z0-9_.-]+)\s*=\s*(.+)$/);
    if (!pair) continue;
    current[pair[1]] = parseTomlValue(pair[2]);
  }
  return root;
}

function parseTomlValue(value) {
  const trimmed = value.trim();
  if (trimmed === 'true') return true;
  if (trimmed === 'false') return false;
  if (/^['"].*['"]$/.test(trimmed)) return trimmed.slice(1, -1);
  if (/^\[.*\]$/.test(trimmed)) {
    return trimmed.slice(1, -1).split(',').map((item) => parseTomlValue(item)).filter((item) => item !== '');
  }
  if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) return Number(trimmed);
  return trimmed;
}

function getPath(object, dotted) {
  return dotted.split('.').reduce((value, key) => value?.[key], object);
}

function run(command, args, options = {}) {
  return spawnSync(command, args, { cwd: REPO_ROOT, encoding: 'utf8', ...options });
}

function addFailure(report, message, details = {}) {
  report.failures.push({ message, ...details });
}

function addWarning(report, message, details = {}) {
  report.warnings.push({ message, ...details });
}

function auditRepo(report) {
  const canonical = listSkillSlugs(CANONICAL_SKILLS);
  report.repo.canonicalSkillCount = canonical.length;
  report.repo.expectedSkillCount = EXPECTED.length;
  if (!sameList(canonical, EXPECTED)) addFailure(report, 'canonical skill surface drift', { expected: EXPECTED, actual: canonical });

  const missingPointers = [];
  for (const item of REQUIRED_POINTERS) {
    const file = path.join(CANONICAL_SKILLS, item.file);
    if (!fs.existsSync(file)) missingPointers.push({ file: normalizeSlash(path.relative(REPO_ROOT, file)), phrase: item.phrase, reason: 'missing-file' });
    else if (!readText(file).includes(item.phrase)) missingPointers.push({ file: normalizeSlash(path.relative(REPO_ROOT, file)), phrase: item.phrase, reason: 'missing-phrase' });
  }
  report.repo.missingProtocolPointers = missingPointers;
  if (missingPointers.length) addFailure(report, 'repo skills missing Codex workflow guard pointers', { missingPointers });
}

function auditActiveSkills(options, report) {
  const activeRoot = path.join(options.agentsHome, 'skills');
  report.activeSkills.root = activeRoot;
  if (!fs.existsSync(activeRoot)) {
    addFailure(report, 'active ~/.agents skills root missing', { activeRoot });
    return;
  }
  const active = listSkillSlugs(activeRoot);
  report.activeSkills.count = active.length;
  report.activeSkills.extra = active.filter((slug) => !EXPECTED.includes(slug));
  report.activeSkills.missing = EXPECTED.filter((slug) => !active.includes(slug));
  if (report.activeSkills.missing.length) addFailure(report, 'active Legion skills missing from ~/.agents', { missing: report.activeSkills.missing });
  if (report.activeSkills.extra.length) addWarning(report, 'extra active skills exist outside canonical Legion surface', { extra: report.activeSkills.extra });

  const drift = [];
  for (const slug of EXPECTED) {
    const source = path.join(CANONICAL_SKILLS, slug);
    const target = path.join(activeRoot, slug);
    if (!fs.existsSync(target)) continue;
    const mismatches = compareTrees(source, target);
    if (mismatches.length) drift.push({ slug, total: mismatches.length, sample: mismatches.slice(0, 10) });
  }
  report.activeSkills.drift = drift;
  if (drift.length) addFailure(report, 'active ~/.agents skills differ from repository canonical skills', { drift });
}

function auditCodexConfig(options, report) {
  const configFile = path.join(options.codexHome, 'config.toml');
  report.codex.codexHome = options.codexHome;
  report.codex.configFile = configFile;
  if (!fs.existsSync(configFile)) {
    addFailure(report, 'Codex config.toml missing', { configFile });
    return;
  }
  const text = readText(configFile);
  const config = parseTomlLite(text);
  report.codex.model = config.model || null;
  report.codex.modelProvider = config.model_provider || null;
  report.codex.modelReasoningEffort = config.model_reasoning_effort || null;
  report.codex.features = config.features || {};
  report.codex.hasShellEnvironmentPolicy = Boolean(config.shell_environment_policy);

  for (const rule of REQUIRED_CONFIG) {
    const actual = getPath(config, rule.key);
    if (actual !== rule.value) {
      const details = { key: rule.key, expected: rule.value, actual };
      if (rule.severity === 'failure') addFailure(report, 'Codex config does not match required model baseline', details);
      else addWarning(report, 'Codex config differs from recommended baseline', details);
    }
  }
  for (const rule of REQUIRED_FEATURES) {
    const actual = getPath(config, `features.${rule.key}`);
    if (actual !== rule.value) {
      const details = { key: `features.${rule.key}`, expected: rule.value, actual };
      if (rule.severity === 'failure') addFailure(report, 'Codex feature baseline missing', details);
      else addWarning(report, 'Codex feature baseline missing', details);
    }
  }

  const inlineSecrets = [];
  function collectSecrets(object, prefix = '') {
    if (!object || typeof object !== 'object') return;
    for (const [key, value] of Object.entries(object)) {
      const full = prefix ? `${prefix}.${key}` : key;
      if (value && typeof value === 'object' && !Array.isArray(value)) collectSecrets(value, full);
      else if (SENSITIVE_KEY_RE.test(key) && typeof value === 'string' && value.length > 8) inlineSecrets.push(full);
    }
  }
  collectSecrets(config);
  report.codex.inlineSecretLikeKeys = inlineSecrets;
  if (inlineSecrets.length) {
    const details = { keys: inlineSecrets };
    if (options.strictSecrets) addFailure(report, 'inline secret-like values in Codex config', details);
    else addWarning(report, 'inline secret-like values in Codex config; prefer environment references before sharing', details);
  }

  const mcpServers = config.mcp_servers || {};
  const broadMcp = [];
  for (const [name, server] of Object.entries(mcpServers)) {
    if (server?.command === 'npx') broadMcp.push({ name, reason: 'npx command MCP' });
    if (typeof server?.url === 'string' && URL_REMOTE_MCP_RE.test(server.url)) broadMcp.push({ name, reason: 'remote MCP URL' });
  }
  report.codex.mcpServers = Object.keys(mcpServers).sort();
  report.codex.broadMcp = broadMcp;
  if (broadMcp.length) addWarning(report, 'MCP servers require task-scoped use and GUARDIAN review before broad delegation', { broadMcp });

  if (options.runCodexFeatures) {
    const features = run('codex', ['features', 'list']);
    const output = `${features.stdout || ''}${features.stderr || ''}`;
    report.codex.featuresCommand = { ok: features.status === 0, status: features.status };
    for (const name of ['multi_agent', 'multi_agent_v2', 'hooks', 'goals', 'memories']) {
      const line = output.split('\n').find((item) => item.trim().startsWith(name));
      if (line) report.codex.featuresCommand[name] = line.trim();
    }
    if (features.status !== 0) addWarning(report, 'codex features list failed', { status: features.status });
  }
}

function auditCodexAux(options, report) {
  const agentsDir = path.join(options.codexHome, 'agents');
  const hooksFile = path.join(options.codexHome, 'hooks.json');
  const pluginMarketplace = path.join(options.agentsHome, 'plugins', 'marketplace.json');

  report.codex.customAgents = fs.existsSync(agentsDir)
    ? fs.readdirSync(agentsDir).filter((name) => name.endsWith('.toml')).sort()
    : [];
  report.codex.hooksJson = fs.existsSync(hooksFile);
  report.codex.personalMarketplace = fs.existsSync(pluginMarketplace) ? pluginMarketplace : null;

  if (report.codex.customAgents.length > 5) addWarning(report, 'many custom Codex agents can compete with Legion routing', { count: report.codex.customAgents.length });
  if (report.codex.hooksJson) addWarning(report, 'user-level Codex hooks are present; verify trust before delegated runs', { hooksFile });
}

function printText(report) {
  process.stdout.write(`codex-surface-audit: ${report.ok ? 'pass' : 'fail'}\n`);
  process.stdout.write(`repo canonical skills: ${report.repo.canonicalSkillCount}\n`);
  if (report.activeSkills.root) {
    process.stdout.write(`active skills root: ${report.activeSkills.root}\n`);
    process.stdout.write(`active skills: ${report.activeSkills.count}\n`);
    process.stdout.write(`active skill drift dirs: ${report.activeSkills.drift?.length || 0}\n`);
  }
  if (report.codex.configFile) {
    process.stdout.write(`codex config: ${report.codex.configFile}\n`);
    process.stdout.write(`codex model: ${report.codex.model || '<unset>'}\n`);
    process.stdout.write(`codex reasoning: ${report.codex.modelReasoningEffort || '<unset>'}\n`);
    process.stdout.write(`codex custom agents: ${report.codex.customAgents?.length || 0}\n`);
    process.stdout.write(`codex hooks.json: ${report.codex.hooksJson ? 'present' : 'absent'}\n`);
  }
  if (report.warnings.length) {
    process.stdout.write('warnings:\n');
    for (const warning of report.warnings) process.stdout.write(`- ${warning.message}\n`);
  }
  if (report.failures.length) {
    process.stdout.write('failures:\n');
    for (const failure of report.failures) process.stdout.write(`- ${failure.message}\n`);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  const report = { ok: true, failures: [], warnings: [], repo: {}, activeSkills: {}, codex: {} };
  auditRepo(report);
  if (!options.repoOnly) {
    auditActiveSkills(options, report);
    auditCodexConfig(options, report);
    auditCodexAux(options, report);
  }
  report.ok = report.failures.length === 0;
  if (options.json) process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  else printText(report);
  if (!report.ok) process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
