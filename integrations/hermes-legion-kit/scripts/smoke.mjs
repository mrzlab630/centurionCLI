#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const SKILL_SIZE_LIMIT = 100_000;
const REQUIRED_SKILLS = [
  'aquila-team-orchestration',
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

function assertOverrides() {
  const researchSkill = path.join(KIT_ROOT, 'overrides', 'skills', 'research', 'research-paper-writing', 'SKILL.md');
  const soulRule = path.join(KIT_ROOT, 'overrides', 'SOUL_RUNTIME_MODEL_RULE.md');
  assert(fs.existsSync(researchSkill), 'missing research-paper-writing override');
  assert(fs.statSync(researchSkill).size < SKILL_SIZE_LIMIT, 'research-paper-writing override exceeds skill size limit');
  assert(/references\/experiment-patterns\.md/.test(readText(researchSkill)), 'research override missing reference routing');
  assert(fs.existsSync(soulRule), 'missing SOUL runtime model rule note');
  assert(/Runtime model evidence overrides stale profile summaries/.test(readText(soulRule)), 'SOUL runtime rule note missing exact rule');
}

function main() {
  for (const skill of REQUIRED_SKILLS) assertSkill(skill);
  for (const [fileName, skills] of Object.entries(REQUIRED_BUNDLES)) assertBundle(fileName, skills);
  runNodeCheck('installer/install.mjs');
  runNodeCheck('scripts/smoke.mjs');
  runNodeCheck('scripts/harness-audit.mjs');
  assertOverrides();
  runInstallerDryRun();
  runInstallerOverrideDryRun();
  process.stdout.write(JSON.stringify({ ok: true, skills: REQUIRED_SKILLS.length, bundles: Object.keys(REQUIRED_BUNDLES).length }, null, 2) + '\n');
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
