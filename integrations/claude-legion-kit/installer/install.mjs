#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import {
  commitTransaction,
  discardStaged,
  stageDirectory,
  stageFileContent
} from '../../lib/transactional-install.mjs';

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

function canonicalSkills(skillsTarget) {
  const copied = [];
  for (const entry of fs.readdirSync(CANONICAL_SKILLS, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const source = path.join(CANONICAL_SKILLS, entry.name);
    if (!fs.existsSync(path.join(source, 'SKILL.md'))) continue;
    copied.push({ name: entry.name, source, target: path.join(skillsTarget, entry.name) });
  }
  return copied.sort((left, right) => left.name.localeCompare(right.name));
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

  const skillEntries = options.syncSkills ? canonicalSkills(skillsTarget) : [];
  const syncedSkills = skillEntries.map((entry) => entry.name);
  let validation = { ok: null, skipped: true };
  if (!options.dryRun) {
    const operations = [];
    try {
      const stagedPlugin = stageDirectory(path.join(KIT_ROOT, 'plugin'), pluginTarget);
      operations.push(stagedPlugin);
      for (const entry of skillEntries) operations.push(stageDirectory(entry.source, entry.target));
      if (options.syncSkills) {
        operations.push(stageFileContent(`${JSON.stringify({
          configVersion: OPEN_DESIGN_CONFIG_VERSION,
          bridgeRoot: OPEN_DESIGN_BRIDGE
        }, null, 2)}\n`, openDesignConfigTarget, { mode: 0o644 }));
      }
      validation = validatePlugin(stagedPlugin.staged);
      if (!validation.ok) throw new Error(`Claude plugin validation failed: ${validation.output}`);
      commitTransaction(operations);
    } catch (error) {
      discardStaged(operations);
      throw error;
    }
  }

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
    openDesignMcpTarget: path.join(pluginTarget, '.mcp.json'),
    validation
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
