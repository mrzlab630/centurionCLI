#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const SKILL_SIZE_LIMIT = 100_000;
const PACKAGE_MANIFEST = path.join(KIT_ROOT, 'package.json');
const STALE_BASELINE_CLAIM = /gpt-5\.5|codex-cli 0\.142\.5/i;
const CURRENT_BASELINE_SURFACES = [
  ['Hermes documentation', path.resolve(KIT_ROOT, '..', '..', 'docs', 'HERMES_LEGION_KIT.md'), ['gpt-5.6-sol']],
  ['local tooling documentation', path.resolve(KIT_ROOT, '..', '..', 'docs', 'LOCAL_TOOLING_BASELINE.md'), ['gpt-5.6-sol', 'codex-cli 0.146.0']],
  ['Codex documentation', path.resolve(KIT_ROOT, '..', '..', 'docs', 'CODEX_LEGION_KIT.md'), ['gpt-5.6-sol', 'codex-cli 0.146.0']],
  ['sanitized tooling snapshot', path.resolve(KIT_ROOT, '..', '..', 'docs', 'settings-snapshots', 'local-tooling-baseline-2026-07-09.json'), ['gpt-5.6-sol', 'codex-cli 0.146.0']],
  ['package README', path.join(KIT_ROOT, 'README.md'), ['gpt-5.6-sol']]
];
const STALE_ROUTING_CLAIM = new RegExp([
  'claude[-_ ]?opus[-_ .]?4[-_. ]?8',
  'opus[-_. ]?4[-_. ]?8',
  'claude[-_ ]?sonnet[-_ .]?4[-_. ]?6',
  'sonnet[-_. ]?4[-_. ]?6',
  'Sol owns routine implementation'
].join('|'), 'i');
const LEGACY_MODEL_MUTATIONS = [
  ['Claude', 'Opus', '4.8'].join(' '),
  ['claude', 'opus', '4', '8'].join('-'),
  ['claude', 'opus', '4', '8'].join('_'),
  ['opus', '4.8'].join('-'),
  ['Claude', 'Sonnet', '4.6'].join(' '),
  ['claude', 'sonnet', '4', '6'].join('-'),
  ['claude', 'sonnet', '4', '6'].join('_'),
  ['sonnet', '4.6'].join('-')
];
const STALE_ROUTING_SURFACES = [
  ['SOUL Claude role note', path.join(KIT_ROOT, 'overrides', 'SOUL_CLAUDE_ROLE_RULE.md')],
  ['adaptive policy', path.join(KIT_ROOT, 'overrides', 'ADAPTIVE_MODEL_ROUTING_POLICY.md')],
  ['package README', path.join(KIT_ROOT, 'README.md')],
  ['Hermes Legion Kit documentation', path.resolve(KIT_ROOT, '..', '..', 'docs', 'HERMES_LEGION_KIT.md')],
  ['Aquila orchestration skill', path.join(KIT_ROOT, 'skills', 'autonomous-ai-agents', 'aquila-team-orchestration', 'SKILL.md')]
];
const REQUIRED_SKILLS = [
  'aquila-team-orchestration',
  'agent-contract-runner',
  'aquila-harness-audit',
  'aquila-executor-eval',
  'aquila-self-debug'
];
const REQUIRED_BUNDLES = {
  'aquila-delivery.yaml': [
    'aquila-team-orchestration',
    'delegated-cli-executor-orchestration',
    'delegating-code-to-executors'
  ],
  'aquila-harness-audit.yaml': [
    'aquila-harness-audit',
    'aquila-self-debug',
    'hermes-agent-skill-authoring'
  ],
  'aquila-executor-eval.yaml': [
    'aquila-executor-eval',
    'aquila-team-orchestration',
    'delegated-cli-executor-orchestration',
    'delegating-code-to-executors'
  ]
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function readText(file) {
  return fs.readFileSync(file, 'utf8');
}

function hasStaleRoutingClaim(text) {
  return STALE_ROUTING_CLAIM.test(text);
}

function assertSkill(skill) {
  const file = path.join(KIT_ROOT, 'skills', 'autonomous-ai-agents', skill, 'SKILL.md');
  assert(fs.existsSync(file), `missing skill: ${skill}`);
  const text = readText(file);
  assert(text.startsWith('---\n'), `${skill} missing frontmatter`);
  assert(new RegExp(`^name:\\s*${skill}$`, 'm').test(text), `${skill} name mismatch`);
  assert(/^description:\s+.+Use when /m.test(text), `${skill} description lacks trigger`);
  assert(!/\/home\/mrz\/tmp\/ecc-review/.test(text), `${skill} leaks ECC clone path`);
  assert(!/(?:curl|wget)[^\n]*(?:\|\s*(?:sh|bash)|sh\s*-c)/.test(text), `${skill} contains remote shell execution`);
  assert(!/base64\s+-d\s*\|\s*(?:sh|bash)/.test(text), `${skill} contains decoded shell execution`);
  if (skill === 'aquila-harness-audit') {
    assert(/runtime model evidence overrides stale profile summaries/i.test(text), `${skill} missing runtime model precedence rule`);
    assert(/enabled `npx -y` MCP/i.test(text), `${skill} missing npx MCP audit rule`);
    assert(/hermes security audit/.test(text), `${skill} missing security audit command`);
    assert(/harness-audit\.mjs/.test(text), `${skill} missing deterministic audit script reference`);
  }
  if (skill === 'aquila-team-orchestration') {
    assert(/^version:\s*1\.1\.0$/m.test(text), `${skill} version must be 1.1.0`);
    assert(/^## Adaptive Model and Effort Routing$/m.test(text), `${skill} missing adaptive model and effort routing section`);
    assert(text.includes('`none|low|medium|high|xhigh|max`'), `${skill} missing exact effort enum`);
    assert(text.includes('overrides/ADAPTIVE_MODEL_ROUTING_POLICY.md'), `${skill} missing adaptive policy manual reference`);
    assert(text.includes('AQUILA_ROUTING_JSON_V1'), `${skill} missing deterministic routing metadata`);
    assert(text.includes('review-routing-ladder-and-cost-control.md'), `${skill} missing routing policy reference`);
    assert(text.includes('V0'), `${skill} missing V0-V3 matrix`);
  }
  if (skill === 'agent-contract-runner') {
    assert(/^version:\s*0\.4\.0$/m.test(text), `${skill} version must be 0.4.0`);
    for (const marker of ['2026-08-03T11:00:42Z', 'AQUILA_ROUTING_JSON_V1', 'V0', 'V1', 'V2', 'V3', 'attempt_ledger.py', 'review_ladder.py', 'agent_result_builder.py', 'terminal']) {
      assert(text.includes(marker), `${skill} missing marker: ${marker}`);
    }
  }
}

function assertBundle(fileName, expectedSkills) {
  const file = path.join(KIT_ROOT, 'skill-bundles', fileName);
  assert(fs.existsSync(file), `missing bundle: ${fileName}`);
  const text = readText(file);
  for (const skill of expectedSkills) assert(text.includes(`- ${skill}`), `${fileName} missing ${skill}`);
  const listedSkills = [...text.matchAll(/^- ([a-z0-9-]+)$/gm)].map((match) => match[1]);
  const heavySkills = new Set(['claude-code', 'codex', 'requesting-code-review', 'test-driven-development', 'kanban-orchestrator', 'hermes-agent']);
  const eagerHeavySkills = listedSkills.filter((skill) => heavySkills.has(skill));
  assert(eagerHeavySkills.length === 0, `${fileName} eagerly loads heavy skills: ${eagerHeavySkills.join(', ')}`);
}

function runNodeCheck(relativePath) {
  const result = spawnSync(process.execPath, ['--check', path.join(KIT_ROOT, relativePath)], { encoding: 'utf8' });
  assert(result.status === 0, `node --check ${relativePath} failed: ${result.stderr || result.stdout}`);
}

function runInstallerDryRun() {
  const result = spawnSync(process.execPath, [path.join(KIT_ROOT, 'installer', 'install.mjs'), '--dry-run'], { encoding: 'utf8' });
  assert(result.status === 0, `installer dry-run failed: ${result.stderr || result.stdout}`);
  const report = JSON.parse(result.stdout);
  assert(report.dryRun === true, 'installer dry-run did not report dryRun=true');
  assert(report.changedSurfaces.includes('skills'), 'installer report missing skills surface');
  assert(report.changedSurfaces.includes('skill-bundles'), 'installer report missing skill-bundles surface');
  assert(report.untouchedSurfaces.includes('SOUL.md'), 'installer must not edit SOUL.md');
}

function runInstallerOverrideDryRun() {
  const result = spawnSync(process.execPath, [path.join(KIT_ROOT, 'installer', 'install.mjs'), '--dry-run', '--include-overrides'], { encoding: 'utf8' });
  assert(result.status === 0, `installer override dry-run failed: ${result.stderr || result.stdout}`);
  const report = JSON.parse(result.stdout);
  assert(report.dryRun === true, 'override dry-run did not report dryRun=true');
  assert(report.includeOverrides === true, 'override dry-run did not report includeOverrides=true');
  assert(report.overrideSkillFiles.includes('research/research-paper-writing/SKILL.md'), 'override dry-run missing research-paper-writing override');
  assert(report.untouchedSurfaces.includes('SOUL.md'), 'override install must not edit SOUL.md');
}

function runPackagedPythonRegressions(scriptRoot) {
  const scripts = ['regression_review_ladder.py', 'regression_agent_contract_runner.py', 'regression_agent_result_builder.py'];
  const isolatedEnvironment = {
    ...process.env,
    HOME: path.join(path.dirname(scriptRoot), 'nonexistent-home'),
    HERMES_HOME: path.join(path.dirname(scriptRoot), 'nonexistent-hermes-home'),
    PYTHONDONTWRITEBYTECODE: '1'
  };
  delete isolatedEnvironment.AQUILA_AGENT_RESULT_SCHEMA;
  for (const script of scripts) {
    const result = spawnSync('python3', [script], { cwd: scriptRoot, encoding: 'utf8', env: isolatedEnvironment });
    assert(result.status === 0, `${script} failed: ${result.stderr || result.stdout}`);
  }
}

function runIsolatedInstallSmoke() {
  const tempHome = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'hermes-legion-kit-smoke-'));
  try {
    const result = spawnSync(process.execPath, [path.join(KIT_ROOT, 'installer', 'install.mjs'), '--hermes-home', tempHome], { encoding: 'utf8' });
    assert(result.status === 0, `isolated installer failed: ${result.stderr || result.stdout}`);
    const scriptRoot = path.join(tempHome, 'skills', 'autonomous-ai-agents', 'agent-contract-runner', 'scripts');
    const requiredFiles = [
      path.join(tempHome, 'skills', 'autonomous-ai-agents', 'agent-contract-runner', 'SKILL.md'),
      path.join(tempHome, 'skills', 'autonomous-ai-agents', 'agent-contract-runner', 'references', 'agent-result.schema.json'),
      path.join(tempHome, 'skills', 'autonomous-ai-agents', 'aquila-team-orchestration', 'references', 'review-routing-ladder-and-cost-control.md'),
      ...['agent_contract_runner.py', 'regression_agent_contract_runner.py', 'agent_result_builder.py', 'regression_agent_result_builder.py', 'attempt_ledger.py', 'review_ladder.py', 'regression_review_ladder.py'].map((file) => path.join(scriptRoot, file))
    ];
    for (const file of requiredFiles) assert(fs.existsSync(file), `isolated install missing: ${file}`);
    assert(!fs.existsSync(path.join(tempHome, 'SOUL.md')), 'installer must not create SOUL.md');
    runPackagedPythonRegressions(scriptRoot);
  } finally {
    fs.rmSync(tempHome, { recursive: true, force: true });
  }
}

function assertCurrentBaselines() {
  for (const [label, file, requiredMarkers] of CURRENT_BASELINE_SURFACES) {
    assert(fs.existsSync(file), `missing current-baseline surface: ${label}`);
    const text = readText(file);
    assert(!STALE_BASELINE_CLAIM.test(text), `${label} contains stale Codex baseline`);
    for (const marker of requiredMarkers) assert(text.includes(marker), `${label} missing current baseline marker: ${marker}`);
    for (const mutation of ['gpt-5.5', 'codex-cli 0.142.5']) {
      assert(STALE_BASELINE_CLAIM.test(`${text}\n${mutation}`), `${label} stale-baseline mutation escaped guard`);
    }
  }
}

function assertOverrides() {
  const researchSkill = path.join(KIT_ROOT, 'overrides', 'skills', 'research', 'research-paper-writing', 'SKILL.md');
  const soulRule = path.join(KIT_ROOT, 'overrides', 'SOUL_RUNTIME_MODEL_RULE.md');
  const claudeRoleRule = path.join(KIT_ROOT, 'overrides', 'SOUL_CLAUDE_ROLE_RULE.md');
  const adaptivePolicy = path.join(KIT_ROOT, 'overrides', 'ADAPTIVE_MODEL_ROUTING_POLICY.md');
  assert(fs.existsSync(researchSkill), 'missing research-paper-writing override');
  assert(fs.statSync(researchSkill).size < SKILL_SIZE_LIMIT, 'research-paper-writing override exceeds skill size limit');
  assert(/references\/experiment-patterns\.md/.test(readText(researchSkill)), 'research override missing reference routing');
  assert(fs.existsSync(soulRule), 'missing SOUL runtime model rule note');
  assert(/Runtime model evidence overrides stale profile summaries/.test(readText(soulRule)), 'SOUL runtime rule note missing exact rule');
  assert(fs.existsSync(claudeRoleRule), 'missing SOUL Claude role rule note');
  const claudeRoleText = readText(claudeRoleRule);
  for (const marker of [
    'Principal reviewer and reasoning-heavy executor',
    'Codex remains the default implementation owner',
    'Claude is not allowed to self-approve',
    'Claude implementation is not limited to Codex unavailability',
    'Aquila retains final judgment'
  ]) {
    assert(claudeRoleText.includes(marker), `SOUL Claude role rule note missing marker: ${marker}`);
  }
  assert(fs.existsSync(adaptivePolicy), 'missing adaptive model routing policy note');
  const policyText = readText(adaptivePolicy);
  for (const marker of [
    'gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.6-sol',
    'none|low|medium|high|xhigh|max',
    'independently for every DAG node', 'Aquila retains final judgment',
    'No executor self-approves', 'not automatically installed',
    'Runtime/launcher evidence overrides stale static summaries',
    'Claude Opus 5',
    'Terra, not Sol, is the routine bounded implementation default',
    'can raise but never lower',
    'prose does not activate effort'
  ]) assert(policyText.includes(marker), `adaptive policy missing marker: ${marker}`);
  assert(/Codex\s+personality remains a valid CLI enum/.test(policyText), 'adaptive policy missing marker: Codex personality remains a valid CLI enum');
  for (const [label, file] of STALE_ROUTING_SURFACES) {
    assert(fs.existsSync(file), `missing stale-routing surface: ${label}`);
    const text = readText(file);
    assert(!hasStaleRoutingClaim(text), `${label} contains stale routing claim`);
    for (const mutation of LEGACY_MODEL_MUTATIONS) {
      assert(hasStaleRoutingClaim(`${text}\n${mutation}`), `${label} legacy-model mutation escaped guard`);
    }
  }
}

function assertPackageVersion() {
  const manifest = JSON.parse(readText(PACKAGE_MANIFEST));
  assert(manifest.version === '0.4.0', 'package version must be 0.4.0');
}

function main() {
  assertPackageVersion();
  assertCurrentBaselines();
  for (const skill of REQUIRED_SKILLS) assertSkill(skill);
  for (const [fileName, skills] of Object.entries(REQUIRED_BUNDLES)) assertBundle(fileName, skills);
  runNodeCheck('installer/install.mjs');
  runNodeCheck('scripts/smoke.mjs');
  runNodeCheck('scripts/harness-audit.mjs');
  assertOverrides();
  runInstallerDryRun();
  runInstallerOverrideDryRun();
  runIsolatedInstallSmoke();
  process.stdout.write(JSON.stringify({ ok: true, skills: REQUIRED_SKILLS.length, bundles: Object.keys(REQUIRED_BUNDLES).length }, null, 2) + '\n');
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
