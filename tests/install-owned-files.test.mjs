import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import https from 'node:https';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const INSTALLER = path.join(ROOT, 'scripts', 'install-owned-files.mjs');

function digest(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function snapshot(root) {
  const entries = [];
  function visit(directory) {
    for (const name of fs.readdirSync(directory).sort()) {
      const full = path.join(directory, name);
      const stat = fs.lstatSync(full);
      const relative = path.relative(root, full);
      entries.push([relative, stat.mode & 0o777, stat.isDirectory() ? 'directory' : digest(full)]);
      if (stat.isDirectory()) visit(full);
    }
  }
  visit(root);
  return entries;
}

function runInstall(agentsHome, claudeHome, environment = {}) {
  return spawnSync(process.execPath, [INSTALLER, '--agents-home', agentsHome, '--claude-home', claudeHome], {
    encoding: 'utf8',
    env: { ...process.env, ...environment }
  });
}

function runPython(code, args) {
  return new Promise((resolve, reject) => {
    const child = spawn('python3', ['-c', code, ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
    let stderr = '';
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (status) => resolve({ status, stderr }));
  });
}

test('staged install preserves foreign files, verifies bytes and modes, retains backups, and rolls back injected failure', async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-owned-install-'));
  const agentsHome = path.join(temporary, '.agents');
  const claudeHome = path.join(temporary, '.claude');
  const oldCore = path.join(agentsHome, 'libs', 'legion_core.py');
  const oldSkill = path.join(agentsHome, 'skills', 'velites', 'SKILL.md');
  const memory = path.join(agentsHome, 'skills', 'velites', 'memory', 'notes.md');
  const foreign = path.join(agentsHome, 'skills', 'foreign-skill', 'SKILL.md');
  let server;
  try {
    for (const file of [oldCore, oldSkill, memory, foreign]) fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(oldCore, 'old unsafe library\n', { mode: 0o600 });
    fs.writeFileSync(oldSkill, 'old skill\n');
    fs.writeFileSync(memory, 'user memory\n');
    fs.writeFileSync(foreign, 'foreign skill\n');

    const result = runInstall(agentsHome, claudeHome);
    assert.equal(result.status, 0, result.stderr);
    const report = JSON.parse(result.stdout);
    assert.ok(report.skillCount >= 37);
    assert.ok(report.targetCount > report.skillCount);
    assert.ok(report.backupCount >= 2);
    assert.equal(fs.readFileSync(memory, 'utf8'), 'user memory\n');
    assert.equal(fs.readFileSync(foreign, 'utf8'), 'foreign skill\n');

    const sourceCore = path.join(ROOT, 'libs', 'legion_core.py');
    const sourceRecon = path.join(ROOT, 'skills', 'velites', 'scripts', 'recon.py');
    const installedRecon = path.join(agentsHome, 'skills', 'velites', 'scripts', 'recon.py');
    const installedExecutable = path.join(agentsHome, 'skills', 'skill-quartermaster', 'scripts', 'findskills-audit.mjs');
    assert.equal(digest(oldCore), digest(sourceCore));
    assert.equal(digest(path.join(claudeHome, 'libs', 'legion_core.py')), digest(sourceCore));
    assert.equal(digest(installedRecon), digest(sourceRecon));
    assert.equal(fs.existsSync(path.join(agentsHome, 'skills', 'velites', 'scripts', '__pycache__')), false);
    assert.equal(fs.statSync(oldCore).mode & 0o777, 0o644);
    assert.equal(fs.statSync(installedRecon).mode & 0o777, 0o644);
    assert.equal(fs.statSync(installedExecutable).mode & 0o777, 0o755);
    assert.equal(fs.readFileSync(path.join(agentsHome, 'libs', `.legion_core.py.centurion-backup-${report.backupBatchId}`), 'utf8'), 'old unsafe library\n');
    assert.equal(fs.readFileSync(path.join(agentsHome, 'skills', 'velites', `.SKILL.md.centurion-backup-${report.backupBatchId}`), 'utf8'), 'old skill\n');

    const firstSkill = path.join(agentsHome, 'skills', 'aedilis', 'SKILL.md');
    fs.writeFileSync(firstSkill, 'changed before failed reinstall\n');
    const before = snapshot(temporary);
    const failed = runInstall(agentsHome, claudeHome, { CENTURION_INSTALL_TEST_FAIL_AFTER: '3' });
    assert.notEqual(failed.status, 0);
    assert.match(failed.stderr, /Injected install failure after 3 swaps/);
    assert.deepEqual(snapshot(temporary), before);
    assert.equal(fs.readFileSync(firstSkill, 'utf8'), 'changed before failed reinstall\n');

    // Import the staged installed library in a clean Python process. A local
    // self-signed TLS server must still fail certificate verification.
    const key = path.join(temporary, 'key.pem');
    const cert = path.join(temporary, 'cert.pem');
    const openssl = spawnSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', cert, '-days', '1', '-subj', '/CN=localhost'], { encoding: 'utf8' });
    assert.equal(openssl.status, 0, openssl.stderr);
    server = https.createServer({ key: fs.readFileSync(key), cert: fs.readFileSync(cert) }, (_request, response) => response.end('ok'));
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const python = await runPython(`
import importlib.util, ssl, urllib.error, urllib.request, sys
before = ssl._create_default_https_context
spec = importlib.util.spec_from_file_location('installed_legion_core', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert ssl._create_default_https_context is before is ssl.create_default_context
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    opener.open(sys.argv[2], timeout=3)
except urllib.error.URLError as error:
    assert isinstance(error.reason, ssl.SSLCertVerificationError), error
else:
    raise AssertionError('untrusted TLS certificate was accepted')
`, [oldCore, `https://127.0.0.1:${server.address().port}/`]);
    assert.equal(python.status, 0, python.stderr);
  } finally {
    if (server) await new Promise((resolve) => server.close(resolve));
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test('foreign files inside a managed directory block installation before any swap', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-owned-foreign-'));
  try {
    const agentsHome = path.join(temporary, '.agents');
    const claudeHome = path.join(temporary, '.claude');
    const oldSkill = path.join(agentsHome, 'skills', 'aedilis', 'SKILL.md');
    const foreign = path.join(agentsHome, 'skills', 'velites', 'scripts', 'local-user-tool.py');
    fs.mkdirSync(path.dirname(oldSkill), { recursive: true });
    fs.mkdirSync(path.dirname(foreign), { recursive: true });
    fs.writeFileSync(oldSkill, 'old skill\n');
    fs.writeFileSync(foreign, 'user tool\n');
    const before = snapshot(temporary);
    const result = runInstall(agentsHome, claudeHome);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Unmanaged file in managed directory/);
    assert.deepEqual(snapshot(temporary), before);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test('symlink install ancestor is rejected without writing through it', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-owned-symlink-'));
  try {
    const redirected = path.join(temporary, 'redirected');
    fs.mkdirSync(redirected);
    fs.symlinkSync(redirected, path.join(temporary, '.agents'));
    const before = snapshot(redirected);
    const result = runInstall(path.join(temporary, '.agents'), path.join(temporary, '.claude'));
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Symlink install ancestor/);
    assert.deepEqual(snapshot(redirected), before);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test('codex home receives libraries when specified', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-owned-codex-'));
  try {
    const agentsHome = path.join(temporary, '.agents');
    const claudeHome = path.join(temporary, '.claude');
    const codexHome = path.join(temporary, '.codex');
    const result = spawnSync(process.execPath, [INSTALLER, '--agents-home', agentsHome, '--claude-home', claudeHome, '--codex-home', codexHome], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const sourceCore = path.join(ROOT, 'libs', 'legion_core.py');
    const agentsCore = path.join(agentsHome, 'libs', 'legion_core.py');
    const claudeCore = path.join(claudeHome, 'libs', 'legion_core.py');
    const codexCore = path.join(codexHome, 'libs', 'legion_core.py');
    assert.equal(digest(agentsCore), digest(sourceCore));
    assert.equal(digest(claudeCore), digest(sourceCore));
    assert.equal(digest(codexCore), digest(sourceCore));
    assert.equal(fs.statSync(codexCore).mode & 0o777, 0o644);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});
