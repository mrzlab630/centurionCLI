#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');

function serenaMcpDefinition() {
  return {
    command: 'uvx',
    args: [
      '-p',
      '3.13',
      'serena-agent',
      'start-mcp-server',
      '--project-from-cwd',
      '--context',
      'codex',
      '--enable-web-dashboard',
      'false',
      '--open-web-dashboard',
      'false'
    ]
  };
}

function parseArgs(argv) {
  const options = {
    target: path.join(os.homedir(), '.gemini', 'antigravity'),
    cliTarget: path.join(os.homedir(), '.gemini', 'antigravity-cli'),
    installCliPlugin: true,
    installWithAgy: true,
    workspaceAgent: '',
    mcpConfig: '',
    registerMcp: false,
    dryRun: false
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--target') options.target = path.resolve(argv[++index]);
    else if (arg === '--cli-target') options.cliTarget = path.resolve(argv[++index]);
    else if (arg === '--no-cli-plugin') options.installCliPlugin = false;
    else if (arg === '--skip-agy-install') options.installWithAgy = false;
    else if (arg === '--workspace-agent') options.workspaceAgent = path.resolve(argv[++index]);
    else if (arg === '--mcp-config') options.mcpConfig = path.resolve(argv[++index]);
    else if (arg === '--register-mcp') options.registerMcp = true;
    else if (arg === '--dry-run') options.dryRun = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }

  if (!options.mcpConfig) options.mcpConfig = path.join(options.target, 'mcp_config.json');
  return options;
}

function usage() {
  return `Usage: node installer/install.mjs [options]\n\nOptions:\n  --target <dir>            Antigravity IDE config directory. Default: ~/.gemini/antigravity\n  --cli-target <dir>        Antigravity CLI config directory. Default: ~/.gemini/antigravity-cli\n  --no-cli-plugin           Do not install the agy CLI plugin\n  --skip-agy-install        Copy CLI plugin files but do not call agy plugin install\n  --workspace-agent <dir>   Optional workspace .agent directory to install/update\n  --mcp-config <file>       IDE MCP config file to update. Default: <target>/mcp_config.json\n  --register-mcp            Also call antigravity-ide --add-mcp when available\n  --dry-run                 Print planned changes without writing\n`;
}

function copyFile(source, destination, dryRun) {
  if (dryRun) return;
  const extension = path.extname(source);
  if (['.md', '.json', '.mjs'].includes(extension)) {
    const legacyKitRoot = '/home/mrz/projects/al/centurionCLI/cohors-prima/integrations/antigravity-legion-kit';
    const content = fs.readFileSync(source, 'utf8')
      .replaceAll(legacyKitRoot, KIT_ROOT)
      .replaceAll('/home/mrz', os.homedir());
    fs.writeFileSync(destination, content);
  } else {
    fs.copyFileSync(source, destination);
  }
}

function copyDirectory(source, destination, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) copyDirectory(sourcePath, destinationPath, dryRun);
    else copyFile(sourcePath, destinationPath, dryRun);
  }
}

function readJson(file) {
  if (!fs.existsSync(file)) return {};
  const text = fs.readFileSync(file, 'utf8');
  if (!text.trim()) return {};
  return JSON.parse(text);
}

function writeJson(file, data, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`);
}

function ensureMcpConfig(file, dryRun) {
  const config = readJson(file);
  config.mcpServers ||= {};
  config.mcpServers['centurion-legion'] = {
    command: 'node',
    args: [path.join(KIT_ROOT, 'mcp-server', 'index.mjs')],
    env: {
      CENTURION_AGENT_ROOT: path.join(KIT_ROOT, 'agent'),
      CENTURION_SKILL_ROOT: path.join(os.homedir(), '.agents', 'skills')
    }
  };
  config.mcpServers.serena = serenaMcpDefinition();
  writeJson(file, config, dryRun);
  return config.mcpServers['centurion-legion'];
}

function copyTree(source, destination, dryRun) {
  if (dryRun) return;
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) copyTree(sourcePath, destinationPath, dryRun);
    else copyFile(sourcePath, destinationPath, dryRun);
  }
}

function ensureImportManifest(cliTarget, dryRun) {
  const manifestFile = path.join(cliTarget, 'import_manifest.json');
  const manifest = readJson(manifestFile);
  manifest.imports = Array.isArray(manifest.imports) ? manifest.imports : [];
  const existing = manifest.imports.find((entry) => entry.name === 'centurion-legion');
  const record = {
    name: 'centurion-legion',
    source: 'local-install',
    importedAt: existing?.importedAt || new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    components: ['skills', 'mcpServers']
  };
  manifest.imports = manifest.imports.filter((entry) => entry.name !== 'centurion-legion').concat(record);
  writeJson(manifestFile, manifest, dryRun);
  return { file: manifestFile, record };
}

function ensureCliPlugin(cliTarget, mcpDefinition, options) {
  const { dryRun, installWithAgy } = options;
  const sourcePlugin = path.join(KIT_ROOT, 'agy-plugin');
  const pluginTarget = path.join(cliTarget, 'plugins', 'centurion-legion');
  const sourceMcpConfig = readJson(path.join(sourcePlugin, 'mcp_config.json'));
  const pluginMcpServers = {
    ...(sourceMcpConfig.mcpServers || {}),
    serena: serenaMcpDefinition(),
    'centurion-legion': mcpDefinition
  };
  if (!dryRun) fs.rmSync(pluginTarget, { recursive: true, force: true });
  copyTree(sourcePlugin, pluginTarget, dryRun);
  writeJson(path.join(pluginTarget, 'mcp_config.json'), {
    mcpServers: pluginMcpServers
  }, dryRun);
  const manifest = installWithAgy ? null : ensureImportManifest(cliTarget, dryRun);
  const agyInstall = installWithAgyCli(pluginTarget, dryRun || !installWithAgy);
  const finalManifest = installWithAgy ? null : readImportManifestRecord(cliTarget, manifest);
  return {
    pluginDir: pluginTarget,
    manifest: finalManifest,
    agyInstall,
    components: ['skills', 'mcpServers']
  };
}

function readImportManifestRecord(cliTarget, fallback) {
  const manifestFile = path.join(cliTarget, 'import_manifest.json');
  const manifest = readJson(manifestFile);
  const record = Array.isArray(manifest.imports)
    ? manifest.imports.find((entry) => entry.name === 'centurion-legion')
    : null;
  return { file: manifestFile, record: record || fallback.record };
}

function installWithAgyCli(pluginTarget, dryRun) {
  if (dryRun) return { ok: null, skipped: true, message: 'dry-run' };
  const result = spawnSync('agy', ['plugin', 'install', pluginTarget], {
    cwd: KIT_ROOT,
    encoding: 'utf8',
    env: { ...process.env, AGY_CLI_DISABLE_AUTO_UPDATE: '1' }
  });
  if (result.error) return { ok: false, skipped: true, message: result.error.message };
  return {
    ok: result.status === 0,
    skipped: false,
    message: (result.stderr || result.stdout || `exit ${result.status}`).trim()
  };
}

function registerWithAntigravity(definition) {
  const payload = JSON.stringify({ name: 'centurion-legion', ...definition });
  const result = spawnSync('antigravity-ide', ['--add-mcp', payload], { encoding: 'utf8' });
  if (result.error) return { ok: false, message: result.error.message };
  return { ok: result.status === 0, message: result.stderr || result.stdout || `exit ${result.status}` };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }

  const targetAgent = path.join(options.target, 'agent');
  const sourceAgent = path.join(KIT_ROOT, 'agent');
  const mcpDefinition = ensureMcpConfig(options.mcpConfig, options.dryRun);
  copyDirectory(sourceAgent, targetAgent, options.dryRun);
  if (options.workspaceAgent) copyDirectory(sourceAgent, options.workspaceAgent, options.dryRun);
  const cliPlugin = options.installCliPlugin ? ensureCliPlugin(options.cliTarget, mcpDefinition, options) : null;

  const report = {
    dryRun: options.dryRun,
    copiedAgentPackTo: targetAgent,
    copiedWorkspaceAgentTo: options.workspaceAgent || null,
    mcpConfig: options.mcpConfig,
    mcpServer: mcpDefinition,
    agyCliPlugin: cliPlugin,
    registerMcp: null
  };

  if (options.registerMcp && !options.dryRun) {
    report.registerMcp = registerWithAntigravity(mcpDefinition);
  }

  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
