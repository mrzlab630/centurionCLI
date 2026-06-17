#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const SKILL_SOURCE = path.join(KIT_ROOT, 'skills');
const BUNDLE_SOURCE = path.join(KIT_ROOT, 'skill-bundles');
const OVERRIDES_SOURCE = path.join(KIT_ROOT, 'overrides');

function parseArgs(argv) {
  const options = {
    hermesHome: process.env.HERMES_HOME || path.join(os.homedir(), '.hermes'),
    dryRun: false,
    includeOverrides: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--hermes-home') options.hermesHome = path.resolve(argv[++index]);
    else if (arg === '--dry-run') options.dryRun = true;
    else if (arg === '--include-overrides') options.includeOverrides = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node installer/install.mjs [options]\n\nOptions:\n  --hermes-home <dir>   Hermes config root. Default: ~/.hermes\n  --dry-run            Print planned changes without writing\n  --include-overrides  Also install reviewed optional overrides from overrides/\n`;
}

function copyFile(source, destination, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(source, destination);
}

function copyTree(source, destination, dryRun) {
  if (!fs.existsSync(source)) throw new Error(`missing source directory: ${source}`);
  if (!dryRun) fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const src = path.join(source, entry.name);
    const dest = path.join(destination, entry.name);
    if (entry.isDirectory()) copyTree(src, dest, dryRun);
    else copyFile(src, dest, dryRun);
  }
}

function listFiles(root) {
  const files = [];
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(fullPath);
      else files.push(path.relative(root, fullPath));
    }
  }
  return files.sort();
}

function install(options) {
  const skillsTarget = path.join(options.hermesHome, 'skills');
  const bundlesTarget = path.join(options.hermesHome, 'skill-bundles');
  const overrideSkillsSource = path.join(OVERRIDES_SOURCE, 'skills');
  const overrideSkillsTarget = path.join(options.hermesHome, 'skills');
  const skillFiles = listFiles(SKILL_SOURCE);
  const bundleFiles = listFiles(BUNDLE_SOURCE);
  const overrideSkillFiles = fs.existsSync(overrideSkillsSource) ? listFiles(overrideSkillsSource) : [];

  copyTree(SKILL_SOURCE, skillsTarget, options.dryRun);
  copyTree(BUNDLE_SOURCE, bundlesTarget, options.dryRun);
  if (options.includeOverrides && overrideSkillFiles.length > 0) {
    copyTree(overrideSkillsSource, overrideSkillsTarget, options.dryRun);
  }

  return {
    dryRun: options.dryRun,
    includeOverrides: options.includeOverrides,
    hermesHome: options.hermesHome,
    copiedSkillsTo: skillsTarget,
    copiedBundlesTo: bundlesTarget,
    copiedOverrideSkillsTo: options.includeOverrides ? overrideSkillsTarget : null,
    skillFiles,
    bundleFiles,
    overrideSkillFiles: options.includeOverrides ? overrideSkillFiles : [],
    changedSurfaces: options.includeOverrides ? ['skills', 'skill-bundles', 'override-skills'] : ['skills', 'skill-bundles'],
    untouchedSurfaces: ['SOUL.md', 'config.yaml', 'plugins', 'hooks', 'mcp_servers']
  };
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
  } else {
    process.stdout.write(`${JSON.stringify(install(options), null, 2)}\n`);
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
