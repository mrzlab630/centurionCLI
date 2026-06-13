#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const DEFAULT_VIEWPORTS = [320, 768, 1440, 1920];
const DEFAULT_STATES = ['loading', 'empty', 'error', 'success'];
const DEFAULT_CHECKS = ['console-errors', 'hydration', 'a11y', 'responsive', 'dark-mode', 'keyboard', 'performance'];

function parseArgs(argv) {
  const options = {
    workspace: process.cwd(),
    baseUrl: null,
    maxPages: 20,
    viewports: DEFAULT_VIEWPORTS,
    states: DEFAULT_STATES,
    checks: DEFAULT_CHECKS,
    json: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--workspace') options.workspace = path.resolve(argv[++index]);
    else if (arg === '--base-url') options.baseUrl = argv[++index];
    else if (arg === '--max-pages') options.maxPages = Number(argv[++index]);
    else if (arg === '--viewports') options.viewports = argv[++index].split(',').map((value) => Number(value.trim())).filter(Boolean);
    else if (arg === '--states') options.states = argv[++index].split(',').map((value) => value.trim()).filter(Boolean);
    else if (arg === '--checks') options.checks = argv[++index].split(',').map((value) => value.trim()).filter(Boolean);
    else if (arg === '--json') options.json = true;
    else if (arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function usage() {
  return `Usage: node scripts/frontend-sweep-plan.mjs --base-url <url> [options]\n\nOptions:\n  --workspace <dir>       Project root. Default: current directory\n  --base-url <url>        Running app URL to crawl/audit\n  --max-pages <n>         Max pages for DFS plan. Default: 20\n  --viewports <csv>       Widths to test. Default: 320,768,1440,1920\n  --states <csv>          States to verify. Default: loading,empty,error,success\n  --checks <csv>          Checks to include\n  --json                  Print JSON only\n`;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function detectFramework(workspace) {
  const pkgPath = path.join(workspace, 'package.json');
  if (!fs.existsSync(pkgPath)) return { framework: 'unknown', packageManager: 'unknown', scripts: {} };
  const pkg = readJson(pkgPath);
  const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
  const scripts = pkg.scripts || {};
  const has = (name) => Object.prototype.hasOwnProperty.call(deps, name);
  let framework = 'unknown';
  if (has('next')) framework = 'next';
  else if (has('@vitejs/plugin-react') || (has('vite') && has('react'))) framework = 'react-vite';
  else if (has('react')) framework = 'react';
  else if (has('vite')) framework = 'vite';
  else if (has('nuxt') || has('vue')) framework = 'vue-nuxt';
  else if (has('@sveltejs/kit') || has('svelte')) framework = 'sveltekit';
  else if (has('astro')) framework = 'astro';
  else if (has('@angular/core')) framework = 'angular';

  let packageManager = 'npm';
  if (fs.existsSync(path.join(workspace, 'pnpm-lock.yaml'))) packageManager = 'pnpm';
  else if (fs.existsSync(path.join(workspace, 'yarn.lock'))) packageManager = 'yarn';
  return { framework, packageManager, scripts };
}

function commandFor(packageManager, script) {
  if (packageManager === 'pnpm') return `pnpm ${script}`;
  if (packageManager === 'yarn') return `yarn ${script}`;
  return `npm run ${script}`;
}

function buildPlan(options) {
  const workspace = path.resolve(options.workspace);
  if (!fs.existsSync(workspace)) throw new Error(`workspace not found: ${workspace}`);
  const detected = detectFramework(workspace);
  const commands = [];
  if (detected.scripts.lint) commands.push({ phase: 'static', command: commandFor(detected.packageManager, 'lint') });
  if (detected.scripts.test) commands.push({ phase: 'unit', command: commandFor(detected.packageManager, 'test') });
  if (detected.scripts.build) commands.push({ phase: 'build', command: commandFor(detected.packageManager, 'build') });
  commands.push({ phase: 'browser-audit', command: 'npx playwright test', note: 'Use existing Playwright suite when present; otherwise create a temporary audit spec in an allowed path.' });

  return {
    owner: 'TESTER',
    handoffs: {
      fixes: 'PICTOR',
      uxAmbiguity: 'AEDILIS',
      copyIssues: 'NOMENCLATOR',
      seoIssues: 'INDAGATOR',
      securityFindings: 'GUARDIAN'
    },
    workspace,
    baseUrl: options.baseUrl,
    detected,
    crawl: {
      strategy: 'dfs-link-graph',
      maxPages: options.maxPages,
      start: options.baseUrl || '<required-running-app-url>'
    },
    viewports: options.viewports,
    states: options.states,
    checks: options.checks,
    evidence: [
      'per-page pass/fail table',
      'viewport screenshots or screenshot paths for changed/failed screens',
      'console error summary',
      'accessibility violations with selectors',
      'hydration/runtime error summary',
      'remaining risks and skipped checks'
    ],
    rejectIf: [
      'horizontal scroll at 320px',
      'text overlap or clipped primary controls',
      'uncaught console errors on primary flow',
      'critical axe violation on reachable page',
      'missing loading/error/empty/success state for touched workflow',
      'proof command unavailable without documented blocker'
    ],
    commands
  };
}

function printText(plan) {
  process.stdout.write(`frontend-sweep-plan: ${plan.detected.framework}\n`);
  process.stdout.write(`owner: ${plan.owner}\n`);
  process.stdout.write(`workspace: ${plan.workspace}\n`);
  process.stdout.write(`baseUrl: ${plan.baseUrl || '<required>'}\n`);
  process.stdout.write(`viewports: ${plan.viewports.join(', ')}\n`);
  process.stdout.write(`checks: ${plan.checks.join(', ')}\n`);
  process.stdout.write('commands:\n');
  for (const item of plan.commands) process.stdout.write(`- ${item.phase}: ${item.command}${item.note ? ` (${item.note})` : ''}\n`);
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  const plan = buildPlan(options);
  if (options.json) process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
  else printText(plan);
  if (!options.baseUrl) process.exitCode = 2;
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
