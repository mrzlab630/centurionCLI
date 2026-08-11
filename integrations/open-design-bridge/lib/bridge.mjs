import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { spawn, spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright-core';
import { normalizedRequest, RESULT_VERSION } from './contracts.mjs';

const MAX_CAPTURE_BYTES = 24 * 1024 * 1024;
const TERMINAL_RUN_STATUSES = new Set(['completed', 'succeeded', 'failed', 'cancelled']);

export async function runDesignRequest(rawRequest, options = {}) {
  const cwd = options.cwd ?? process.cwd();
  const env = options.env ?? process.env;
  const outputRoot = env.CENTURION_DESIGN_ROOT
    ? path.resolve(env.CENTURION_DESIGN_ROOT)
    : path.resolve(cwd, '.centurion', 'design');
  const request = normalizedRequest(rawRequest, { cwd, outputRoot });
  const staleStagingRemoved = sweepTransientRoot(outputRoot, '.staging', request.cleanup.stagingMaxAgeHours);
  const staleTrashRemoved = sweepTransientRoot(outputRoot, '.trash', request.cleanup.stagingMaxAgeHours);
  if (request.action === 'cleanup') {
    return runCleanupRequest(request, {
      env,
      outputRoot,
      resultPath: options.resultPath ?? null,
      staleStagingRemoved,
      staleTrashRemoved
    });
  }

  const warnings = [];
  const errors = [];
  const proof = [];
  const finalOutputDir = request.artifact.outputDir;
  let stagingDir = null;
  let executionRequest = null;

  let projectId = request.project.projectId;
  let conversationId = request.project.conversationId;
  let runId = null;
  let runInfo = null;
  let artifact = null;
  let screenshot = null;
  let daemonStarted = false;
  let executorExitCode = null;
  let runLogPath = null;
  let previousArtifactSha256 = null;
  let od = null;
  let cleanup = {
    policy: request.cleanup.onFailure,
    staleStagingRemoved,
    staleTrashRemoved,
    stagingDeleted: false,
    failedProjectDeleted: false,
    pending: false,
    preservedPath: null
  };

  try {
    assertOutputTargetsUnused(request);
    stagingDir = createStagingDir(outputRoot, request.requestId);
    executionRequest = {
      ...request,
      artifact: { ...request.artifact, outputDir: stagingDir }
    };
    od = resolveOdCommand(env);
    daemonStarted = await ensureDaemon(od, executionRequest, env, stagingDir);
    proof.push({ check: 'daemon', result: 'passed', summary: `Open Design reachable at ${request.daemon.url}` });

    if (request.action === 'create') {
      const created = await odJson(od, [
        'project', 'create',
        '--name', request.project.name,
        '--plugin', request.executor.plugin,
        '--inputs', JSON.stringify(request.executor.inputs),
        '--mode', 'design',
        '--json'
      ], executionRequest, env);
      projectId = created.project?.id;
      conversationId = created.conversationId ?? null;
      if (!projectId) throw new Error('Open Design project create returned no project.id');
    }

    if (request.action === 'revise') {
      const previousArtifact = await readProjectFileMaybe(od, projectId, request.artifact.entry, executionRequest, env);
      previousArtifactSha256 = previousArtifact
        ? crypto.createHash('sha256').update(previousArtifact).digest('hex')
        : null;
    }

    const prompt = buildProductionPrompt(request);
    const runArgs = [
      'run', 'start',
      '--project', projectId,
      '--plugin', request.executor.plugin,
      '--inputs', JSON.stringify(request.executor.inputs),
      '--grant-caps', request.executor.grantCapabilities.join(','),
      '--agent', request.executor.agent,
      '--message', prompt,
      '--json'
    ];
    if (conversationId) runArgs.push('--conversation', conversationId);
    if (request.executor.model) runArgs.push('--model', request.executor.model);
    const started = await odJson(od, runArgs, executionRequest, env);
    runId = started.runId;
    conversationId = started.conversationId ?? conversationId;
    if (!runId) throw new Error('Open Design run start returned no runId');

    const watched = await odCapture(od, ['run', 'watch', runId], executionRequest, env, request.executor.timeoutMs);
    executorExitCode = watched.code;
    runLogPath = path.join(stagingDir, 'open-design-events.ndjson');
    fs.writeFileSync(runLogPath, watched.stdout);
    if (watched.stderr.trim()) fs.writeFileSync(path.join(stagingDir, 'open-design-stderr.log'), watched.stderr);

    runInfo = await odJson(od, ['run', 'info', runId, '--json'], executionRequest, env, 30_000);
    if (!TERMINAL_RUN_STATUSES.has(runInfo.status)) {
      throw new Error(`Open Design run is not terminal after watch: status=${runInfo.status}`);
    }
    if (runInfo.status === 'cancelled') throw new Error('Open Design run was cancelled');
    if (!['completed', 'succeeded'].includes(runInfo.status)) {
      warnings.push(`Open Design run ended with status=${runInfo.status}${runInfo.error ? `: ${runInfo.error}` : ''}`);
    }

    artifact = await materializeProject(od, projectId, executionRequest, env);
    proof.push(...verifyHtmlArtifact(artifact.absolutePath));
    if (request.action === 'revise') {
      const changed = Boolean(previousArtifactSha256) && artifact.sha256 !== previousArtifactSha256;
      proof.push({
        check: 'revision-changed',
        result: changed ? 'passed' : 'failed',
        summary: changed ? 'artifact SHA-256 changed from the previous project state' : 'revision did not change the artifact SHA-256'
      });
    }

    if (request.screenshot.enabled) {
      screenshot = await captureScreenshot(artifact.absolutePath, executionRequest, env);
      proof.push({
        check: 'screenshot',
        result: 'passed',
        summary: `${screenshot.width}x${screenshot.height} PNG rendered in Chrome`
      });
    }

    const failedProof = proof.filter((entry) => entry.result !== 'passed');
    if (failedProof.length) errors.push(...failedProof.map((entry) => `${entry.check}: ${entry.summary}`));
    if (errors.length === 0) {
      promoteStaging(stagingDir, finalOutputDir);
      artifact = rebaseArtifact(artifact, stagingDir, finalOutputDir);
      screenshot = rebaseScreenshot(screenshot, stagingDir, finalOutputDir);
      runLogPath = rebasePath(runLogPath, stagingDir, finalOutputDir);
    }
  } catch (error) {
    errors.push(error.message);
  }

  if (errors.length > 0 && stagingDir) {
    cleanup = await cleanupFailedRun({
      cleanup,
      request,
      executionRequest,
      stagingDir,
      od,
      projectId,
      env,
      warnings
    });
    artifact = null;
    screenshot = null;
    runLogPath = cleanup.preservedPath
      ? path.join(cleanup.preservedPath, 'open-design-events.ndjson')
      : null;
  }

  const status = errors.length === 0 && artifact && (!request.screenshot.enabled || screenshot)
    ? 'done'
    : 'failed';
  return {
    resultVersion: RESULT_VERSION,
    requestId: request.requestId,
    status,
    action: request.action,
    projectId,
    conversationId,
    runId,
    revisionOf: request.project.previousResultPath,
    executor: {
      agent: request.executor.agent,
      model: request.executor.model,
      plugin: request.executor.plugin,
      runStatus: runInfo?.status ?? null,
      runExitCode: runInfo?.exitCode ?? executorExitCode,
      runError: runInfo?.error ?? null
    },
    artifact,
    screenshot,
    proof,
    warnings,
    errors,
    cleanup,
    diagnostics: {
      daemonUrl: request.daemon.url,
      daemonStarted,
      outputDir: finalOutputDir,
      runLogPath
    }
  };
}

async function runCleanupRequest(request, options) {
  const errors = [];
  const warnings = [];
  const proof = [];
  const targetPath = path.resolve(request.artifact.outputDir);
  if (!isWithin(options.outputRoot, targetPath) || targetPath === path.resolve(options.outputRoot)) {
    errors.push(`cleanup target must be a child of CENTURION_DESIGN_ROOT: ${options.outputRoot}`);
  }
  if ([path.join(options.outputRoot, '.staging'), path.join(options.outputRoot, '.trash')]
    .some((reservedRoot) => targetPath === path.resolve(reservedRoot))) {
    errors.push('cleanup target cannot be a transient root directory');
  }
  if (options.resultPath && isWithin(targetPath, options.resultPath)) {
    errors.push('cleanup --result path must be outside the bundle being removed');
  }
  if (errors.length === 0) {
    try {
      assertRemovableDirectory(targetPath);
    } catch (error) {
      errors.push(error.message);
    }
  }

  const previous = request.project.previousResult;
  const projectId = previous?.projectId ?? null;
  let localAction = null;
  let trashPath = null;
  let projectDeleted = false;

  if (errors.length === 0 && request.cleanup.deleteProject) {
    if (!projectId) errors.push('previous result contains no projectId for project deletion');
    else {
      const scratch = createStagingDir(options.outputRoot, `${request.requestId}-cleanup`);
      try {
        const od = resolveOdCommand(options.env);
        const cleanupRequest = { ...request, artifact: { ...request.artifact, outputDir: scratch } };
        await ensureDaemon(od, cleanupRequest, options.env, scratch);
        const deleted = await odCapture(od, ['project', 'delete', projectId], cleanupRequest, options.env, 30_000);
        if (deleted.code !== 0) throw new Error(deleted.stderr.trim() || deleted.stdout.trim());
        projectDeleted = true;
        proof.push({ check: 'project-cleanup', result: 'passed', summary: `deleted Open Design project ${projectId}` });
      } catch (error) {
        errors.push(`Open Design project cleanup failed: ${error.message}`);
      } finally {
        try {
          fs.rmSync(scratch, { recursive: true, force: true });
        } catch (error) {
          warnings.push(`failed cleanup scratch removal: ${error.message}`);
        }
      }
    }
  }

  if (errors.length === 0) {
    try {
      if (!fs.existsSync(targetPath)) {
        warnings.push(`cleanup target already absent: ${targetPath}`);
        localAction = 'already-absent';
      } else if (request.cleanup.mode === 'trash') {
        const trashRoot = path.join(options.outputRoot, '.trash');
        fs.mkdirSync(trashRoot, { recursive: true });
        trashPath = path.join(trashRoot, `${Date.now()}-${crypto.randomUUID()}-${path.basename(targetPath)}`);
        fs.renameSync(targetPath, trashPath);
        const trashedAt = new Date();
        fs.utimesSync(trashPath, trashedAt, trashedAt);
        localAction = 'trashed';
      } else {
        fs.rmSync(targetPath, { recursive: true, force: true });
        localAction = 'deleted';
      }
      proof.push({ check: 'local-cleanup', result: 'passed', summary: `${localAction}: ${targetPath}` });
    } catch (error) {
      errors.push(`local bundle cleanup failed: ${error.message}`);
    }
  }

  return {
    resultVersion: RESULT_VERSION,
    requestId: request.requestId,
    status: errors.length ? 'failed' : 'done',
    action: 'cleanup',
    projectId,
    conversationId: previous?.conversationId ?? null,
    runId: null,
    revisionOf: request.project.previousResultPath,
    executor: null,
    artifact: null,
    screenshot: null,
    proof,
    warnings,
    errors,
    cleanup: {
      mode: request.cleanup.mode,
      targetPath,
      localAction,
      trashPath,
      projectDeleted,
      staleStagingRemoved: options.staleStagingRemoved,
      staleTrashRemoved: options.staleTrashRemoved,
      pending: false
    },
    diagnostics: { outputRoot: options.outputRoot }
  };
}

async function cleanupFailedRun({ cleanup, request, executionRequest, stagingDir, od, projectId, env, warnings }) {
  if (request.cleanup.onFailure === 'delete') {
    try {
      fs.rmSync(stagingDir, { recursive: true, force: true });
      cleanup.stagingDeleted = !fs.existsSync(stagingDir);
    } catch (error) {
      warnings.push(`failed staging cleanup: ${error.message}`);
      cleanup.stagingDeleted = !fs.existsSync(stagingDir);
      cleanup.pending = !cleanup.stagingDeleted;
      cleanup.preservedPath = cleanup.stagingDeleted ? null : stagingDir;
    }
    if (request.action === 'create' && projectId && request.cleanup.deleteFailedProject && od) {
      try {
        const deleted = await odCapture(od, ['project', 'delete', projectId], executionRequest, env, 30_000);
        if (deleted.code === 0) cleanup.failedProjectDeleted = true;
        else warnings.push(`failed Open Design project cleanup: ${deleted.stderr.trim() || deleted.stdout.trim()}`);
      } catch (error) {
        warnings.push(`failed Open Design project cleanup: ${error.message}`);
      }
    }
  } else {
    cleanup.pending = request.cleanup.onFailure === 'ask';
    cleanup.preservedPath = stagingDir;
  }
  return cleanup;
}

function createStagingDir(outputRoot, requestId) {
  const stagingRoot = path.join(outputRoot, '.staging');
  fs.mkdirSync(stagingRoot, { recursive: true });
  const safeId = String(requestId).replace(/[^A-Za-z0-9._-]/g, '-');
  return fs.mkdtempSync(path.join(stagingRoot, `${safeId}-`));
}

function promoteStaging(stagingDir, finalOutputDir) {
  fs.mkdirSync(path.dirname(finalOutputDir), { recursive: true });
  if (fs.existsSync(finalOutputDir)) {
    throw new Error(`output bundle appeared during execution; refusing to replace it: ${finalOutputDir}`);
  }
  fs.renameSync(stagingDir, finalOutputDir);
}

function rebaseArtifact(artifact, fromRoot, toRoot) {
  if (!artifact) return null;
  return {
    ...artifact,
    absolutePath: rebasePath(artifact.absolutePath, fromRoot, toRoot),
    outputDir: toRoot,
    files: artifact.files.map((file) => ({
      ...file,
      absolutePath: rebasePath(file.absolutePath, fromRoot, toRoot)
    }))
  };
}

function rebaseScreenshot(screenshot, fromRoot, toRoot) {
  return screenshot
    ? { ...screenshot, absolutePath: rebasePath(screenshot.absolutePath, fromRoot, toRoot) }
    : null;
}

function rebasePath(value, fromRoot, toRoot) {
  if (!value) return value;
  return path.join(toRoot, path.relative(fromRoot, value));
}

function sweepTransientRoot(outputRoot, directory, maxAgeHours) {
  const transientRoot = path.join(outputRoot, directory);
  if (!fs.existsSync(transientRoot)) return 0;
  const cutoff = Date.now() - (maxAgeHours * 60 * 60 * 1000);
  let removed = 0;
  for (const entry of fs.readdirSync(transientRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const target = path.join(transientRoot, entry.name);
    let stats;
    try {
      stats = fs.lstatSync(target);
    } catch (error) {
      if (error.code === 'ENOENT') continue;
      throw error;
    }
    if (stats.isSymbolicLink() || !stats.isDirectory() || stats.mtimeMs >= cutoff) continue;
    fs.rmSync(target, { recursive: true, force: true });
    removed += 1;
  }
  return removed;
}

function assertRemovableDirectory(targetPath) {
  let stats;
  try {
    stats = fs.lstatSync(targetPath);
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
  if (stats.isSymbolicLink()) throw new Error(`cleanup target must not be a symbolic link: ${targetPath}`);
  if (!stats.isDirectory()) throw new Error(`cleanup target must be a directory: ${targetPath}`);
}

function buildProductionPrompt(request) {
  const action = request.action === 'create'
    ? `Create the requested interface and write the canonical deliverable to ${request.artifact.entry}.`
    : `Inspect the current ${request.artifact.entry}, then revise that same artifact in place.`;
  return [
    'You are the Open Design production executor inside a CENTURION proof-first workflow.',
    action,
    `User brief: ${request.brief}`,
    `Target viewport: ${request.screenshot.viewport.width}x${request.screenshot.viewport.height}.`,
    'Return a working implementation, not a prose-only design.',
    'Keep the primary artifact directly renderable in Chrome.',
    'Preserve valid existing behavior during revisions unless the brief explicitly replaces it.',
    'Verify the artifact before finishing. Do not delete unrelated project files.'
  ].join('\n');
}

function resolveOdCommand(env) {
  if (env.CENTURION_OD_COMMAND_JSON) {
    const parsed = JSON.parse(env.CENTURION_OD_COMMAND_JSON);
    if (!Array.isArray(parsed) || !parsed.length || !parsed.every((item) => typeof item === 'string' && item.length > 0)) {
      throw new Error('CENTURION_OD_COMMAND_JSON must be a non-empty JSON string array');
    }
    return { command: parsed[0], prefix: parsed.slice(1) };
  }
  if (env.CENTURION_OD_ROOT) {
    const entry = path.join(path.resolve(env.CENTURION_OD_ROOT), 'apps', 'daemon', 'bin', 'od.mjs');
    if (!fs.existsSync(entry)) throw new Error(`Open Design CLI entry not found: ${entry}`);
    return { command: process.execPath, prefix: [entry] };
  }
  if (env.OD_BIN) {
    return { command: env.OD_NODE_BIN || process.execPath, prefix: [path.resolve(env.OD_BIN)] };
  }
  throw new Error('Open Design command is not configured; set CENTURION_OD_COMMAND_JSON, CENTURION_OD_ROOT, or OD_BIN');
}

async function ensureDaemon(od, request, env, outputDir) {
  const status = await odCapture(od, ['status', '--json'], request, env, 15_000);
  if (status.code === 0) return false;
  if (!request.daemon.ensureRunning) throw new Error(`Open Design daemon is unavailable at ${request.daemon.url}`);

  const daemonLog = fs.openSync(path.join(outputDir, 'open-design-daemon.log'), 'a');
  const url = new URL(request.daemon.url);
  const child = spawn(od.command, [
    ...od.prefix,
    '--no-open',
    '--host', url.hostname,
    '--port', url.port || '7456'
  ], {
    detached: true,
    stdio: ['ignore', daemonLog, daemonLog],
    env
  });
  fs.closeSync(daemonLog);
  child.unref();
  const deadline = Date.now() + request.daemon.startupTimeoutMs;
  while (Date.now() < deadline) {
    await delay(500);
    const probe = await odCapture(od, ['status', '--json'], request, env, 10_000);
    if (probe.code === 0) return true;
  }
  throw new Error(`Open Design daemon did not start within ${request.daemon.startupTimeoutMs}ms`);
}

async function materializeProject(od, projectId, request, env) {
  const listing = await odJson(od, ['files', 'list', projectId, '--json'], request, env, 30_000);
  const files = Array.isArray(listing.files) ? listing.files : [];
  const entryFile = files.find((file) => file.path === request.artifact.entry)
    ?? files.find((file) => file.kind === 'html' && file.artifactManifest?.status === 'complete')
    ?? files.find((file) => file.kind === 'html');
  if (!entryFile) throw new Error('Open Design project contains no HTML artifact');

  const materialized = [];
  for (const file of files) {
    if (file.type !== 'file') continue;
    if (!safeProjectPath(file.path)) throw new Error(`unsafe Open Design file path: ${file.path}`);
    const target = path.resolve(request.artifact.outputDir, file.path);
    if (!isWithin(request.artifact.outputDir, target)) throw new Error(`unsafe Open Design file path: ${file.path}`);
    const read = await odCapture(od, ['files', 'read', projectId, file.path], request, env, 30_000, false);
    if (read.code !== 0) throw new Error(`failed to read Open Design file ${file.path}: ${read.stderr.trim()}`);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, read.stdoutBuffer);
    materialized.push({ path: file.path, absolutePath: target, bytes: read.stdoutBuffer.length });
  }

  const absolutePath = path.resolve(request.artifact.outputDir, entryFile.path);
  if (!fs.existsSync(absolutePath)) throw new Error(`materialized artifact missing: ${absolutePath}`);
  const bytes = fs.statSync(absolutePath).size;
  return {
    entry: entryFile.path,
    absolutePath,
    outputDir: request.artifact.outputDir,
    bytes,
    sha256: sha256File(absolutePath),
    files: materialized
  };
}

function verifyHtmlArtifact(file) {
  const html = fs.readFileSync(file, 'utf8');
  const checks = [
    ['html-size', html.length >= 512, `${html.length} characters`],
    ['html-document', /<!doctype\s+html/i.test(html) && /<html[\s>]/i.test(html) && /<body[\s>]/i.test(html), 'doctype, html, and body present'],
    ['html-placeholders', !/\{\{[^}]+\}\}|\b(?:TODO|FIXME|lorem ipsum)\b/i.test(html), 'no unresolved templates or placeholder markers']
  ];
  const inlineScripts = [...html.matchAll(/<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
    .filter((match) => !/\btype\s*=\s*["']module["']/i.test(match[1] ?? ''))
    .map((match) => match[2])
    .filter((script) => script.trim());
  let scriptsValid = true;
  let scriptError = '';
  for (const script of inlineScripts) {
    try { new Function(script); } catch (error) {
      scriptsValid = false;
      scriptError = error.message;
      break;
    }
  }
  checks.push(['inline-script-syntax', scriptsValid, scriptsValid ? `${inlineScripts.length} inline script(s) parsed` : scriptError]);
  return checks.map(([check, passed, summary]) => ({ check, result: passed ? 'passed' : 'failed', summary }));
}

async function captureScreenshot(htmlFile, request, env) {
  const browserPath = resolveBrowserPath(env);
  const browser = await chromium.launch({
    executablePath: browserPath,
    headless: true,
    args: ['--no-sandbox', '--disable-gpu']
  });
  try {
    const page = await browser.newPage({ viewport: request.screenshot.viewport });
    const pageErrors = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    if (!request.screenshot.allowNetwork) {
      await page.route('**/*', async (route) => {
        const protocol = new URL(route.request().url()).protocol;
        if (['file:', 'data:', 'blob:', 'about:'].includes(protocol)) await route.continue();
        else await route.abort('blockedbyclient');
      });
    }
    await page.goto(pathToFileURL(htmlFile).href, { waitUntil: 'load' });
    if (request.screenshot.waitMs > 0) await page.waitForTimeout(request.screenshot.waitMs);
    if (pageErrors.length) throw new Error(`browser page error: ${pageErrors.join('; ')}`);
    const screenshotPath = path.join(request.artifact.outputDir, 'screenshot.png');
    await page.screenshot({ path: screenshotPath, fullPage: request.screenshot.fullPage });
    const dimensions = pngDimensions(screenshotPath);
    return {
      absolutePath: screenshotPath,
      bytes: fs.statSync(screenshotPath).size,
      sha256: sha256File(screenshotPath),
      width: dimensions.width,
      height: dimensions.height,
      fullPage: request.screenshot.fullPage,
      browserPath
    };
  } finally {
    await browser.close();
  }
}

function resolveBrowserPath(env) {
  if (env.CENTURION_BROWSER_BIN && fs.existsSync(env.CENTURION_BROWSER_BIN)) return env.CENTURION_BROWSER_BIN;
  const candidates = ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'];
  for (const candidate of candidates) {
    const resolved = spawnSync('sh', ['-lc', `command -v ${candidate}`], { encoding: 'utf8' }).stdout.trim();
    if (resolved && fs.existsSync(resolved)) return resolved;
  }
  throw new Error('Chrome/Chromium executable not found; set CENTURION_BROWSER_BIN');
}

async function odJson(od, args, request, env, timeoutMs = 30_000) {
  const result = await odCapture(od, args, request, env, timeoutMs);
  if (result.code !== 0) throw new Error(`Open Design command failed (${args.slice(0, 3).join(' ')}): ${result.stderr.trim() || result.stdout.trim()}`);
  try { return JSON.parse(result.stdout); } catch (error) {
    throw new Error(`Open Design returned invalid JSON for ${args.slice(0, 3).join(' ')}: ${error.message}`);
  }
}

async function odCapture(od, args, request, env, timeoutMs = 30_000, text = true) {
  const daemonArgs = ['--daemon-url', request.daemon.url];
  const finalArgs = [...od.prefix, ...args, ...daemonArgs];
  return runCommand(od.command, finalArgs, { env, timeoutMs });
}

async function readProjectFileMaybe(od, projectId, relativePath, request, env) {
  const listing = await odJson(od, ['files', 'list', projectId, '--json'], request, env, 30_000);
  const exists = Array.isArray(listing.files)
    && listing.files.some((file) => file.type === 'file' && file.path === relativePath);
  if (!exists) return null;
  const read = await odCapture(od, ['files', 'read', projectId, relativePath], request, env, 30_000);
  if (read.code !== 0) throw new Error(`failed to read previous Open Design artifact ${relativePath}: ${read.stderr.trim()}`);
  return read.stdoutBuffer;
}

function assertOutputTargetsUnused(request) {
  if (fs.existsSync(request.artifact.outputDir)) {
    throw new Error(`output bundle already exists; use a new requestId/outputDir: ${request.artifact.outputDir}`);
  }
}

function runCommand(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { env: options.env, stdio: ['ignore', 'pipe', 'pipe'] });
    const stdout = [];
    const stderr = [];
    let captured = 0;
    let settled = false;
    let killTimer = null;
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      killTimer = setTimeout(() => child.kill('SIGKILL'), 2_000);
      killTimer.unref();
    }, options.timeoutMs);

    const collect = (target) => (chunk) => {
      captured += chunk.length;
      if (captured > MAX_CAPTURE_BYTES) {
        child.kill('SIGTERM');
        return;
      }
      target.push(chunk);
    };
    child.stdout.on('data', collect(stdout));
    child.stderr.on('data', collect(stderr));
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (killTimer) clearTimeout(killTimer);
      reject(error);
    });
    child.on('close', (code, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (killTimer) clearTimeout(killTimer);
      const stdoutBuffer = Buffer.concat(stdout);
      const stderrBuffer = Buffer.concat(stderr);
      resolve({
        code: code ?? 1,
        signal,
        stdout: stdoutBuffer.toString('utf8'),
        stderr: stderrBuffer.toString('utf8'),
        stdoutBuffer,
        stderrBuffer
      });
    });
  });
}

function safeProjectPath(value) {
  const normalized = String(value).replaceAll('\\', '/');
  return normalized.length > 0
    && !path.posix.isAbsolute(normalized)
    && !/^[A-Za-z]:\//.test(normalized)
    && !normalized.split('/').includes('..');
}

function isWithin(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function pngDimensions(file) {
  const header = fs.readFileSync(file).subarray(0, 24);
  if (header.length < 24 || header.toString('hex', 0, 8) !== '89504e470d0a1a0a') throw new Error('screenshot is not a valid PNG');
  return { width: header.readUInt32BE(16), height: header.readUInt32BE(20) };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
