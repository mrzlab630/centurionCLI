#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import {
  commitTransaction,
  discardStaged,
  restoreFile,
  snapshotFile,
  stageFile,
  stageFileContent
} from '../../lib/transactional-install.mjs';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const SKILL_SOURCE = path.join(KIT_ROOT, 'skills');
const BUNDLE_SOURCE = path.join(KIT_ROOT, 'skill-bundles');
const RUNTIME_SOURCE = path.join(KIT_ROOT, 'runtime');
const OVERRIDES_SOURCE = path.join(KIT_ROOT, 'overrides');
const OPEN_DESIGN_SKILL_SOURCE = path.join(REPO_ROOT, 'skills', 'open-design-producer');
const OPEN_DESIGN_BRIDGE = path.join(REPO_ROOT, 'integrations', 'open-design-bridge');
const OPEN_DESIGN_CONFIG_VERSION = 'CENTURION_OPEN_DESIGN_CONFIG_V1';
const OPEN_DESIGN_MCP_ENTRY = path.join(OPEN_DESIGN_BRIDGE, 'mcp-server', 'index.mjs');

function parseArgs(argv) {
  const options = {
    hermesHome: process.env.HERMES_HOME || path.join(os.homedir(), '.hermes'),
    dryRun: false,
    includeOverrides: false,
    openDesignCliOnly: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--hermes-home') options.hermesHome = path.resolve(argv[++index]);
    else if (arg === '--dry-run') options.dryRun = true;
    else if (arg === '--include-overrides') options.includeOverrides = true;
    else if (arg === '--open-design-cli-only') options.openDesignCliOnly = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node installer/install.mjs [options]\n\nOptions:\n  --hermes-home <dir>       Hermes config root. Default: ~/.hermes\n  --dry-run                Print planned changes without writing\n  --include-overrides      Also install reviewed optional overrides from overrides/\n  --open-design-cli-only  Install the Open Design CLI surface without registering its MCP\n`;
}

function installedMode(source) {
  const normalized = source.split(path.sep).join('/');
  const executable = normalized.includes('/runtime/bin/') || (/\/scripts\/[^/]+\.(?:mjs|py|sh)$/.test(normalized));
  return executable ? 0o755 : 0o644;
}

function isTransient(entryName) {
  return entryName === '__pycache__' || entryName === '.DS_Store' || entryName.endsWith('.pyc');
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

function stageFiles(operations, sourceRoot, targetRoot, files) {
  for (const relative of files) {
    operations.push(stageFile(
      path.join(sourceRoot, relative),
      path.join(targetRoot, relative),
      { mode: installedMode(path.join(sourceRoot, relative)) }
    ));
  }
}

function registerOpenDesignMcp(options) {
  if (options.dryRun) return false;
  const env = { ...process.env, HERMES_HOME: options.hermesHome };
  const soulPath = path.join(options.hermesHome, 'SOUL.md');
  const soulSnapshot = snapshotFile(soulPath);
  const configSnapshot = snapshotFile(path.join(options.hermesHome, 'config.yaml'));
  try {
    const existing = spawnSync('hermes', ['mcp', 'remove', 'centurion-open-design'], { env, encoding: 'utf8', input: 'y\n' });
    if (existing.status !== 0 && !/not found|does not exist|no server/i.test(`${existing.stdout}${existing.stderr}`)) {
      throw new Error(`failed to replace Hermes MCP: ${existing.stderr || existing.stdout}`);
    }
    const added = spawnSync('hermes', [
      'mcp', 'add', 'centurion-open-design',
      '--connect-timeout', '10',
      '--command', process.execPath,
      '--args', OPEN_DESIGN_MCP_ENTRY
    ], { env, encoding: 'utf8', input: 'n\n' });
    if (added.status !== 0 || !/Saved 'centurion-open-design'/.test(added.stdout)) {
      throw new Error(`failed to register Hermes MCP: ${added.stderr || added.stdout}`);
    }
  } catch (error) {
    restoreFile(configSnapshot);
    restoreFile(soulSnapshot);
    throw error;
  } finally {
    if (!soulSnapshot.existed && fs.existsSync(soulPath)) fs.rmSync(soulPath, { force: true });
  }
  return true;
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

  let openDesignMcpRegistered = false;
  if (!options.dryRun) {
    const operations = [];
    const hermesConfigSnapshot = snapshotFile(path.join(options.hermesHome, 'config.yaml'));
    try {
      stageFiles(operations, SKILL_SOURCE, skillsTarget, skillFiles);
      stageFiles(operations, OPEN_DESIGN_SKILL_SOURCE, openDesignSkillTarget, openDesignSkillFiles);
      stageFiles(operations, BUNDLE_SOURCE, bundlesTarget, bundleFiles);
      stageFiles(operations, RUNTIME_SOURCE, options.hermesHome, runtimeFiles);
      if (!options.openDesignCliOnly) {
        operations.push(stageFileContent(`${JSON.stringify({
          configVersion: OPEN_DESIGN_CONFIG_VERSION,
          bridgeRoot: OPEN_DESIGN_BRIDGE
        }, null, 2)}\n`, openDesignConfigTarget, { mode: 0o644 }));
      }
      if (options.includeOverrides) {
        stageFiles(operations, overrideSkillsSource, overrideSkillsTarget, overrideSkillFiles);
      }
      commitTransaction(operations, () => {
        if (!options.openDesignCliOnly) openDesignMcpRegistered = registerOpenDesignMcp(options);
      });
    } catch (error) {
      discardStaged(operations);
      restoreFile(hermesConfigSnapshot);
      throw error;
    }
  }

  return {
    dryRun: options.dryRun,
    includeOverrides: options.includeOverrides,
    openDesignCliOnly: options.openDesignCliOnly,
    hermesHome: options.hermesHome,
    copiedSkillsTo: skillsTarget,
    copiedOpenDesignSkillTo: openDesignSkillTarget,
    copiedBundlesTo: bundlesTarget,
    copiedRuntimeBinTo: runtimeBinTarget,
    openDesignConfigTarget,
    openDesignConfigVersion: OPEN_DESIGN_CONFIG_VERSION,
    openDesignConfigWritten: !options.dryRun && !options.openDesignCliOnly,
    openDesignMcpEntry: OPEN_DESIGN_MCP_ENTRY,
    openDesignMcpRegistered,
    copiedOverrideSkillsTo: options.includeOverrides ? overrideSkillsTarget : null,
    skillFiles,
    openDesignSkillFiles,
    bundleFiles,
    runtimeFiles,
    overrideSkillFiles: options.includeOverrides ? overrideSkillFiles : [],
    changedSurfaces: [
      'skills', 'skill-bundles', 'runtime-bin',
      ...(!options.openDesignCliOnly ? ['centurion-config'] : []),
      ...(!options.openDesignCliOnly ? ['mcp-server'] : []),
      ...(options.includeOverrides ? ['override-skills'] : [])
    ],
    untouchedSurfaces: [
      'SOUL.md', 'plugins', 'hooks',
      ...(options.openDesignCliOnly ? ['config.yaml', 'mcp-servers', 'centurion-config'] : [])
    ]
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
