#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { parseTomlLite } from './codex-surface-audit.mjs';
import { EXPECTED_SKILL_COUNT, SHARED_CAPABILITIES } from './lib/surface-config.mjs';

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

function snapshotTree(root) {
  if (!fs.existsSync(root)) return [];
  const entries = [];
  const visit = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((left, right) => left.name.localeCompare(right.name))) {
      const full = path.join(current, entry.name);
      const relative = path.relative(root, full);
      const stats = fs.lstatSync(full);
      if (entry.isDirectory()) {
        entries.push({ relative, type: 'directory', mode: stats.mode & 0o777 });
        visit(full);
      } else {
        entries.push({ relative, type: 'file', mode: stats.mode & 0o777, content: fs.readFileSync(full).toString('base64') });
      }
    }
  };
  visit(root);
  return entries;
}

function writeExecutable(file, source) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, source, { mode: 0o755 });
  fs.chmodSync(file, 0o755);
}

function smokeAudit() {
  const audit = path.join(KIT_ROOT, 'scripts', 'codex-surface-audit.mjs');
  const repoOnly = readJsonOutput(run(process.execPath, [audit, '--repo-only', '--json']), 'repo-only audit');
  assert(repoOnly.repo.canonicalSkillCount === EXPECTED_SKILL_COUNT, 'repo canonical skill count mismatch');
  assert(repoOnly.repo.missingProtocolPointers.length === 0, 'repo protocol pointers missing');

  assert(JSON.stringify(repoOnly.repo.sharedCapabilities) === JSON.stringify(SHARED_CAPABILITIES), 'repo shared capability mismatch');
}

function smokeOpenDesignInstall() {
  const installer = path.join(KIT_ROOT, 'installer', 'install-open-design.mjs');
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-open-design-install-'));
  const agentsHome = path.join(tempRoot, 'agents');
  const codexHome = path.join(tempRoot, 'codex');
  try {
    const result = run(process.execPath, [installer, '--agents-home', agentsHome, '--codex-home', codexHome]);
    assert(result.status === 0, `Open Design installer failed: ${result.stderr || result.stdout}`);
    assert(fs.existsSync(path.join(agentsHome, 'skills', 'open-design-producer', 'SKILL.md')), 'Codex Open Design skill missing');
    assert(fs.existsSync(path.join(codexHome, 'centurion', 'open-design-bridge.json')), 'Codex Open Design bridge config missing');
    const config = fs.readFileSync(path.join(codexHome, 'config.toml'), 'utf8');
    assert(config.includes('[mcp_servers.centurion-open-design]'), 'Codex Open Design MCP missing');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function smokeOpenDesignInstallRollback() {
  const installer = path.join(KIT_ROOT, 'installer', 'install-open-design.mjs');
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-open-design-rollback-'));
  const agentsHome = path.join(tempRoot, 'agents');
  const codexHome = path.join(tempRoot, 'codex');
  const fakeBin = path.join(tempRoot, 'bin');
  try {
    const skillTarget = path.join(agentsHome, 'skills', 'open-design-producer');
    fs.mkdirSync(skillTarget, { recursive: true });
    fs.writeFileSync(path.join(skillTarget, 'old.txt'), 'old skill');
    fs.mkdirSync(path.join(codexHome, 'centurion'), { recursive: true });
    fs.writeFileSync(path.join(codexHome, 'centurion', 'open-design-bridge.json'), 'old bridge config');
    fs.writeFileSync(path.join(codexHome, 'config.toml'), 'old codex config\n');
    writeExecutable(path.join(fakeBin, 'codex'), `#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const args = process.argv.slice(2);
if (args[0] === 'mcp' && args[1] === 'get') process.exit(1);
if (args[0] === 'mcp' && args[1] === 'add') {
  fs.writeFileSync(path.join(process.env.CODEX_HOME, 'config.toml'), 'mutated before failure\\n');
  process.stderr.write('injected add failure\\n');
  process.exit(42);
}
process.exit(2);
`);
    const beforeAgents = snapshotTree(agentsHome);
    const beforeCodex = snapshotTree(codexHome);
    const result = run(process.execPath, [installer, '--agents-home', agentsHome, '--codex-home', codexHome], {
      env: { ...process.env, PATH: `${fakeBin}${path.delimiter}${process.env.PATH}` }
    });
    assert(result.status !== 0, 'Codex installer failure injection must fail');
    assert(JSON.stringify(snapshotTree(agentsHome)) === JSON.stringify(beforeAgents), 'Codex installer did not restore agents home');
    assert(JSON.stringify(snapshotTree(codexHome)) === JSON.stringify(beforeCodex), 'Codex installer did not restore Codex home');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function smokeTomlParsing() {
  const parsed = parseTomlLite(`
model = "gpt-5.6-sol" # keep this comment outside the value
description = "keep # inside double quotes"
literal = 'keep # inside single quotes'
[features]
memories = true # trailing comment
`);
  assert(parsed.model === 'gpt-5.6-sol', 'TOML parser should strip trailing comments');
  assert(parsed.description === 'keep # inside double quotes', 'TOML parser should preserve # in double-quoted values');
  assert(parsed.literal === 'keep # inside single quotes', 'TOML parser should preserve # in single-quoted values');
  assert(parsed.features.memories === true, 'TOML parser should keep nested booleans with trailing comments');
}

function smokeSync() {
  const sync = path.join(KIT_ROOT, 'scripts', 'sync-agents.mjs');
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

function smokeLegionContracts() {
  const validator = path.join(REPO_ROOT, 'integrations', 'legion-contracts', 'scripts', 'legion-contract.mjs');
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-legion-contract-'));
  try {
    const resultFile = path.join(tempRoot, 'LEGION_RESULT.json');
    fs.writeFileSync(resultFile, JSON.stringify({
      contractVersion: 'LEGION_RESULT_V1',
      owner: 'REVIEWER',
      executor: 'codex',
      status: 'done',
      filesChanged: ['README.md'],
      proof: [{ command: 'npm run smoke', result: 'passed', summary: 'contract smoke' }],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    }, null, 2));
    const ok = run(process.execPath, [validator, 'validate-result', '--file', resultFile], { cwd: REPO_ROOT });
    assert(ok.status === 0, `LEGION_RESULT validator failed: ${ok.stderr || ok.stdout}`);
    fs.writeFileSync(resultFile, JSON.stringify({
      contractVersion: 'LEGION_RESULT_V1',
      owner: 'REVIEWER',
      executor: 'codex',
      status: 'done',
      filesChanged: ['README.md'],
      proof: [],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    }, null, 2));
    const bad = run(process.execPath, [validator, 'validate-result', '--file', resultFile], { cwd: REPO_ROOT });
    assert(bad.status !== 0, 'LEGION_RESULT validator should fail on done result without proof');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function smokeCamofoxSkill() {
  const skillRoot = path.join(KIT_ROOT, 'skills', 'camofox-browser');
  const skillFile = path.join(skillRoot, 'SKILL.md');
  const scriptFile = path.join(skillRoot, 'scripts', 'camofox-smoke.mjs');
  const metadataFile = path.join(skillRoot, 'agents', 'openai.yaml');
  assert(fs.existsSync(skillFile), 'camofox-browser SKILL.md missing');
  assert(fs.existsSync(scriptFile), 'camofox-smoke script missing');
  assert(fs.existsSync(metadataFile), 'camofox openai.yaml missing');
  const skill = fs.readFileSync(skillFile, 'utf8');
  const metadata = fs.readFileSync(metadataFile, 'utf8');
  assert(/Do not use for routine localhost UI checks/.test(skill), 'camofox skill must defer routine UI checks to normal browser tools');
  assert(/Do not import cookies/.test(skill), 'camofox skill must guard cookie import');
  assert(/Run Camofox checks sequentially/.test(skill), 'camofox skill must document sequential execution');
  assert(/allow_implicit_invocation: false/.test(metadata), 'camofox skill must be explicit opt-in');
  const check = run(process.execPath, ['--check', scriptFile]);
  assert(check.status === 0, `camofox script syntax failed: ${check.stderr || check.stdout}`);
}

function main() {
  smokeTomlParsing();
  smokeAudit();
  smokeSync();
  smokeLegionEval();
  smokeLegionContracts();
  smokeCamofoxSkill();
  smokeOpenDesignInstall();
  smokeOpenDesignInstallRollback();
  process.stdout.write('codex-legion-kit smoke: pass\n');
}

try {
  main();
} catch (error) {
  process.stderr.write(`codex-legion-kit smoke: fail: ${error.message}\n`);
  process.exitCode = 1;
}
