#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';

const claudeHome = path.resolve(process.env.CLAUDE_HOME || path.join(os.homedir(), '.claude'));
const configPath = path.join(claudeHome, 'centurion', 'open-design-bridge.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
if (config.configVersion !== 'CENTURION_OPEN_DESIGN_CONFIG_V1' || typeof config.bridgeRoot !== 'string' || !path.isAbsolute(config.bridgeRoot)) {
  throw new Error(`invalid Open Design bridge config: ${configPath}`);
}
const server = path.join(config.bridgeRoot, 'mcp-server', 'index.mjs');
if (!fs.existsSync(server)) throw new Error(`Open Design MCP server missing: ${server}`);
const child = spawn(process.execPath, [server], { stdio: 'inherit', env: process.env });
child.on('error', (error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exitCode = code ?? 1;
});
