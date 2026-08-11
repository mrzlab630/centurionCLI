#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const CANONICAL_SKILLS = path.join(REPO_ROOT, 'skills');
const OPEN_DESIGN_BRIDGE = path.join(REPO_ROOT, 'integrations', 'open-design-bridge');
const OPEN_DESIGN_CONFIG_VERSION = 'CENTURION_OPEN_DESIGN_CONFIG_V1';

function parseArgs(argv) {
  const options = {
    claudeHome: process.env.CLAUDE_HOME || path.join(os.homedir(), '.claude'),
    syncSkills: true,
    dryRun: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--claude-home') options.claudeHome = path.resolve(argv[++index]);
    else if (arg === '--no-skill-sync') options.syncSkills = false;
    else if (arg === '--dry-run') options.dryRun = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node installer/install.mjs [options]\n\nOptions:\n  --claude-home <dir>  Claude Code config root. Default: ~/.claude\n  --no-skill-sync     Install plugin only, do not sync canonical skills\n  --dry-run           Print planned changes without writing\n`;
}

function copyTree(source, destination, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const src = path.join(source, entry.name);
    const dest = path.join(destination, entry.name);
    if (entry.isDirectory()) copyTree(src, dest, dryRun);
    else fs.copyFileSync(src, dest);
  }
}

function syncCanonicalSkills(skillsTarget, dryRun) {
  const copied = [];
  for (const entry of fs.readdirSync(CANONICAL_SKILLS, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const source = path.join(CANONICAL_SKILLS, entry.name);
    if (!fs.existsSync(path.join(source, 'SKILL.md'))) continue;
    const target = path.join(skillsTarget, entry.name);
    if (!dryRun) fs.rmSync(target, { recursive: true, force: true });
    copyTree(source, target, dryRun);
    copied.push(entry.name);
  }
  return copied.sort();
}

function validatePlugin(pluginDir) {
  const result = spawnSync('claude', ['plugin', 'validate', pluginDir, '--strict'], {
    encoding: 'utf8',
    env: { ...process.env }
  });
  return {
    ok: result.status === 0,
    status: result.status,
    output: `${result.stdout || ''}${result.stderr || ''}`.trim()
  };
}

function writeOpenDesignConfig(configTarget, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(path.dirname(configTarget), { recursive: true });
  fs.writeFileSync(configTarget, `${JSON.stringify({
    configVersion: OPEN_DESIGN_CONFIG_VERSION,
    bridgeRoot: OPEN_DESIGN_BRIDGE
  }, null, 2)}\n`);
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  const skillsTarget = path.join(options.claudeHome, 'skills');
  const pluginTarget = path.join(skillsTarget, 'centurion-legion');
  const openDesignConfigTarget = path.join(options.claudeHome, 'centurion', 'open-design-bridge.json');

  if (!fs.existsSync(CANONICAL_SKILLS)) throw new Error(`canonical skills not found: ${CANONICAL_SKILLS}`);
  if (!fs.existsSync(path.join(OPEN_DESIGN_BRIDGE, 'bin', 'centurion-design.mjs'))) throw new Error(`Open Design bridge not found: ${OPEN_DESIGN_BRIDGE}`);

  if (!options.dryRun) fs.mkdirSync(skillsTarget, { recursive: true });
  if (!options.dryRun) fs.rmSync(pluginTarget, { recursive: true, force: true });
  copyTree(path.join(KIT_ROOT, 'plugin'), pluginTarget, options.dryRun);
  const syncedSkills = options.syncSkills ? syncCanonicalSkills(skillsTarget, options.dryRun) : [];
  if (options.syncSkills) writeOpenDesignConfig(openDesignConfigTarget, options.dryRun);
  const validation = options.dryRun ? { ok: null, skipped: true } : validatePlugin(pluginTarget);

  const report = {
    dryRun: options.dryRun,
    claudeHome: options.claudeHome,
    pluginTarget,
    canonicalSkills: CANONICAL_SKILLS,
    syncedSkillCount: syncedSkills.length,
    syncedSkills,
    sharedCapabilities: syncedSkills.includes('open-design-producer') ? ['open-design-producer'] : [],
    openDesignConfigTarget,
    openDesignConfigVersion: OPEN_DESIGN_CONFIG_VERSION,
    openDesignConfigWritten: options.syncSkills && !options.dryRun,
    validation
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (validation.ok === false) process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
