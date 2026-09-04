#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {
  isPlainObject,
  parseStrictJson,
  validateAgentResult,
  validateDelegationResult
} from '../legion-contracts/lib/contracts.mjs';
import {
  AGY_RESULT_FILE,
  AGY_SNAPSHOT_FILE,
  deriveControlPaths,
  deriveOrderIdFromControlPath,
  ensureControlNamespace,
  assertExternalCustodyPath,
  validateOrderId
} from '../lib/control-artifact-namespace.mjs';

const IGNORE_DIRS = new Set(['.git', 'node_modules', 'dist', 'build', 'coverage', '.venv', 'vendor']);

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
    } else {
      args._.push(token);
    }
  }
  return args;
}

function usage() {
  return `Usage:\n  node scripts/agy-order-guard.mjs snapshot --workspace <dir> --order-id <orderId> [--out .centurion/agents_results/<orderId>/AGY_SNAPSHOT.json]\n  node scripts/agy-order-guard.mjs verify --workspace <dir> --order-id <orderId> [--before .centurion/agents_results/<orderId>/AGY_SNAPSHOT.json] --allowed <path[,path]> [--result .centurion/agents_results/<orderId>/AGY_RESULT.json] [--forbidden <regex[,regex]>] [--allow-legacy]\n`;
}

function splitList(value) {
  if (!value || value === true) return [];
  return String(value).split(',').map((item) => item.trim()).filter(Boolean);
}

function normalizeRelative(file) {
  return file.split(path.sep).join('/').replace(/^\.\//, '');
}

function walkFiles(directory, root = directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && IGNORE_DIRS.has(entry.name)) continue;
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
  const files = walkFiles(workspace);
  const snapshot = {};
  for (const file of files) snapshot[file] = hashFile(path.join(workspace, file));
  return snapshot;
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
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
  writeJson(file, data);
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
  return parseStrictJson(fs.readFileSync(file, 'utf8'), `JSON file ${file}`);
}

function changedFiles(before, after) {
  const names = new Set([...Object.keys(before), ...Object.keys(after)]);
  return [...names].filter((name) => before[name] !== after[name]).sort();
}

function sameList(left, right) {
  const a = [...new Set(left)].sort();
  const b = [...new Set(right)].sort();
  return a.length === b.length && a.every((item, index) => item === b[index]);
}

function isAllowed(file, allowedPaths) {
  const normalized = normalizeRelative(file);
  return allowedPaths.some((allowed) => {
    const value = normalizeRelative(allowed).replace(/\/+$/, '');
    return normalized === value || normalized.startsWith(`${value}/`);
  });
}

function compileForbidden(patterns) {
  return patterns.map((pattern) => ({ pattern, re: new RegExp(pattern, 'i') }));
}

function resolveOrderId(args, candidates = []) {
  const explicitValue = args['order-id'] ?? args.orderId;
  const derived = [];
  for (const [value, fileName, label] of candidates) {
    if (value !== undefined) derived.push(deriveOrderIdFromControlPath(value, fileName, label));
  }
  if (explicitValue !== undefined) {
    const explicit = validateOrderId(explicitValue);
    if (derived.some((orderId) => orderId !== explicit)) throw new Error('orderId does not match the supplied control artifact path');
    return explicit;
  }
  if (!derived.length) throw new Error('--order-id is required (or derive it from a namespaced control path)');
  if (new Set(derived).size !== 1) throw new Error('control artifact paths must use the same orderId');
  return derived[0];
}

function rejectOutOfNamespaceControlEntries(paths, allowedPaths) {
  for (const value of allowedPaths) {
    const normalized = String(value).replace(/\\/g, '/').replace(/\/+$/, '');
    if (normalized === '.centurion/agents_results' || normalized.startsWith('.centurion/agents_results/')) {
      const expectedNamespace = paths.namespaceRelative;
      if (normalized !== expectedNamespace && !normalized.startsWith(`${expectedNamespace}/`)) {
        throw new Error('allowed control paths must stay inside the exact order namespace');
      }
    }
    const baseName = normalized.split('/').pop();
    if (baseName === AGY_RESULT_FILE && normalized !== paths.resultRelative) {
      throw new Error(`allowed path for ${AGY_RESULT_FILE} must be inside the exact order namespace`);
    }
    if (baseName === AGY_SNAPSHOT_FILE && normalized !== paths.snapshotRelative) {
      throw new Error(`allowed path for ${AGY_SNAPSHOT_FILE} must be inside the exact order namespace`);
    }
  }
}

function scanForbidden(workspace, files, patterns) {
  const compiled = compileForbidden(patterns);
  const hits = [];
  for (const file of files) {
    const fullPath = path.join(workspace, file);
    let stats;
    try {
      stats = fs.lstatSync(fullPath);
    } catch (error) {
      if (error.code === 'ENOENT') continue;
      throw error;
    }
    if (stats.isSymbolicLink()) throw new Error(`symlink component rejected: ${fullPath}`);
    const text = fs.readFileSync(fullPath, 'utf8');
    for (const item of compiled) {
      if (item.re.test(text)) hits.push({ file, pattern: item.pattern });
    }
  }
  return hits;
}

function validateCanonicalResult(result, orderId) {
  return validateAgentResult(result, {
    expectedOrderId: orderId,
    expectedExecutor: 'agy'
  });
}

function validateResultShape(result, { allowLegacy, orderId }) {
  if (!allowLegacy) return validateCanonicalResult(result, orderId);
  return validateDelegationResult(result, {
    acceptedOrderVersions: ['AGY_ORDER_V1'],
    actorLabel: 'agy',
    requireProofForDone: false,
    requirePassedProofForDone: false
  });
}

function verify(args) {
  const resultArg = args.result === undefined ? undefined : args.result;
  const beforeArg = args.before === undefined ? undefined : args.before;
  const orderId = resolveOrderId(args, [[resultArg, AGY_RESULT_FILE, 'result path']]);
  if (beforeArg === undefined) throw new Error('--before must be an explicit absolute external custody path');
  const paths = deriveControlPaths(String(args.workspace || ''), orderId, { resultPath: resultArg });
  paths.snapshotAbsolute = assertExternalCustodyPath(paths.workspace, beforeArg, 'snapshot path');
  if (paths.resultAbsolute === paths.snapshotAbsolute) {
    throw new Error('result and snapshot paths must not collide');
  }
  const beforeFile = paths.snapshotAbsolute;
  const resultPath = paths.resultRelative;
  const declaredAllowedPaths = splitList(args.allowed);
  rejectOutOfNamespaceControlEntries(paths, declaredAllowedPaths);
  const allowedPaths = [...new Set(declaredAllowedPaths.concat(resultPath))];
  const forbidden = splitList(args.forbidden);

  if (!fs.existsSync(beforeFile)) throw new Error(`snapshot custody file not found: ${beforeFile}`);
  if (!declaredAllowedPaths.length) throw new Error('allowed paths are required');

  const before = readCustodySnapshot(beforeFile);
  const after = snapshotWorkspace(paths.workspace);
  const changed = changedFiles(before, after);
  const productChanged = changed.filter((file) => file !== paths.resultRelative);
  const scopeViolations = changed.filter((file) => !isAllowed(file, allowedPaths));
  const forbiddenHits = scanForbidden(paths.workspace, changed.filter((file) => isAllowed(file, allowedPaths)), forbidden);
  const resultFullPath = paths.resultAbsolute;
  const failures = [];

  if (!fs.existsSync(resultFullPath)) failures.push(`missing result file: ${resultPath}`);
  let result = null;
  if (fs.existsSync(resultFullPath)) {
    try {
      result = readJson(resultFullPath);
      failures.push(...validateResultShape(result, {
        allowLegacy: args['allow-legacy'] === true,
        orderId
      }));
      if (!args['allow-legacy'] && Array.isArray(result.filesChanged) && result.filesChanged.every((item) => isPlainObject(item) && typeof item.path === 'string')) {
        const declared = result.filesChanged.map((item) => normalizeRelative(item.path));
        if (!sameList(declared, productChanged)) failures.push(`result.filesChanged[].path mismatch: expected ${productChanged.join(', ') || '<none>'}; got ${declared.join(', ') || '<none>'}`);
      }
    } catch (error) {
      failures.push(`result JSON parse failed: ${error.message}`);
    }
  }

  if (scopeViolations.length) failures.push(`scope violations: ${scopeViolations.join(', ')}`);
  if (forbiddenHits.length) failures.push(`forbidden pattern hits: ${forbiddenHits.map((hit) => `${hit.file}:${hit.pattern}`).join(', ')}`);
  if (result?.scopeDeviations?.length) failures.push(`agy reported scope deviations: ${result.scopeDeviations.join(', ')}`);
  if (result?.scopeViolations?.length) failures.push(`agy reported scope violations: ${result.scopeViolations.join(', ')}`);
  if (result?.forbiddenPatternHits?.length) failures.push(`agy reported forbidden hits: ${result.forbiddenPatternHits.join(', ')}`);

  const report = { ok: failures.length === 0, changed, productChanged, scopeViolations, forbiddenHits, resultFile: resultPath, failures };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (failures.length) process.exitCode = 1;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.command === 'snapshot') {
    const outArg = args.out === undefined ? undefined : args.out;
    if (outArg === undefined) throw new Error('--out must be an explicit absolute external custody path');
    const orderId = resolveOrderId(args);
    const paths = deriveControlPaths(String(args.workspace || ''), orderId);
    paths.snapshotAbsolute = assertExternalCustodyPath(paths.workspace, outArg, 'snapshot path');
    const snapshot = snapshotWorkspace(paths.workspace);
    writeCustodySnapshot(paths.snapshotAbsolute, snapshot);
    process.stdout.write(`snapshot written: ${paths.snapshotAbsolute}\n`);
    return;
  }

  if (args.command === 'verify') {
    verify(args);
    return;
  }

  process.stdout.write(usage());
  process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
