#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const kitRoot = path.join(repoRoot, 'integrations', 'hermes-legion-kit');
const hermesHome = path.resolve(process.env.HERMES_HOME || path.join(os.homedir(), '.hermes'));
const agentsHome = path.resolve(process.env.AGENTS_HOME || path.join(os.homedir(), '.agents'));
const apply = process.argv.includes('--apply');
const unknown = process.argv.slice(2).filter((arg) => arg !== '--apply');
if (unknown.length) throw new Error(`Unknown argument(s): ${unknown.join(', ')}`);

function walkFiles(root) {
  if (!fs.existsSync(root)) return [];
  const files = [];
  const stack = [root];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (entry.name === 'node_modules' || entry.name === '__pycache__' || entry.name.endsWith('.pyc')) continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (entry.isFile()) files.push(full);
      else throw new Error(`Refusing non-regular deployment path: ${full}`);
    }
  }
  return files.sort();
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function fileRecord(file, root, surface) {
  const stats = fs.statSync(file);
  return { surface, path: path.relative(root, file), sha256: sha256(file), bytes: stats.size, mode: stats.mode & 0o777 };
}

function addMapping(map, sourceRoot, targetRoot) {
  for (const source of walkFiles(sourceRoot)) map.set(path.join(targetRoot, path.relative(sourceRoot, source)), source);
}

function protectedFiles(root, incoming) {
  const protectedMap = new Map();
  for (const file of walkFiles(root)) if (!incoming.has(file)) protectedMap.set(file, sha256(file));
  return protectedMap;
}

function assertSafeTarget(root, target) {
  const relative = path.relative(root, target);
  if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Deployment target escapes its root: ${target}`);
  }
  const rootStats = fs.lstatSync(root);
  if (!rootStats.isDirectory() || rootStats.isSymbolicLink()) throw new Error(`Deployment root must be a real directory: ${root}`);
  let current = root;
  for (const component of relative.split(path.sep).slice(0, -1)) {
    current = path.join(current, component);
    if (!fs.existsSync(current)) break;
    const stats = fs.lstatSync(current);
    if (!stats.isDirectory() || stats.isSymbolicLink()) throw new Error(`Refusing unsafe deployment parent: ${current}`);
  }
}

function restoreBackups(records, rootBySurface) {
  for (const record of records) {
    const target = path.join(rootBySurface[record.surface], record.path);
    const backup = path.join(backupRoot, 'files', record.surface, record.path);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(backup, target);
    fs.chmodSync(target, record.mode);
  }
}

function removeAddedTargets(entries, rootBySurface) {
  for (const entry of entries) {
    const target = path.join(rootBySurface[entry.surface], entry.target);
    fs.rmSync(target, { force: true });
  }
}

const hermesIncoming = new Map();
addMapping(hermesIncoming, path.join(kitRoot, 'skills'), path.join(hermesHome, 'skills'));
addMapping(hermesIncoming, path.join(repoRoot, 'skills', 'open-design-producer'), path.join(hermesHome, 'skills', 'autonomous-ai-agents', 'open-design-producer'));
addMapping(hermesIncoming, path.join(kitRoot, 'skill-bundles'), path.join(hermesHome, 'skill-bundles'));
addMapping(hermesIncoming, path.join(kitRoot, 'runtime'), hermesHome);
hermesIncoming.set(path.join(hermesHome, 'centurion', 'open-design-bridge.json'), null);

const agentsIncoming = new Map();
addMapping(agentsIncoming, path.join(repoRoot, 'skills'), path.join(agentsHome, 'skills'));

const protectedHermesBefore = protectedFiles(path.join(hermesHome, 'skills'), hermesIncoming);
const protectedAgentsBefore = protectedFiles(path.join(agentsHome, 'skills'), agentsIncoming);
const replacements = [];
const additions = [];
for (const [surface, root, incoming] of [['hermes', hermesHome, hermesIncoming], ['agents', agentsHome, agentsIncoming]]) {
  for (const [target, source] of incoming) {
    assertSafeTarget(root, target);
    if (fs.existsSync(target)) {
      const stats = fs.lstatSync(target);
      if (!stats.isFile() || stats.isSymbolicLink()) throw new Error(`Refusing non-regular deployment target: ${target}`);
    }
    const entry = { surface, target: path.relative(root, target), source: source ? path.relative(repoRoot, source) : 'generated' };
    (fs.existsSync(target) ? replacements : additions).push(entry);
  }
}

const plan = {
  schema: 'CENTURION_DEPLOYMENT_V1',
  mode: apply ? 'apply' : 'plan',
  policy: 'repo-wins-preserve-local-only',
  openDesign: 'cli-only',
  repoRoot,
  hermesHome,
  agentsHome,
  incomingFiles: hermesIncoming.size + agentsIncoming.size,
  hermesIncomingFiles: hermesIncoming.size,
  agentsIncomingFiles: agentsIncoming.size,
  replacements: replacements.sort((a, b) => `${a.surface}:${a.target}`.localeCompare(`${b.surface}:${b.target}`)),
  additions: additions.sort((a, b) => `${a.surface}:${a.target}`.localeCompare(`${b.surface}:${b.target}`)),
  protectedLocalFiles: protectedHermesBefore.size + protectedAgentsBefore.size,
  untouchedSurfaces: ['config.yaml', 'SOUL.md', '.env', 'auth.json', 'plugins', 'hooks', 'mcp-servers']
};

if (!apply) {
  process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
  process.exit(0);
}

const stamp = new Date().toISOString().replaceAll(':', '').replaceAll('.', '');
const backupRoot = path.join(hermesHome, 'backups', `centurion-${stamp}`);
fs.mkdirSync(path.join(backupRoot, 'files'), { recursive: true, mode: 0o700 });
const backedUp = [];
for (const [surface, root, incoming] of [['hermes', hermesHome, hermesIncoming], ['agents', agentsHome, agentsIncoming]]) {
  for (const target of incoming.keys()) {
    if (!fs.existsSync(target)) continue;
    const relative = path.relative(root, target);
    const destination = path.join(backupRoot, 'files', surface, relative);
    fs.mkdirSync(path.dirname(destination), { recursive: true, mode: 0o700 });
    fs.copyFileSync(target, destination);
    backedUp.push(fileRecord(target, root, surface));
  }
}

const immutableBefore = {};
for (const name of ['config.yaml', 'SOUL.md', '.env', 'auth.json']) {
  const file = path.join(hermesHome, name);
  immutableBefore[name] = fs.existsSync(file) && fs.statSync(file).isFile() ? sha256(file) : null;
}
fs.writeFileSync(path.join(backupRoot, 'manifest.json'), `${JSON.stringify({ ...plan, backedUp, immutableBefore }, null, 2)}\n`, { mode: 0o600 });

const rootBySurface = { hermes: hermesHome, agents: agentsHome };
let installerReport;
try {
  const installer = spawnSync(process.execPath, [path.join(kitRoot, 'installer', 'install.mjs'), '--hermes-home', hermesHome, '--open-design-cli-only'], { encoding: 'utf8' });
  if (installer.status !== 0) throw new Error(`Installer failed: ${installer.stderr || installer.stdout}`);
  installerReport = JSON.parse(installer.stdout);
  for (const [target, source] of agentsIncoming) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    const staged = path.join(path.dirname(target), `.${path.basename(target)}.centurion-stage-${crypto.randomUUID()}`);
    fs.copyFileSync(source, staged);
    fs.chmodSync(staged, fs.statSync(source).mode & 0o777);
    fs.renameSync(staged, target);
  }
} catch (error) {
  restoreBackups(backedUp, rootBySurface);
  removeAddedTargets(additions, rootBySurface);
  throw error;
}

const incomingMismatches = [];
for (const [surface, root, incoming] of [['hermes', hermesHome, hermesIncoming], ['agents', agentsHome, agentsIncoming]]) {
  for (const [target, source] of incoming) {
    if (!fs.existsSync(target)) incomingMismatches.push(`${surface}:${path.relative(root, target)}: missing`);
    else if (source && sha256(target) !== sha256(source)) incomingMismatches.push(`${surface}:${path.relative(root, target)}: hash mismatch`);
  }
}
const protectedMismatches = [];
for (const [surface, root, protectedMap] of [['hermes', hermesHome, protectedHermesBefore], ['agents', agentsHome, protectedAgentsBefore]]) {
  for (const [file, digest] of protectedMap) {
    if (!fs.existsSync(file) || sha256(file) !== digest) protectedMismatches.push(`${surface}:${path.relative(root, file)}`);
  }
}
const immutableMismatches = [];
for (const [name, digest] of Object.entries(immutableBefore)) {
  const file = path.join(hermesHome, name);
  const after = fs.existsSync(file) && fs.statSync(file).isFile() ? sha256(file) : null;
  if (after !== digest) immutableMismatches.push(name);
}
if (incomingMismatches.length || protectedMismatches.length || immutableMismatches.length) {
  restoreBackups(backedUp, rootBySurface);
  removeAddedTargets(additions, rootBySurface);
  throw new Error(`Post-install verification failed and deployment was rolled back: ${JSON.stringify({ incomingMismatches, protectedMismatches, immutableMismatches })}`);
}

const result = {
  ...plan,
  status: 'pass',
  backupRoot,
  backedUpFiles: backedUp.length,
  installerReport,
  verification: {
    incomingFilesMatched: hermesIncoming.size + agentsIncoming.size,
    protectedLocalFilesMatched: protectedHermesBefore.size + protectedAgentsBefore.size,
    immutableSurfacesMatched: Object.keys(immutableBefore).length,
    mcpRegistered: installerReport.openDesignMcpRegistered
  }
};
fs.writeFileSync(path.join(backupRoot, 'result.json'), `${JSON.stringify(result, null, 2)}\n`, { mode: 0o600 });
process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
