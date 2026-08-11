#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const SKILL_SOURCE = path.join(KIT_ROOT, 'skills');
const BUNDLE_SOURCE = path.join(KIT_ROOT, 'skill-bundles');
const RUNTIME_SOURCE = path.join(KIT_ROOT, 'runtime');
const OVERRIDES_SOURCE = path.join(KIT_ROOT, 'overrides');
const OPEN_DESIGN_SKILL_SOURCE = path.join(REPO_ROOT, 'skills', 'open-design-producer');
const OPEN_DESIGN_BRIDGE = path.join(REPO_ROOT, 'integrations', 'open-design-bridge');
const OPEN_DESIGN_CONFIG_VERSION = 'CENTURION_OPEN_DESIGN_CONFIG_V1';

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
  const normalized = source.split(path.sep).join('/');
  const executable = normalized.includes('/runtime/bin/') || (/\/scripts\/[^/]+\.(?:mjs|py|sh)$/.test(normalized));
  fs.chmodSync(destination, executable ? 0o755 : 0o644);
}

function isTransient(entryName) {
  return entryName === '__pycache__' || entryName === '.DS_Store' || entryName.endsWith('.pyc');
}

function copyTree(source, destination, dryRun) {
  if (!fs.existsSync(source)) throw new Error(`missing source directory: ${source}`);
  if (!dryRun) fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (isTransient(entry.name)) continue;
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
      if (isTransient(entry.name)) continue;
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(fullPath);
      else files.push(path.relative(root, fullPath));
    }
  }
  return files.sort();
}

function writeOpenDesignConfig(configTarget, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(path.dirname(configTarget), { recursive: true });
  fs.writeFileSync(configTarget, `${JSON.stringify({
    configVersion: OPEN_DESIGN_CONFIG_VERSION,
    bridgeRoot: OPEN_DESIGN_BRIDGE
  }, null, 2)}\n`);
}

function install(options) {
  const skillsTarget = path.join(options.hermesHome, 'skills');
  const bundlesTarget = path.join(options.hermesHome, 'skill-bundles');
  const runtimeBinTarget = path.join(options.hermesHome, 'bin');
  const openDesignSkillTarget = path.join(skillsTarget, 'autonomous-ai-agents', 'open-design-producer');
  const openDesignConfigTarget = path.join(options.hermesHome, 'centurion', 'open-design-bridge.json');
  const overrideSkillsSource = path.join(OVERRIDES_SOURCE, 'skills');
  const overrideSkillsTarget = path.join(options.hermesHome, 'skills');
  const skillFiles = listFiles(SKILL_SOURCE);
  const bundleFiles = listFiles(BUNDLE_SOURCE);
  const runtimeFiles = listFiles(RUNTIME_SOURCE);
  const openDesignSkillFiles = listFiles(OPEN_DESIGN_SKILL_SOURCE);
  const overrideSkillFiles = fs.existsSync(overrideSkillsSource) ? listFiles(overrideSkillsSource) : [];

  if (!fs.existsSync(path.join(OPEN_DESIGN_SKILL_SOURCE, 'SKILL.md'))) throw new Error(`missing Open Design skill: ${OPEN_DESIGN_SKILL_SOURCE}`);
  if (!fs.existsSync(path.join(OPEN_DESIGN_BRIDGE, 'bin', 'centurion-design.mjs'))) throw new Error(`missing Open Design bridge: ${OPEN_DESIGN_BRIDGE}`);

  copyTree(SKILL_SOURCE, skillsTarget, options.dryRun);
  if (!options.dryRun) fs.rmSync(openDesignSkillTarget, { recursive: true, force: true });
  copyTree(OPEN_DESIGN_SKILL_SOURCE, openDesignSkillTarget, options.dryRun);
  copyTree(BUNDLE_SOURCE, bundlesTarget, options.dryRun);
  copyTree(path.join(RUNTIME_SOURCE, 'bin'), runtimeBinTarget, options.dryRun);
  writeOpenDesignConfig(openDesignConfigTarget, options.dryRun);
  if (options.includeOverrides && overrideSkillFiles.length > 0) {
    copyTree(overrideSkillsSource, overrideSkillsTarget, options.dryRun);
  }

  return {
    dryRun: options.dryRun,
    includeOverrides: options.includeOverrides,
    hermesHome: options.hermesHome,
    copiedSkillsTo: skillsTarget,
    copiedOpenDesignSkillTo: openDesignSkillTarget,
    copiedBundlesTo: bundlesTarget,
    copiedRuntimeBinTo: runtimeBinTarget,
    openDesignConfigTarget,
    openDesignConfigVersion: OPEN_DESIGN_CONFIG_VERSION,
    openDesignConfigWritten: !options.dryRun,
    copiedOverrideSkillsTo: options.includeOverrides ? overrideSkillsTarget : null,
    skillFiles,
    openDesignSkillFiles,
    bundleFiles,
    runtimeFiles,
    overrideSkillFiles: options.includeOverrides ? overrideSkillFiles : [],
    changedSurfaces: options.includeOverrides ? ['skills', 'skill-bundles', 'runtime-bin', 'centurion-config', 'override-skills'] : ['skills', 'skill-bundles', 'runtime-bin', 'centurion-config'],
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
