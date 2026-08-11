#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CONFIG_VERSION = 'CENTURION_OPEN_DESIGN_CONFIG_V1';
const CLI_RELATIVE_PATH = path.join('bin', 'centurion-design.mjs');
const scriptDir = path.dirname(fileURLToPath(import.meta.url));

function absolute(value) {
  return path.resolve(String(value));
}

function cliFromBridgeRoot(bridgeRoot) {
  return path.join(absolute(bridgeRoot), CLI_RELATIVE_PATH);
}

function usableCli(cliPath) {
  return fs.existsSync(cliPath) && fs.statSync(cliPath).isFile();
}

function configCandidates() {
  const home = os.homedir();
  const roots = [
    process.env.CLAUDE_HOME || path.join(home, '.claude'),
    process.env.HERMES_HOME || path.join(home, '.hermes')
  ];
  return [...new Set(roots.map((root) => path.join(absolute(root), 'centurion', 'open-design-bridge.json')))];
}

function readConfig(configPath, issues) {
  if (!fs.existsSync(configPath)) return null;
  try {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    if (config.configVersion !== CONFIG_VERSION) {
      issues.push(`${configPath}: unsupported configVersion`);
      return null;
    }
    if (typeof config.bridgeRoot !== 'string' || !path.isAbsolute(config.bridgeRoot)) {
      issues.push(`${configPath}: bridgeRoot must be an absolute path`);
      return null;
    }
    return config;
  } catch (error) {
    issues.push(`${configPath}: ${error.message}`);
    return null;
  }
}

function resolveCli() {
  const issues = [];
  const directCli = process.env.CENTURION_DESIGN_CLI;
  if (directCli) {
    const cliPath = absolute(directCli);
    if (usableCli(cliPath)) return { source: 'CENTURION_DESIGN_CLI', cliPath, bridgeRoot: path.dirname(path.dirname(cliPath)), configPath: null, issues };
    issues.push(`CENTURION_DESIGN_CLI does not point to a file: ${cliPath}`);
  }

  const bridgeCandidates = [
    ['CENTURION_OPEN_DESIGN_BRIDGE', process.env.CENTURION_OPEN_DESIGN_BRIDGE],
    ['CENTURION_REPO_ROOT', process.env.CENTURION_REPO_ROOT && path.join(process.env.CENTURION_REPO_ROOT, 'integrations', 'open-design-bridge')]
  ];
  for (const [source, bridgeRoot] of bridgeCandidates) {
    if (!bridgeRoot) continue;
    const cliPath = cliFromBridgeRoot(bridgeRoot);
    if (usableCli(cliPath)) return { source, cliPath, bridgeRoot: absolute(bridgeRoot), configPath: null, issues };
    issues.push(`${source} bridge CLI not found: ${cliPath}`);
  }

  for (const configPath of configCandidates()) {
    const config = readConfig(configPath, issues);
    if (!config) continue;
    const cliPath = cliFromBridgeRoot(config.bridgeRoot);
    if (usableCli(cliPath)) return { source: 'harness-config', cliPath, bridgeRoot: config.bridgeRoot, configPath, issues };
    issues.push(`${configPath}: bridge CLI not found: ${cliPath}`);
  }

  const sourceBridgeRoot = path.resolve(scriptDir, '..', '..', '..', 'integrations', 'open-design-bridge');
  const sourceCli = cliFromBridgeRoot(sourceBridgeRoot);
  if (usableCli(sourceCli)) return { source: 'source-repository', cliPath: sourceCli, bridgeRoot: sourceBridgeRoot, configPath: null, issues };
  issues.push(`source repository bridge CLI not found: ${sourceCli}`);

  throw new Error(`Open Design bridge CLI was not found. ${issues.join(' | ')}`);
}

function main() {
  const args = process.argv.slice(2);
  const printCli = args.includes('--print-cli');
  if (printCli && args.length !== 1) throw new Error('--print-cli cannot be combined with bridge arguments');

  const resolved = resolveCli();
  if (printCli) {
    process.stdout.write(`${JSON.stringify({ configVersion: CONFIG_VERSION, ...resolved }, null, 2)}\n`);
    return;
  }

  const result = spawnSync(process.execPath, [resolved.cliPath, ...args], {
    env: process.env,
    stdio: 'inherit'
  });
  if (result.error) throw result.error;
  if (result.signal) throw new Error(`Open Design bridge terminated by signal ${result.signal}`);
  process.exitCode = result.status ?? 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
