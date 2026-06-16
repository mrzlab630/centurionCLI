#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { validateDelegationResult } from '../../legion-contracts/lib/contracts.mjs';

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
  return `Usage:\n  node scripts/agy-order-guard.mjs snapshot --workspace <dir> --out <snapshot.json>\n  node scripts/agy-order-guard.mjs verify --workspace <dir> --before <snapshot.json> --allowed <path[,path]> --result <AGY_RESULT.json> [--forbidden <regex[,regex]>]\n`;
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
    if (entry.isDirectory()) files.push(...walkFiles(fullPath, root));
    else files.push(normalizeRelative(path.relative(root, fullPath)));
  }
  return files.sort();
}

function hashFile(file) {
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
  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function changedFiles(before, after) {
  const names = new Set([...Object.keys(before), ...Object.keys(after)]);
  return [...names].filter((name) => before[name] !== after[name]).sort();
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

function scanForbidden(workspace, files, patterns) {
  const compiled = compileForbidden(patterns);
  const hits = [];
  for (const file of files) {
    const fullPath = path.join(workspace, file);
    if (!fs.existsSync(fullPath)) continue;
    const text = fs.readFileSync(fullPath, 'utf8');
    for (const item of compiled) {
      if (item.re.test(text)) hits.push({ file, pattern: item.pattern });
    }
  }
  return hits;
}

function validateResultShape(result) {
  return validateDelegationResult(result, {
    acceptedOrderVersions: ['AGY_ORDER_V1'],
    actorLabel: 'agy',
    requireProofForDone: false,
    requirePassedProofForDone: false
  });
}

function verify(args) {
  const workspace = path.resolve(String(args.workspace || ''));
  const beforeFile = path.resolve(String(args.before || ''));
  const resultPath = normalizeRelative(String(args.result || 'AGY_RESULT.json'));
  const allowedPaths = [...new Set(splitList(args.allowed).concat(resultPath))];
  const forbidden = splitList(args.forbidden);

  if (!fs.existsSync(workspace)) throw new Error(`workspace not found: ${workspace}`);
  if (!fs.existsSync(beforeFile)) throw new Error(`snapshot not found: ${beforeFile}`);
  if (!allowedPaths.length) throw new Error('allowed paths are required');

  const before = readJson(beforeFile);
  const after = snapshotWorkspace(workspace);
  const changed = changedFiles(before, after);
  const scopeViolations = changed.filter((file) => !isAllowed(file, allowedPaths));
  const forbiddenHits = scanForbidden(workspace, changed.filter((file) => isAllowed(file, allowedPaths)), forbidden);
  const resultFullPath = path.join(workspace, resultPath);
  const failures = [];

  if (!fs.existsSync(resultFullPath)) failures.push(`missing result file: ${resultPath}`);
  let result = null;
  if (fs.existsSync(resultFullPath)) {
    try {
      result = readJson(resultFullPath);
      failures.push(...validateResultShape(result));
    } catch (error) {
      failures.push(`result JSON parse failed: ${error.message}`);
    }
  }

  if (scopeViolations.length) failures.push(`scope violations: ${scopeViolations.join(', ')}`);
  if (forbiddenHits.length) failures.push(`forbidden pattern hits: ${forbiddenHits.map((hit) => `${hit.file}:${hit.pattern}`).join(', ')}`);
  if (result?.scopeViolations?.length) failures.push(`agy reported scope violations: ${result.scopeViolations.join(', ')}`);
  if (result?.forbiddenPatternHits?.length) failures.push(`agy reported forbidden hits: ${result.forbiddenPatternHits.join(', ')}`);

  const report = { ok: failures.length === 0, changed, scopeViolations, forbiddenHits, resultFile: resultPath, failures };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (failures.length) process.exitCode = 1;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.command === 'snapshot') {
    const workspace = path.resolve(String(args.workspace || ''));
    const out = path.resolve(String(args.out || ''));
    if (!fs.existsSync(workspace)) throw new Error(`workspace not found: ${workspace}`);
    if (!out) throw new Error('--out is required');
    writeJson(out, snapshotWorkspace(workspace));
    process.stdout.write(`snapshot written: ${out}\n`);
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
