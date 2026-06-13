#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const IGNORE_DIRS = new Set(['.git', 'node_modules', 'dist', 'build', 'coverage', '.venv', 'vendor', '.next']);
const TEXT_EXTENSIONS = new Set(['.md', '.mjs', '.js', '.cjs', '.json', '.yaml', '.yml', '.toml', '.sh', '.bash', '.py', '.ts', '.tsx', '.jsx', '.txt']);

const RULES = [
  { id: 'remote-shell', severity: 'blocker', pattern: /(?:curl|wget)\b[^\n|;&]*(?:\||&&)\s*(?:bash|sh|zsh)\b/i, reason: 'remote download piped to shell' },
  { id: 'powershell-iex', severity: 'blocker', pattern: /(?:Invoke-WebRequest|iwr|curl)\b[^\n|;&]*(?:\||;)\s*iex\b/i, reason: 'remote PowerShell execution' },
  { id: 'base64-shell', severity: 'blocker', pattern: /base64\s+(?:-d|--decode)[^\n|;&]*(?:\||&&)\s*(?:bash|sh|zsh|python|node)\b/i, reason: 'encoded payload execution' },
  { id: 'private-key', severity: 'blocker', pattern: /-----BEGIN (?:RSA |OPENSSH |EC |DSA |PRIVATE )?PRIVATE KEY-----/i, reason: 'private key material' },
  { id: 'destructive-root-rm', severity: 'blocker', pattern: /rm\s+-rf\s+(?:\/|~|\$HOME)(?:\s|$)/i, reason: 'destructive broad remove' },
  { id: 'ssh-key-access', severity: 'blocker', pattern: /(?:cat|cp|tar|zip|base64|python|node)\b[^\n]*(?:\.ssh|id_rsa|id_ed25519|known_hosts)/i, reason: 'SSH credential access' },
  { id: 'env-exfiltration', severity: 'blocker', pattern: /(?:curl|wget|nc|socat)\b[^\n]*(?:printenv|env\s|process\.env|\$[A-Z0-9_]*(?:TOKEN|SECRET|KEY|PASSWORD))/i, reason: 'possible environment exfiltration' },
  { id: 'sudo', severity: 'warning', pattern: /\bsudo\b/i, reason: 'privileged command requested' },
  { id: 'eval', severity: 'warning', pattern: /\b(?:eval|new Function)\s*\(/i, reason: 'dynamic code execution' },
  { id: 'broad-home-access', severity: 'warning', pattern: /(?:~\/|\$HOME\/|\/home\/)[^\n]*(?:\.config|\.claude|\.codex|\.ssh|\.aws|\.gnupg)/i, reason: 'broad private directory access' },
  { id: 'secret-like-token', severity: 'warning', pattern: /(?:ghp_|github_pat_|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})/i, reason: 'secret-like token' }
];

function parseArgs(argv) {
  const options = { target: '.', json: false, warnOnly: false, maxBytes: 1_000_000 };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--target') options.target = argv[++index];
    else if (arg === '--json') options.json = true;
    else if (arg === '--warn-only') options.warnOnly = true;
    else if (arg === '--max-bytes') options.maxBytes = Number(argv[++index]);
    else if (arg === '--help') options.help = true;
    else if (!arg.startsWith('--')) options.target = arg;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node scripts/external-skill-scan.mjs [target] [options]\n\nOptions:\n  --target <dir>    Skill/plugin directory to scan. Default: current directory\n  --json            Print JSON report\n  --warn-only       Exit 0 even when blockers are found\n  --max-bytes <n>   Max bytes per text file. Default: 1000000\n`;
}

function isTextFile(file) {
  const ext = path.extname(file).toLowerCase();
  return TEXT_EXTENSIONS.has(ext) || path.basename(file) === 'SKILL.md' || path.basename(file) === 'README.md';
}

function walk(root, directory = root) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && IGNORE_DIRS.has(entry.name)) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(root, full));
    else if (isTextFile(full)) files.push(path.relative(root, full).split(path.sep).join('/'));
  }
  return files.sort();
}

function lineNumber(text, index) {
  return text.slice(0, index).split('\n').length;
}

function scanPackageJson(root, report) {
  const file = path.join(root, 'package.json');
  if (!fs.existsSync(file)) return;
  try {
    const pkg = JSON.parse(fs.readFileSync(file, 'utf8'));
    const scripts = pkg.scripts || {};
    for (const name of ['preinstall', 'install', 'postinstall', 'prepare']) {
      if (scripts[name]) {
        report.findings.push({ severity: 'warning', rule: 'package-lifecycle-script', file: 'package.json', line: 1, reason: `package lifecycle script: ${name}` });
      }
    }
  } catch (error) {
    report.findings.push({ severity: 'warning', rule: 'package-json-parse', file: 'package.json', line: 1, reason: `package.json parse failed: ${error.message}` });
  }
}

function scan(options) {
  const root = path.resolve(options.target);
  if (!fs.existsSync(root)) throw new Error(`target not found: ${root}`);
  if (!fs.statSync(root).isDirectory()) throw new Error(`target must be a directory: ${root}`);

  const files = walk(root);
  const report = {
    ok: true,
    target: root,
    scannedFiles: files.length,
    blockers: 0,
    warnings: 0,
    findings: []
  };

  const hasSkill = fs.existsSync(path.join(root, 'SKILL.md')) || files.some((file) => file.endsWith('/SKILL.md'));
  const hasPlugin = fs.existsSync(path.join(root, '.claude-plugin', 'plugin.json'));
  if (!hasSkill && !hasPlugin) {
    report.findings.push({ severity: 'warning', rule: 'missing-skill-entrypoint', file: '.', line: 1, reason: 'no SKILL.md or .claude-plugin/plugin.json found' });
  }

  scanPackageJson(root, report);

  for (const file of files) {
    const full = path.join(root, file);
    const stat = fs.statSync(full);
    if (stat.size > options.maxBytes) {
      report.findings.push({ severity: 'warning', rule: 'large-file-skipped', file, line: 1, reason: `file exceeds max bytes: ${stat.size}` });
      continue;
    }
    const text = fs.readFileSync(full, 'utf8');
    for (const rule of RULES) {
      const match = rule.pattern.exec(text);
      if (match) {
        report.findings.push({ severity: rule.severity, rule: rule.id, file, line: lineNumber(text, match.index), reason: rule.reason });
      }
    }
  }

  report.blockers = report.findings.filter((finding) => finding.severity === 'blocker').length;
  report.warnings = report.findings.filter((finding) => finding.severity === 'warning').length;
  report.ok = report.blockers === 0;
  return report;
}

function printText(report) {
  process.stdout.write(`external-skill-scan: ${report.ok ? 'pass' : 'fail'}\n`);
  process.stdout.write(`target: ${report.target}\n`);
  process.stdout.write(`scanned files: ${report.scannedFiles}\n`);
  process.stdout.write(`blockers: ${report.blockers}\n`);
  process.stdout.write(`warnings: ${report.warnings}\n`);
  for (const finding of report.findings.slice(0, 50)) {
    process.stdout.write(`- ${finding.severity} ${finding.rule} ${finding.file}:${finding.line} ${finding.reason}\n`);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  const report = scan(options);
  if (options.json) process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  else printText(report);
  if (!report.ok && !options.warnOnly) process.exitCode = 1;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
