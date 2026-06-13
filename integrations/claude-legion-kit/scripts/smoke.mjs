#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const EXPECTED = [
  'aedilis','aleator','architect','artifex','augur','capabilities','censor','coder','context-optimizer','documenter','error-handler','evocate-ad-opus','git-master','glossator','haruspex','indagator','ludifex','mercator','nomenclator','orator','orchestrator','pictor','planner','pontifex','praeco','praemonitor','prompt-engineer','quaestor','refactorer','researcher','reviewer','security','sicarius','skill-quartermaster','tabularius','tester','velites'
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function listSkillSlugs(directory) {
  return fs.readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(directory, entry.name, 'SKILL.md')))
    .map((entry) => entry.name)
    .sort();
}

function run(command, args, options = {}) {
  return spawnSync(command, args, { cwd: KIT_ROOT, encoding: 'utf8', ...options });
}

function smokeGuard() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-order-guard-'));
  const snapshot = path.join(os.tmpdir(), `claude-order-before-${process.pid}-${Date.now()}.json`);
  const guard = path.join(KIT_ROOT, 'scripts', 'claude-order-guard.mjs');
  try {
    fs.writeFileSync(path.join(tempRoot, 'index.html'), '<main>before</main>\n');
    fs.writeFileSync(path.join(tempRoot, 'package.json'), '{"type":"module"}\n');
    const snap = run(process.execPath, [guard, 'snapshot', '--workspace', tempRoot, '--out', snapshot]);
    assert(snap.status === 0, `snapshot failed: ${snap.stderr || snap.stdout}`);
    fs.writeFileSync(path.join(tempRoot, 'index.html'), '<main>after</main>\n');
    fs.writeFileSync(path.join(tempRoot, 'CLAUDE_RESULT.json'), JSON.stringify({
      orderVersion: 'CLAUDE_ORDER_V1',
      owner: 'PICTOR',
      status: 'done',
      filesChanged: ['index.html'],
      proof: [{ command: 'synthetic', result: 'passed', summary: 'guard smoke' }],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    }, null, 2));
    const ok = run(process.execPath, [guard, 'verify', '--workspace', tempRoot, '--before', snapshot, '--allowed', 'index.html,CLAUDE_RESULT.json', '--result', 'CLAUDE_RESULT.json']);
    assert(ok.status === 0, `verify should pass: ${ok.stderr || ok.stdout}`);
    fs.writeFileSync(path.join(tempRoot, 'package.json'), '{"type":"module","mutated":true}\n');
    const bad = run(process.execPath, [guard, 'verify', '--workspace', tempRoot, '--before', snapshot, '--allowed', 'index.html,CLAUDE_RESULT.json', '--result', 'CLAUDE_RESULT.json']);
    assert(bad.status !== 0, 'verify should fail on unallowed package.json change');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
    fs.rmSync(snapshot, { force: true });
  }
}

function main() {
  const plugin = readJson(path.join(KIT_ROOT, 'plugin', '.claude-plugin', 'plugin.json'));
  assert(plugin.name === 'centurion-legion', 'plugin name mismatch');
  assert(plugin.skills?.includes('./'), 'plugin must expose root skill');
  assert(fs.existsSync(path.join(KIT_ROOT, 'plugin', 'SKILL.md')), 'root plugin SKILL.md missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'plugin', 'skills', 'claude-order', 'SKILL.md')), 'claude-order skill missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'plugin', 'output-styles', 'centurion-legion.md')), 'output style missing');

  const canonical = listSkillSlugs(path.join(REPO_ROOT, 'skills'));
  assert(JSON.stringify(canonical) === JSON.stringify(EXPECTED), `canonical skills drift: ${canonical.length}`);
  const agents = fs.readdirSync(path.join(KIT_ROOT, 'plugin', 'agents')).filter((name) => name.endsWith('.md')).map((name) => name.replace(/\.md$/, '')).sort();
  assert(JSON.stringify(agents) === JSON.stringify(EXPECTED), `agent surface drift: ${agents.length}`);

  for (const slug of EXPECTED) {
    const text = fs.readFileSync(path.join(KIT_ROOT, 'plugin', 'agents', `${slug}.md`), 'utf8');
    assert(text.includes(`Canonical skill source: \`skills/${slug}/SKILL.md\``), `agent ${slug} missing source link`);
    assert(text.includes('CLAUDE_ORDER v1'), `agent ${slug} missing CLAUDE_ORDER guardrail`);
  }

  const validation = run('claude', ['plugin', 'validate', './plugin', '--strict']);
  assert(validation.status === 0, `claude plugin validate failed: ${validation.stderr || validation.stdout}`);

  const tempHome = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-legion-install-'));
  try {
    const install = run(process.execPath, [path.join(KIT_ROOT, 'installer', 'install.mjs'), '--claude-home', tempHome]);
    assert(install.status === 0, `installer failed: ${install.stderr || install.stdout}`);
    const report = JSON.parse(install.stdout);
    assert(report.syncedSkillCount === EXPECTED.length, `installer synced ${report.syncedSkillCount} skills`);
    assert(fs.existsSync(path.join(tempHome, 'skills', 'centurion-legion', '.claude-plugin', 'plugin.json')), 'installed plugin missing');
    assert(fs.existsSync(path.join(tempHome, 'skills', 'pictor', 'SKILL.md')), 'installed canonical skill missing');
  } finally {
    fs.rmSync(tempHome, { recursive: true, force: true });
  }

  smokeGuard();
  process.stdout.write('claude-legion-kit smoke: pass\n');
}

try {
  main();
} catch (error) {
  process.stderr.write(`claude-legion-kit smoke: fail: ${error.message}\n`);
  process.exitCode = 1;
}
