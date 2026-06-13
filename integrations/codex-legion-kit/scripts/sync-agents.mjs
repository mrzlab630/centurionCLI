#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const CANONICAL_SKILLS = path.join(REPO_ROOT, 'skills');
const EXPECTED = [
  'aedilis','aleator','architect','artifex','augur','capabilities','censor','coder','context-optimizer','documenter','error-handler','evocate-ad-opus','git-master','glossator','haruspex','indagator','ludifex','mercator','nomenclator','orator','orchestrator','pictor','planner','pontifex','praeco','praemonitor','prompt-engineer','quaestor','refactorer','researcher','reviewer','security','sicarius','skill-quartermaster','tabularius','tester','velites'
];

const IGNORED_GENERATED_DIRS = new Set([
  '.git',
  '.next',
  '.venv',
  'build',
  'coverage',
  'dist',
  'node_modules',
  'reports',
  'vendor'
]);

function parseArgs(argv) {
  const options = {
    agentsHome: process.env.AGENTS_HOME || path.join(os.homedir(), '.agents'),
    write: false,
    all: false,
    skills: [],
    json: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--agents-home') options.agentsHome = path.resolve(argv[++index]);
    else if (arg === '--write') options.write = true;
    else if (arg === '--all') options.all = true;
    else if (arg === '--skill') options.skills.push(argv[++index]);
    else if (arg === '--json') options.json = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node scripts/sync-agents.mjs [options]\n\nOptions:\n  --agents-home <dir>  Agent root parent. Default: ~/.agents\n  --skill <slug>       Limit to one skill; repeatable\n  --all                Consider all canonical Legion skills\n  --write              Apply sync. Without this, dry-run only\n  --json               Print JSON report\n`;
}

function normalizeSlash(value) {
  return value.split(path.sep).join('/');
}

function walkFiles(root, directory = root) {
  if (!fs.existsSync(root)) return [];
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (IGNORED_GENERATED_DIRS.has(entry.name)) continue;
      files.push(...walkFiles(root, full));
    }
    else files.push(normalizeSlash(path.relative(root, full)));
  }
  return files.sort();
}

function hashFile(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function compareTrees(source, target) {
  const sourceFiles = new Map(walkFiles(source).map((file) => [file, hashFile(path.join(source, file))]));
  const targetFiles = new Map(walkFiles(target).map((file) => [file, hashFile(path.join(target, file))]));
  const all = [...new Set([...sourceFiles.keys(), ...targetFiles.keys()])].sort();
  const mismatches = [];
  for (const file of all) {
    if (!sourceFiles.has(file)) mismatches.push({ file, reason: 'extra-active' });
    else if (!targetFiles.has(file)) mismatches.push({ file, reason: 'missing-active' });
    else if (sourceFiles.get(file) !== targetFiles.get(file)) mismatches.push({ file, reason: 'hash-mismatch' });
  }
  return mismatches;
}

function pruneTarget(target) {
  if (!fs.existsSync(target)) return;
  for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
    if (entry.isDirectory() && IGNORED_GENERATED_DIRS.has(entry.name)) continue;
    fs.rmSync(path.join(target, entry.name), { recursive: true, force: true });
  }
}

function copyTree(source, target) {
  fs.mkdirSync(target, { recursive: true });
  pruneTarget(target);
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (entry.isDirectory() && IGNORED_GENERATED_DIRS.has(entry.name)) continue;
    const src = path.join(source, entry.name);
    const dest = path.join(target, entry.name);
    if (entry.isDirectory()) copyTree(src, dest);
    else fs.copyFileSync(src, dest);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  const activeRoot = path.join(options.agentsHome, 'skills');
  const selected = options.skills.length ? options.skills : (options.all ? EXPECTED : EXPECTED);
  const report = { dryRun: !options.write, activeRoot, synced: [], unchanged: [], missingSource: [], drift: [] };

  for (const slug of selected) {
    if (!EXPECTED.includes(slug)) throw new Error(`unknown canonical skill: ${slug}`);
    const source = path.join(CANONICAL_SKILLS, slug);
    const target = path.join(activeRoot, slug);
    if (!fs.existsSync(path.join(source, 'SKILL.md'))) {
      report.missingSource.push(slug);
      continue;
    }
    const mismatches = compareTrees(source, target);
    if (!mismatches.length) {
      report.unchanged.push(slug);
      continue;
    }
    report.drift.push({ slug, total: mismatches.length, sample: mismatches.slice(0, 10) });
    if (options.write) {
      copyTree(source, target);
      report.synced.push(slug);
    }
  }

  if (options.json) process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  else {
    process.stdout.write(`sync-agents: ${options.write ? 'write' : 'dry-run'}\n`);
    process.stdout.write(`active root: ${activeRoot}\n`);
    process.stdout.write(`drift dirs: ${report.drift.length}\n`);
    process.stdout.write(`synced dirs: ${report.synced.length}\n`);
    for (const item of report.drift) process.stdout.write(`- ${item.slug}: ${item.total} changed files\n`);
  }
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
