#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { isPlainObject, parseStrictJson, validateCanonicalAgentResult, validateDelegationResult } from '../lib/claude-result-validator.mjs';

const IGNORE_DIRS = new Set(['.git', 'node_modules', 'dist', 'build', 'coverage', '.venv', 'vendor']);
const ORDER_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/;

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const args = { _: [], command };
  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (token.startsWith('--')) {
      const key = token.slice(2);
      const next = rest[index + 1];
      if (!next || next.startsWith('--')) args[key] = true;
      else {
        args[key] = next;
        index += 1;
      }
    } else args._.push(token);
  }
  return args;
}

function usage() {
  return `Usage:\n  node scripts/claude-order-guard.mjs snapshot --workspace <dir> --order-id <safe-id> [--out <namespace-relative-or-absolute-path>]\n  node scripts/claude-order-guard.mjs verify --workspace <dir> --order-id <safe-id> [--before <namespace-relative-or-absolute-path>] --allowed <path[,path]> [--result <namespace-relative-or-absolute-path>] [--forbidden <regex[,regex]>]\n`;
}

function splitList(value) {
  if (!value || value === true) return [];
  return String(value).split(',').map((item) => item.trim()).filter(Boolean);
}

function normalizeRelative(file) {
  return String(file).split(/[\\/]/g).join('/').replace(/^\.\//, '');
}

function requireWorkspace(value) {
  if (!value || value === true) throw new Error('--workspace is required');
  const workspace = path.resolve(String(value));
  let stats;
  try {
    stats = fs.lstatSync(workspace);
  } catch {
    throw new Error(`workspace not found: ${workspace}`);
  }
  if (stats.isSymbolicLink()) throw new Error(`workspace symlink rejected: ${workspace}`);
  if (!stats.isDirectory()) throw new Error(`workspace is not a directory: ${workspace}`);
  return workspace;
}

function requireOrderId(value) {
  if (typeof value !== 'string' || value !== value.trim() || !ORDER_ID_PATTERN.test(value)) throw new Error('order-id must be one safe path component matching [A-Za-z0-9][A-Za-z0-9_-]{7,127}');
  return value;
}

function isWithin(parent, child) {
  const relative = path.relative(parent, child);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function assertNoSymlinkComponents(root, target) {
  if (!isWithin(root, target)) throw new Error(`path escapes workspace: ${target}`);
  let current = root;
  const relative = path.relative(root, target);
  for (const component of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, component);
    let stats;
    try {
      stats = fs.lstatSync(current);
    } catch (error) {
      if (error.code === 'ENOENT') break;
      throw error;
    }
    if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${current}`);
    if (current !== target && !stats.isDirectory()) throw new Error(`path component is not a directory: ${current}`);
  }
}

function ensureDirectoryChain(root, target) {
  if (!isWithin(root, target)) throw new Error(`path escapes workspace: ${target}`);
  let current = root;
  const relative = path.relative(root, target);
  for (const component of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, component);
    try {
      const stats = fs.lstatSync(current);
      if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${current}`);
      if (!stats.isDirectory()) throw new Error(`path component is not a directory: ${current}`);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      fs.mkdirSync(current);
      const stats = fs.lstatSync(current);
      if (stats.isSymbolicLink() || !stats.isDirectory()) throw new Error(`control directory creation rejected: ${current}`);
    }
  }
}

function namespaceFor(workspace, orderId) {
  return path.join(workspace, '.centurion', 'agents_results', requireOrderId(orderId));
}

function controlArtifact(workspace, namespace, value, defaultName, label) {
  const raw = value === undefined || value === true ? path.join(namespace, defaultName) : String(value);
  if (!raw.trim()) throw new Error(`${label} must not be empty`);
  const target = path.resolve(workspace, raw);
  if (target === namespace || !isWithin(namespace, target)) throw new Error(`${label} must be below the order namespace: ${namespace}`);
  assertNoSymlinkComponents(workspace, target);
  return target;
}

function walkFiles(directory, root = directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (IGNORE_DIRS.has(entry.name)) continue;
    const fullPath = path.join(directory, entry.name);
    const stats = fs.lstatSync(fullPath);
    if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${fullPath}`);
    if (stats.isDirectory()) files.push(...walkFiles(fullPath, root));
    else files.push(normalizeRelative(path.relative(root, fullPath)));
  }
  return files.sort();
}

function hashFile(file) {
  const stats = fs.lstatSync(file);
  if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${file}`);
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function snapshotWorkspace(workspace) {
  const snapshot = {};
  for (const file of walkFiles(workspace)) snapshot[file] = hashFile(path.join(workspace, file));
  return snapshot;
}

function writeJsonExclusive(file, data) {
  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, { flag: 'wx' });
}

function custodyDigestPath(snapshotFile) {
  return `${snapshotFile}.sha256`;
}

function rejectSymlinkFile(file) {
  const stats = fs.lstatSync(file);
  if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${file}`);
}

function writeCustodySnapshot(file, data) {
  const encoded = `${JSON.stringify(data, null, 2)}\n`;
  const digestFile = custodyDigestPath(file);
  if (fs.existsSync(file) || fs.existsSync(digestFile)) throw new Error(`snapshot custody files already exist: ${file}`);
  writeJsonExclusive(file, data);
  try {
    fs.writeFileSync(digestFile, `${crypto.createHash('sha256').update(encoded).digest('hex')}\n`, { flag: 'wx', mode: 0o600 });
  } catch (error) {
    fs.rmSync(file, { force: true });
    throw error;
  }
}

function readCustodySnapshot(file) {
  const digestFile = custodyDigestPath(file);
  rejectSymlinkFile(file);
  const bytes = fs.readFileSync(file);
  const preserveRejected = (reason) => {
    const digest = crypto.createHash('sha256').update(bytes).digest('hex');
    const evidence = `${file}.${digest}.rejected.bin`;
    try {
      fs.writeFileSync(evidence, bytes, { flag: 'wx', mode: 0o600 });
    } catch (error) {
      if (error.code !== 'EEXIST') throw new Error(`${reason}; raw snapshot evidence could not be preserved: ${error.message}`);
    }
    throw new Error(`${reason}; raw snapshot evidence: ${evidence}`);
  };
  let expected;
  try {
    rejectSymlinkFile(digestFile);
    expected = fs.readFileSync(digestFile, 'utf8').trim();
  } catch (error) {
    if (error.code === 'ENOENT') preserveRejected(`snapshot custody digest not found: ${digestFile}`);
    throw error;
  }
  if (!/^[a-f0-9]{64}$/i.test(expected)) preserveRejected(`snapshot custody digest is invalid: ${digestFile}`);
  const actual = crypto.createHash('sha256').update(bytes).digest('hex');
  if (actual !== expected.toLowerCase()) preserveRejected(`snapshot custody digest mismatch: ${file}`);
  try {
    return parseStrictJson(bytes.toString('utf8'), `JSON file ${file}`);
  } catch (error) {
    preserveRejected(`snapshot JSON parse failed: ${error.message}`);
  }
}

function readJson(file) {
  const stats = fs.lstatSync(file);
  if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${file}`);
  return parseStrictJson(fs.readFileSync(file, 'utf8'), `JSON file ${file}`);
}

function changedFiles(before, after, excluded = new Set()) {
  const names = new Set([...Object.keys(before), ...Object.keys(after)]);
  return [...names].filter((name) => !excluded.has(name) && before[name] !== after[name]).sort();
}

function isAllowed(file, allowedPaths) {
  const normalized = normalizeRelative(file);
  return allowedPaths.some((allowed) => {
    const value = normalizeRelative(allowed).replace(/\/+$/, '');
    return normalized === value || normalized.startsWith(`${value}/`);
  });
}

function scanForbidden(workspace, files, patterns) {
  const compiled = patterns.map((pattern) => ({ pattern, re: new RegExp(pattern, 'i') }));
  const hits = [];
  for (const file of files) {
    const fullPath = path.join(workspace, file);
    if (!fs.existsSync(fullPath)) continue;
    const text = fs.readFileSync(fullPath, 'utf8');
    for (const item of compiled) if (item.re.test(text)) hits.push({ file, pattern: item.pattern });
  }
  return hits;
}

function validateResultShape(result, orderId, allowLegacy) {
  if (allowLegacy) return validateDelegationResult(result, { acceptedContractVersions: [], acceptedOrderVersions: ['CLAUDE_ORDER_V1'], actorLabel: 'claude' });
  return validateCanonicalAgentResult(result, { expectedOrderId: orderId, expectedExecutor: 'claude' });
}

function sameList(left, right) {
  const a = [...new Set(left)].sort();
  const b = [...new Set(right)].sort();
  return a.length === b.length && a.every((item, index) => item === b[index]);
}

function isPlainFileChange(item) {
  return isPlainObject(item) && typeof item.path === 'string';
}

function workspaceRelative(workspace, target) {
  return normalizeRelative(path.relative(workspace, target));
}

function declaredPaths(workspace, value) {
  return splitList(value).map((item) => {
    const target = path.isAbsolute(item) ? path.resolve(item) : path.resolve(workspace, item);
    if (!isWithin(workspace, target)) throw new Error(`allowed path escapes workspace: ${item}`);
    assertNoSymlinkComponents(workspace, target);
    return workspaceRelative(workspace, target);
  });
}

function verify(args) {
  const workspace = requireWorkspace(args.workspace);
  const orderId = requireOrderId(args['order-id']);
  const namespace = namespaceFor(workspace, orderId);
  const namespaceStats = fs.existsSync(namespace) ? fs.lstatSync(namespace) : null;
  if (!namespaceStats) throw new Error(`order namespace not found: ${namespace}`);
  if (namespaceStats.isSymbolicLink()) throw new Error(`symlink component rejected: ${namespace}`);
  if (!namespaceStats.isDirectory()) throw new Error(`order namespace is not a directory: ${namespace}`);

  if (args.before === undefined || !path.isAbsolute(String(args.before))) throw new Error('--before must be an explicit absolute external custody path');
  const beforeFile = path.resolve(String(args.before));
  if (isWithin(workspace, beforeFile)) throw new Error('--before must be outside the workspace; in-workspace snapshots are unsafe controller custody');
  assertNoSymlinkComponents(path.parse(beforeFile).root, beforeFile);
  const resultFile = controlArtifact(workspace, namespace, args.result, 'CLAUDE_RESULT.json', '--result');
  const allowed = declaredPaths(workspace, args.allowed);
  if (!allowed.length) throw new Error('allowed paths are required');
  if (!fs.existsSync(beforeFile)) throw new Error(`snapshot custody file not found: ${beforeFile}`);

  const before = readCustodySnapshot(beforeFile);
  const after = snapshotWorkspace(workspace);
  const resultRelative = workspaceRelative(workspace, resultFile);
  const changed = changedFiles(before, after);
  const productChanged = changed.filter((file) => file !== resultRelative);
  const allowedPaths = [...new Set([...allowed, resultRelative])];
  const scopeViolations = changed.filter((file) => !isAllowed(file, allowedPaths));
  const forbiddenHits = scanForbidden(workspace, changed.filter((file) => isAllowed(file, allowedPaths)), splitList(args.forbidden));
  const failures = [];

  if (!fs.existsSync(resultFile)) failures.push(`missing result file: ${workspaceRelative(workspace, resultFile)}`);
  let result = null;
  if (fs.existsSync(resultFile)) {
    try {
      result = readJson(resultFile);
      const allowLegacy = args['allow-legacy'] === true;
      failures.push(...validateResultShape(result, orderId, allowLegacy));
      if (allowLegacy && Array.isArray(result.filesChanged) && result.filesChanged.every((item) => typeof item === 'string') && !sameList(result.filesChanged.map(normalizeRelative), changed)) failures.push(`result.filesChanged mismatch: expected ${changed.join(', ') || '<none>'}; got ${result.filesChanged.join(', ') || '<none>'}`);
      if (!allowLegacy && Array.isArray(result.filesChanged) && result.filesChanged.every(isPlainFileChange)) {
        const declared = result.filesChanged.map((item) => normalizeRelative(item.path));
        if (!sameList(declared, productChanged)) failures.push(`result.filesChanged[].path mismatch: expected ${productChanged.join(', ') || '<none>'}; got ${declared.join(', ') || '<none>'}`);
      }
    } catch (error) {
      failures.push(`result JSON parse failed: ${error.message}`);
    }
  }

  if (scopeViolations.length) failures.push(`scope violations: ${scopeViolations.join(', ')}`);
  if (forbiddenHits.length) failures.push(`forbidden pattern hits: ${forbiddenHits.map((hit) => `${hit.file}:${hit.pattern}`).join(', ')}`);
  if (Array.isArray(result?.scopeViolations) && result.scopeViolations.length) failures.push(`claude reported scope violations: ${result.scopeViolations.join(', ')}`);
  if (Array.isArray(result?.scopeDeviations) && result.scopeDeviations.length) failures.push(`claude reported scope deviations: ${result.scopeDeviations.join(', ')}`);
  if (Array.isArray(result?.forbiddenPatternHits) && result.forbiddenPatternHits.length) failures.push(`claude reported forbidden hits: ${result.forbiddenPatternHits.join(', ')}`);

  const report = { ok: failures.length === 0, mode: args['allow-legacy'] === true ? 'legacy' : 'canonical', changed, productChanged, scopeViolations, forbiddenHits, resultFile: resultRelative, failures };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (failures.length) process.exitCode = 1;
}

function snapshot(args) {
  const workspace = requireWorkspace(args.workspace);
  const namespace = namespaceFor(workspace, args['order-id']);
  ensureDirectoryChain(workspace, namespace);
  if (args.out === undefined || !path.isAbsolute(String(args.out))) throw new Error('--out must be an explicit absolute external custody path');
  const out = path.resolve(String(args.out));
  if (isWithin(workspace, out)) throw new Error('--out must be outside the workspace; in-workspace snapshots are unsafe controller custody');
  assertNoSymlinkComponents(path.parse(out).root, out);
  ensureDirectoryChain(path.parse(out).root, path.dirname(out));
  if (fs.existsSync(out)) throw new Error(`snapshot already exists: ${out}`);
  writeCustodySnapshot(out, snapshotWorkspace(workspace));
  process.stdout.write(`snapshot written: ${out}\n`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.command === 'snapshot') return snapshot(args);
  if (args.command === 'verify') return verify(args);
  process.stdout.write(usage());
  process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
