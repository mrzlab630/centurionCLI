#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SOURCE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKILL_FILES = ['SKILL.md', 'REFERENCE.md', 'package.json', 'package-lock.json'];
const SKILL_DIRECTORIES = ['references', 'agents', 'scripts', 'knowledge'];

function parseArgs(args) {
  const options = {
    agentsHome: process.env.AGENTS_HOME || path.join(os.homedir(), '.agents'),
    claudeHome: process.env.CLAUDE_HOME || path.join(os.homedir(), '.claude'),
    codexHome: process.env.CODEX_HOME || null
  };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === '--agents-home' || arg === '--claude-home' || arg === '--codex-home') {
      if (!args[index + 1]) throw new Error(`Missing value for ${arg}`);
      const key = arg === '--agents-home' ? 'agentsHome' : arg === '--claude-home' ? 'claudeHome' : 'codexHome';
      options[key] = path.resolve(args[++index]);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  options.agentsHome = path.resolve(options.agentsHome);
  options.claudeHome = path.resolve(options.claudeHome);
  if (options.codexHome) options.codexHome = path.resolve(options.codexHome);
  if (options.agentsHome === options.claudeHome) throw new Error('Agents and Claude homes must differ');
  if (options.codexHome && (options.codexHome === options.agentsHome || options.codexHome === options.claudeHome)) {
    throw new Error('Codex home must differ from Agents and Claude homes');
  }
  return options;
}

function lstatOrNull(target) {
  try { return fs.lstatSync(target); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function expectedMode(source, kind) {
  if (kind === 'directory') return 0o755;
  if (source.endsWith('.py')) return 0o644;
  return fs.statSync(source).mode & 0o111 ? 0o755 : 0o644;
}

function isGenerated(name) {
  return name === '__pycache__' || name.endsWith('.pyc');
}

function inspectTree(root, source = false) {
  const entries = [];
  function visit(current, relative) {
    const stats = fs.lstatSync(current);
    if (stats.isSymbolicLink()) throw new Error(`Symlink in ${source ? 'source' : 'staged target'}: ${current}`);
    if (stats.isDirectory()) {
      entries.push({ path: relative, kind: 'directory', mode: source ? expectedMode(current, 'directory') : stats.mode & 0o777 });
      for (const name of fs.readdirSync(current).sort()) {
        if (source && isGenerated(name)) continue;
        visit(path.join(current, name), path.join(relative, name));
      }
    } else if (stats.isFile()) {
      entries.push({
        path: relative,
        kind: 'file',
        mode: source ? expectedMode(current, 'file') : stats.mode & 0o777,
        sha256: crypto.createHash('sha256').update(fs.readFileSync(current)).digest('hex')
      });
    } else {
      throw new Error(`Unsupported file type: ${current}`);
    }
  }
  visit(root, '.');
  return JSON.stringify(entries);
}

function copyExact(source, destination) {
  const stats = fs.lstatSync(source);
  if (stats.isSymbolicLink()) throw new Error(`Symlink in source: ${source}`);
  if (stats.isDirectory()) {
    fs.mkdirSync(destination, { mode: 0o755 });
    fs.chmodSync(destination, 0o755);
    for (const name of fs.readdirSync(source).sort()) {
      if (isGenerated(name)) continue;
      copyExact(path.join(source, name), path.join(destination, name));
    }
  } else if (stats.isFile()) {
    fs.copyFileSync(source, destination);
    fs.chmodSync(destination, expectedMode(source, 'file'));
  } else {
    throw new Error(`Unsupported file type: ${source}`);
  }
}

function listOperations(options) {
  const operations = [];
  const skillsRoot = path.join(SOURCE_ROOT, 'skills');
  let skillCount = 0;
  for (const name of fs.readdirSync(skillsRoot).sort()) {
    const sourceDir = path.join(skillsRoot, name);
    if (!fs.lstatSync(sourceDir).isDirectory() || !fs.existsSync(path.join(sourceDir, 'SKILL.md'))) continue;
    skillCount += 1;
    const targetDir = path.join(options.agentsHome, 'skills', name);
    for (const entry of [...SKILL_FILES, ...SKILL_DIRECTORIES]) {
      const source = path.join(sourceDir, entry);
      if (lstatOrNull(source)) operations.push({ source, target: path.join(targetDir, entry) });
    }
  }
  const libsRoot = path.join(SOURCE_ROOT, 'libs');
  for (const name of fs.readdirSync(libsRoot).sort()) {
    if (!name.endsWith('.py')) continue;
    const source = path.join(libsRoot, name);
    if (!fs.lstatSync(source).isFile()) throw new Error(`Library source is not a regular file: ${source}`);
    for (const home of [options.agentsHome, options.claudeHome]) {
      operations.push({ source, target: path.join(home, 'libs', name) });
    }
  }
  const codexHome = options.codexHome;
  if (codexHome) {
    for (const name of fs.readdirSync(libsRoot).sort()) {
      if (!name.endsWith('.py')) continue;
      const source = path.join(libsRoot, name);
      operations.push({ source, target: path.join(codexHome, 'libs', name) });
    }
  }
  return { operations, skillCount };
}

function ensureParent(target, createdParents, createMissing = true) {
  const missing = [];
  let cursor = path.dirname(target);
  while (true) {
    const stats = lstatOrNull(cursor);
    if (stats?.isSymbolicLink()) throw new Error(`Symlink install ancestor: ${cursor}`);
    if (stats && !stats.isDirectory()) throw new Error(`Install ancestor is not a directory: ${cursor}`);
    if (!stats) {
      if (!createMissing) throw new Error(`Install ancestor disappeared: ${cursor}`);
      missing.push(cursor);
    }
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
    cursor = parent;
  }
  for (const directory of missing.reverse()) {
    fs.mkdirSync(directory);
    createdParents.add(directory);
  }
  // A staged sibling must resolve to the same directory as its target.
  const parent = path.dirname(target);
  if (!fs.lstatSync(parent).isDirectory()) throw new Error(`Install parent is not a directory: ${parent}`);
}

function rejectForeignEntries(source, target) {
  const sourcePaths = new Set(JSON.parse(inspectTree(source, true)).map((entry) => entry.path));
  for (const entry of JSON.parse(inspectTree(target))) {
    if (entry.path === '.') continue;
    if (entry.path.split(path.sep).some(isGenerated)) continue;
    if (!sourcePaths.has(entry.path)) throw new Error(`Unmanaged file in managed directory: ${path.join(target, entry.path)}`);
  }
}

function cleanupParents(createdParents) {
  for (const directory of [...createdParents].sort((a, b) => b.length - a.length)) {
    try { fs.rmdirSync(directory); } catch (error) {
      if (!['ENOENT', 'ENOTEMPTY', 'EEXIST'].includes(error.code)) throw error;
    }
  }
}

function stageAll(operations, batchId, createdParents) {
  for (const operation of operations) {
    ensureParent(operation.target, createdParents);
    const sourceStats = fs.lstatSync(operation.source);
    const existing = lstatOrNull(operation.target);
    if (existing && (existing.isSymbolicLink() || existing.isDirectory() !== sourceStats.isDirectory())) {
      throw new Error(`Unsafe target type: ${operation.target}`);
    }
    if (existing?.isDirectory()) rejectForeignEntries(operation.source, operation.target);
    operation.before = existing ? inspectTree(operation.target) : null;
    operation.expected = inspectTree(operation.source, true);
    operation.staged = path.join(path.dirname(operation.target), `.${path.basename(operation.target)}.centurion-stage-${batchId}`);
    operation.backup = existing ? path.join(path.dirname(operation.target), `.${path.basename(operation.target)}.centurion-backup-${batchId}`) : null;
    if (lstatOrNull(operation.staged) || (operation.backup && lstatOrNull(operation.backup))) {
      throw new Error(`Install batch path already exists: ${operation.target}`);
    }
    copyExact(operation.source, operation.staged);
    if (inspectTree(operation.staged) !== operation.expected) throw new Error(`Staged hash or mode mismatch: ${operation.target}`);
  }
}

function commitAll(operations, failAfter) {
  const touched = [];
  try {
    for (const operation of operations) {
      if (inspectTree(operation.source, true) !== operation.expected) throw new Error(`Source changed during install: ${operation.source}`);
      ensureParent(operation.target, new Set(), false);
      const current = lstatOrNull(operation.target);
      if ((current ? inspectTree(operation.target) : null) !== operation.before) {
        throw new Error(`Target changed during install: ${operation.target}`);
      }
      if (current?.isDirectory()) rejectForeignEntries(operation.source, operation.target);
      touched.push(operation);
      if (operation.backup) {
        fs.renameSync(operation.target, operation.backup);
        operation.backedUp = true;
        if (inspectTree(operation.backup) !== operation.before) throw new Error(`Backup hash or mode mismatch: ${operation.target}`);
      }
      fs.renameSync(operation.staged, operation.target);
      operation.installed = true;
      if (inspectTree(operation.target) !== operation.expected) throw new Error(`Installed hash or mode mismatch: ${operation.target}`);
      if (failAfter && touched.length === failAfter) throw new Error(`Injected install failure after ${failAfter} swaps`);
    }
  } catch (error) {
    const rollbackErrors = [];
    for (const operation of touched.reverse()) {
      try {
        if (operation.installed) fs.rmSync(operation.target, { recursive: true, force: true });
        if (operation.backedUp) fs.renameSync(operation.backup, operation.target);
      } catch (rollbackError) {
        rollbackErrors.push(`${operation.target}: ${rollbackError.message}`);
      }
    }
    if (rollbackErrors.length) throw new Error(`${error.message}; rollback incomplete: ${rollbackErrors.join('; ')}`);
    throw error;
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const { operations, skillCount } = listOperations(options);
  const batchId = crypto.randomUUID();
  const createdParents = new Set();
  const injected = process.env.CENTURION_INSTALL_TEST_FAIL_AFTER;
  const failAfter = injected ? Number(injected) : 0;
  if (injected && (!Number.isSafeInteger(failAfter) || failAfter < 1)) throw new Error('Invalid test failure point');
  let committed = false;
  try {
    stageAll(operations, batchId, createdParents);
    commitAll(operations, failAfter);
    committed = true;
  } finally {
    for (const operation of operations) {
      if (operation.staged) fs.rmSync(operation.staged, { recursive: true, force: true });
    }
    if (!committed) cleanupParents(createdParents);
  }
  process.stdout.write(`${JSON.stringify({
    skillCount,
    targetCount: operations.length,
    backupCount: operations.filter((operation) => operation.backup).length,
    backupBatchId: batchId,
    backupPattern: '.<target>.centurion-backup-<backupBatchId>'
  })}\n`);
}

try { main(); } catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
