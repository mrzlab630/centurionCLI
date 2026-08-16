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
  stageDirectory,
  stageFileContent
} from '../../lib/transactional-install.mjs';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPO_ROOT = path.resolve(KIT_ROOT, '..', '..');
const SKILL_SOURCE = path.join(REPO_ROOT, 'skills', 'open-design-producer');
const BRIDGE_ROOT = path.join(REPO_ROOT, 'integrations', 'open-design-bridge');
const MCP_ENTRY = path.join(BRIDGE_ROOT, 'mcp-server', 'index.mjs');
const CONFIG_VERSION = 'CENTURION_OPEN_DESIGN_CONFIG_V1';

function parseArgs(argv) {
  const options = {
    agentsHome: process.env.AGENTS_HOME || path.join(os.homedir(), '.agents'),
    codexHome: process.env.CODEX_HOME || path.join(os.homedir(), '.codex'),
    dryRun: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--agents-home') options.agentsHome = path.resolve(argv[++index]);
    else if (arg === '--codex-home') options.codexHome = path.resolve(argv[++index]);
    else if (arg === '--dry-run') options.dryRun = true;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return options;
}

function registerMcp(codexHome) {
  const env = { ...process.env, CODEX_HOME: codexHome };
  const existing = spawnSync('codex', ['mcp', 'get', 'centurion-open-design'], { env, encoding: 'utf8' });
  if (existing.status === 0) {
    const removed = spawnSync('codex', ['mcp', 'remove', 'centurion-open-design'], { env, encoding: 'utf8' });
    if (removed.status !== 0) throw new Error(`failed to replace Codex MCP: ${removed.stderr || removed.stdout}`);
  }
  const added = spawnSync('codex', ['mcp', 'add', 'centurion-open-design', '--', process.execPath, MCP_ENTRY], { env, encoding: 'utf8' });
  if (added.status !== 0) throw new Error(`failed to register Codex MCP: ${added.stderr || added.stdout}`);
}

const options = parseArgs(process.argv.slice(2));
const skillTarget = path.join(options.agentsHome, 'skills', 'open-design-producer');
const bridgeConfigTarget = path.join(options.codexHome, 'centurion', 'open-design-bridge.json');
if (!options.dryRun) {
  const configSnapshot = snapshotFile(path.join(options.codexHome, 'config.toml'));
  const operations = [];
  try {
    operations.push(stageDirectory(SKILL_SOURCE, skillTarget, { skip: (name) => name === 'node_modules' }));
    operations.push(stageFileContent(`${JSON.stringify({ configVersion: CONFIG_VERSION, bridgeRoot: BRIDGE_ROOT }, null, 2)}\n`, bridgeConfigTarget, { mode: 0o644 }));
    commitTransaction(operations, () => registerMcp(options.codexHome));
  } catch (error) {
    discardStaged(operations);
    restoreFile(configSnapshot);
    throw error;
  }
}
process.stdout.write(`${JSON.stringify({
  dryRun: options.dryRun,
  skillTarget,
  bridgeConfigTarget,
  mcpEntry: MCP_ENTRY,
  mcpServer: 'centurion-open-design'
}, null, 2)}\n`);
