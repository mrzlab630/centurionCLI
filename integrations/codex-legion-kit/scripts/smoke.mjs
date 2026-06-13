#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { parseTomlLite } from './codex-surface-audit.mjs';
import { EXPECTED_SKILL_COUNT } from './lib/surface-config.mjs';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function run(command, args, options = {}) {
  return spawnSync(command, args, { cwd: KIT_ROOT, encoding: 'utf8', ...options });
}

function readJsonOutput(result, label) {
  assert(result.status === 0, `${label} failed: ${result.stderr || result.stdout}`);
  return JSON.parse(result.stdout);
}

function smokeAudit() {
  const audit = path.join(KIT_ROOT, 'scripts', 'codex-surface-audit.mjs');
  const repoOnly = readJsonOutput(run(process.execPath, [audit, '--repo-only', '--json']), 'repo-only audit');
  assert(repoOnly.repo.canonicalSkillCount === EXPECTED_SKILL_COUNT, 'repo canonical skill count mismatch');
  assert(repoOnly.repo.missingProtocolPointers.length === 0, 'repo protocol pointers missing');

  const full = readJsonOutput(run(process.execPath, [audit, '--json']), 'full audit');
  assert(full.repo.canonicalSkillCount === EXPECTED_SKILL_COUNT, 'full audit canonical count mismatch');
  assert(full.activeSkills.count === EXPECTED_SKILL_COUNT, 'active skill count mismatch');
  assert(full.activeSkills.drift.length === 0, 'active ~/.agents skill drift must be zero');
  assert(full.codex.model === 'gpt-5.5', 'Codex model must be gpt-5.5');
}

function smokeTomlParsing() {
  const parsed = parseTomlLite(`
model = "gpt-5.5" # keep this comment outside the value
description = "keep # inside double quotes"
literal = 'keep # inside single quotes'
[features]
memories = true # trailing comment
`);
  assert(parsed.model === 'gpt-5.5', 'TOML parser should strip trailing comments');
  assert(parsed.description === 'keep # inside double quotes', 'TOML parser should preserve # in double-quoted values');
  assert(parsed.literal === 'keep # inside single quotes', 'TOML parser should preserve # in single-quoted values');
  assert(parsed.features.memories === true, 'TOML parser should keep nested booleans with trailing comments');
}

function smokeSync() {
  const sync = path.join(KIT_ROOT, 'scripts', 'sync-agents.mjs');
  const current = readJsonOutput(run(process.execPath, [sync, '--json']), 'active sync dry-run');
  assert(current.drift.length === 0, 'active sync dry-run should not report drift');

  const tempHome = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-agents-sync-'));
  try {
    const dry = readJsonOutput(run(process.execPath, [sync, '--agents-home', tempHome, '--skill', 'tester', '--json']), 'temp sync dry-run');
    assert(dry.drift.length === 1 && dry.synced.length === 0, 'temp dry-run must report tester drift without syncing');
    const write = readJsonOutput(run(process.execPath, [sync, '--agents-home', tempHome, '--skill', 'tester', '--write', '--json']), 'temp sync write');
    assert(write.synced.includes('tester'), 'temp write must sync tester');
    assert(fs.existsSync(path.join(tempHome, 'skills', 'tester', 'references', 'frontend-sweep.md')), 'tester reference missing after sync');
    const sentinel = path.join(tempHome, 'skills', 'tester', 'references', 'node_modules', '.sentinel');
    fs.mkdirSync(path.dirname(sentinel), { recursive: true });
    fs.writeFileSync(sentinel, 'keep generated dependencies');
    const preserve = readJsonOutput(run(process.execPath, [sync, '--agents-home', tempHome, '--skill', 'tester', '--write', '--json']), 'temp sync preserve generated');
    assert(preserve.synced.length === 0 && preserve.drift.length === 0, 'temp generated-only drift must stay ignored');
    assert(fs.existsSync(sentinel), 'generated node_modules sentinel must survive write sync');
    const clean = readJsonOutput(run(process.execPath, [sync, '--agents-home', tempHome, '--skill', 'tester', '--json']), 'temp sync clean');
    assert(clean.drift.length === 0, 'temp sync should be clean after write');
  } finally {
    fs.rmSync(tempHome, { recursive: true, force: true });
  }
}

function smokeLegionEval() {
  const evalScript = path.join(REPO_ROOT, 'skills', 'tester', 'scripts', 'legion-skill-eval.mjs');
  const result = run(process.execPath, [evalScript], { cwd: REPO_ROOT });
  assert(result.status === 0, `legion skill eval failed: ${result.stderr || result.stdout}`);
  const report = JSON.parse(result.stdout);
  assert(report.status === 'pass', 'legion skill eval status must pass');
}

function main() {
  smokeTomlParsing();
  smokeAudit();
  smokeSync();
  smokeLegionEval();
  process.stdout.write('codex-legion-kit smoke: pass\n');
}

try {
  main();
} catch (error) {
  process.stderr.write(`codex-legion-kit smoke: fail: ${error.message}\n`);
  process.exitCode = 1;
}
