#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const DEFAULT_SKILL_LIMIT = 100_000;

function parseArgs(argv) {
  const options = {
    hermesHome: process.env.HERMES_HOME || path.join(os.homedir(), '.hermes'),
    skillLimit: DEFAULT_SKILL_LIMIT,
    json: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--hermes-home') options.hermesHome = path.resolve(argv[++index]);
    else if (arg === '--skill-limit') options.skillLimit = Number.parseInt(argv[++index], 10);
    else if (arg === '--json') options.json = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!Number.isInteger(options.skillLimit) || options.skillLimit <= 0) {
    throw new Error('--skill-limit must be a positive integer');
  }
  return options;
}

function usage() {
  return `Usage: node scripts/harness-audit.mjs [options]\n\nOptions:\n  --hermes-home <dir>  Hermes config root. Default: ~/.hermes\n  --skill-limit <n>    SKILL.md size warning limit. Default: 100000\n  --json               Print JSON only\n`;
}

function readTextIfExists(file) {
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
}

function lineOf(text, pattern) {
  const lines = text.split('\n');
  for (let index = 0; index < lines.length; index += 1) {
    if (pattern.test(lines[index])) return index + 1;
  }
  return null;
}

function walk(root, predicate) {
  if (!fs.existsSync(root)) return [];
  const files = [];
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(fullPath);
      else if (!predicate || predicate(fullPath)) files.push(fullPath);
    }
  }
  return files.sort();
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, encoding: 'utf8', timeout: 60_000 });
  return {
    command: [command, ...args].join(' '),
    status: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
    error: result.error ? result.error.message : ''
  };
}

function parseModelDefault(configText) {
  const match = configText.match(/^model:\s*\n(?:^[ \t]+[^\n]*\n)*?^[ \t]+default:\s*([^\n#]+)/m);
  return match ? match[1].trim().replace(/^['"]|['"]$/g, '') : null;
}

function detectEnabledNpxServers(configText) {
  const servers = [];
  const lines = configText.split('\n');
  let inMcp = false;
  let current = null;
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (/^mcp_servers:\s*$/.test(line)) {
      inMcp = true;
      continue;
    }
    if (!inMcp) continue;
    if (/^[^\s].+:/.test(line)) break;
    const serverMatch = line.match(/^  ([A-Za-z0-9_.-]+):\s*$/);
    if (serverMatch) {
      if (current) servers.push(current);
      current = {
        name: serverMatch[1],
        line: index + 1,
        command: null,
        args: [],
        enabled: null
      };
      continue;
    }
    if (!current) continue;
    const commandMatch = line.match(/^    command:\s*(.+?)\s*$/);
    if (commandMatch) current.command = commandMatch[1].replace(/^['"]|['"]$/g, '');
    const enabledMatch = line.match(/^    enabled:\s*(true|false)\s*$/);
    if (enabledMatch) current.enabled = enabledMatch[1] === 'true';
    const argMatch = line.match(/^    -\s*(.+?)\s*$/);
    if (argMatch) current.args.push(argMatch[1].replace(/^['"]|['"]$/g, ''));
  }
  if (current) servers.push(current);
  return servers.filter((server) => server.enabled && server.command === 'npx' && server.args.includes('-y'));
}

function hasRuntimeOverrideRule(soulText) {
  return /Runtime model evidence overrides stale profile summaries/i.test(soulText);
}

function collectOversizedSkills(hermesHome, limit) {
  const skillsRoot = path.join(hermesHome, 'skills');
  return walk(skillsRoot, (file) => path.basename(file) === 'SKILL.md')
    .map((file) => ({ file, bytes: fs.statSync(file).size }))
    .filter((entry) => entry.bytes > limit)
    .map((entry) => ({
      path: path.relative(hermesHome, entry.file),
      bytes: entry.bytes,
      limit
    }));
}

function audit(options) {
  const configPath = path.join(options.hermesHome, 'config.yaml');
  const soulPath = path.join(options.hermesHome, 'SOUL.md');
  const configText = readTextIfExists(configPath);
  const soulText = readTextIfExists(soulPath);
  const modelDefault = parseModelDefault(configText);
  const enabledNpxServers = detectEnabledNpxServers(configText);
  const oversizedSkills = collectOversizedSkills(options.hermesHome, options.skillLimit);
  const promptSize = run('hermes', ['prompt-size', '--json'], options.hermesHome);
  let promptModel = null;
  try {
    promptModel = promptSize.status === 0 ? JSON.parse(promptSize.stdout).model || null : null;
  } catch {
    promptModel = null;
  }

  const warnings = [];
  if (!configText) warnings.push({ id: 'missing-config', owner: 'aquila', proof: configPath });
  if (!soulText) warnings.push({ id: 'missing-soul', owner: 'aquila', proof: soulPath });
  if (modelDefault && promptModel && modelDefault !== promptModel) {
    warnings.push({
      id: 'model-report-mismatch',
      owner: 'aquila',
      proof: `config model.default=${modelDefault}; prompt-size model=${promptModel}`,
      recommendation: 'Check active session logs before treating this as failure.'
    });
  }
  if (!hasRuntimeOverrideRule(soulText)) {
    warnings.push({
      id: 'missing-runtime-model-override-rule',
      owner: 'aquila',
      proof: soulPath,
      recommendation: 'Add compact SOUL rule: runtime model evidence overrides stale profile summaries for the current session.'
    });
  }
  for (const server of enabledNpxServers) {
    warnings.push({
      id: 'enabled-npx-y-mcp',
      owner: 'security',
      proof: `${configPath}:${server.line}`,
      server: server.name,
      recommendation: 'Version-pinned npx reduces drift but remains registry execution; prefer local/pinned binaries when stability or supply-chain risk matters.'
    });
  }
  for (const skill of oversizedSkills) {
    warnings.push({
      id: 'oversized-skill',
      owner: 'context-optimizer',
      proof: `${skill.path} ${skill.bytes} bytes > ${skill.limit}`,
      recommendation: 'Move long examples/procedures into references/ and keep SKILL.md as trigger/checklist/router.'
    });
  }

  return {
    ok: warnings.length === 0,
    hermesHome: options.hermesHome,
    checks: {
      configPath,
      soulPath,
      modelDefault,
      promptModel,
      modelDefaultLine: configText ? lineOf(configText, /^  default:/) : null,
      runtimeOverrideRule: hasRuntimeOverrideRule(soulText),
      enabledNpxMcpCount: enabledNpxServers.length,
      oversizedSkillCount: oversizedSkills.length,
      promptSizeCommand: promptSize.command,
      promptSizeExitCode: promptSize.status
    },
    enabledNpxServers: enabledNpxServers.map((server) => ({
      name: server.name,
      line: server.line,
      package: server.args.find((arg) => arg !== '-y') || null
    })),
    oversizedSkills,
    warnings
  };
}

function printHuman(report) {
  process.stdout.write(`Hermes harness audit: ${report.ok ? 'pass' : 'warn'}\n`);
  process.stdout.write(`Hermes home: ${report.hermesHome}\n`);
  process.stdout.write(`Model: config=${report.checks.modelDefault || 'unknown'} prompt-size=${report.checks.promptModel || 'unknown'}\n`);
  process.stdout.write(`Runtime model override rule: ${report.checks.runtimeOverrideRule ? 'present' : 'missing'}\n`);
  process.stdout.write(`Enabled npx -y MCP servers: ${report.checks.enabledNpxMcpCount}\n`);
  process.stdout.write(`Oversized SKILL.md files: ${report.checks.oversizedSkillCount}\n`);
  if (report.warnings.length > 0) {
    process.stdout.write('\nWarnings:\n');
    for (const warning of report.warnings) {
      process.stdout.write(`- ${warning.id} owner=${warning.owner} proof=${warning.proof}\n`);
    }
  }
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
  } else {
    const report = audit(options);
    if (options.json) process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    else printHuman(report);
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
