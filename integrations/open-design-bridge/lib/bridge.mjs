import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { spawn, spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright-core';
import { normalizedRequest, RESULT_VERSION } from './contracts.mjs';
import { MAX_JSON_INPUT_BYTES } from './json-input.mjs';
import { assertPathWithinRoot, assertPublicOutputPath, isWithinPath, projectedRealPath } from './path-safety.mjs';
import { AnchoredRoot } from './descriptor-fs.mjs';

const MAX_CAPTURE_BYTES = 24 * 1024 * 1024;
const MAX_PROJECT_FILES = 512;
const MAX_MATERIALIZED_BYTES = 128 * 1024 * 1024;
const TERMINAL_RUN_STATUSES = new Set(['completed', 'succeeded', 'failed', 'cancelled']);

export async function runDesignRequest(rawRequest, options = {}) {
  const cwd = options.cwd ?? process.cwd();
  const env = options.env ?? process.env;
  const outputRoot = env.CENTURION_DESIGN_ROOT
    ? path.resolve(env.CENTURION_DESIGN_ROOT)
    : path.resolve(cwd, '.centurion', 'design');
  const referenceRoot = env.CENTURION_REFERENCE_ROOT
    ? path.resolve(env.CENTURION_REFERENCE_ROOT)
    : path.join(outputRoot, '.reference-cache');
  const storageRoot = new AnchoredRoot(outputRoot, { create: true, hook: options.storageHook });
  try {
    return await runDesignRequestAnchored(rawRequest, options, { cwd, env, outputRoot, referenceRoot, storageRoot });
  } finally {
    storageRoot.close();
  }
}

async function runDesignRequestAnchored(rawRequest, options, context) {
  const { cwd, env, outputRoot, referenceRoot, storageRoot } = context;
  const request = normalizedRequest(rawRequest, { cwd, outputRoot, referenceRoot, storageRoot, storageHook: options.storageHook });
  options.afterNormalize?.(request);
  if (request.action !== 'cleanup' && options.resultPath) {
    assertResultPathOutsideBundle(request.artifact.outputDir, options.resultPath);
  }
  const staleStagingRemoved = sweepTransientRoot(storageRoot, '.staging', request.cleanup.stagingMaxAgeHours);
  const staleTrashRemoved = sweepTransientRoot(storageRoot, '.trash', request.cleanup.stagingMaxAgeHours);
  if (request.action === 'cleanup') {
    return runCleanupRequest(request, {
      env,
      outputRoot,
      storageRoot,
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
  let references = null;
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
    stagingDir = createStagingDir(storageRoot, request.requestId);
    executionRequest = {
      ...request,
      artifact: { ...request.artifact, outputDir: stagingDir }
    };
    od = resolveOdCommand(env);
    daemonStarted = await ensureDaemon(od, executionRequest, env, stagingDir, storageRoot);
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

    references = await stageReferences(od, projectId, executionRequest, env);
    if (references) {
      proof.push({
        check: 'references-staged',
        result: 'passed',
        summary: `${references.selectedIds.length} reference(s) staged in Open Design project`
      });
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
    storageRoot.writeFile(storageRoot.relative(runLogPath), watched.stdout, { operation: 'run-log-write' });
    if (watched.stderr.trim()) {
      storageRoot.writeFile(storageRoot.relative(path.join(stagingDir, 'open-design-stderr.log')), watched.stderr, { operation: 'stderr-log-write' });
    }

    runInfo = await odJson(od, ['run', 'info', runId, '--json'], executionRequest, env, 30_000);
    if (!TERMINAL_RUN_STATUSES.has(runInfo.status)) {
      throw new Error(`Open Design run is not terminal after watch: status=${runInfo.status}`);
    }
    if (runInfo.status === 'cancelled') throw new Error('Open Design run was cancelled');
    if (!['completed', 'succeeded'].includes(runInfo.status)) {
      warnings.push(`Open Design run ended with status=${runInfo.status}${runInfo.error ? `: ${runInfo.error}` : ''}`);
    }

    artifact = await materializeProject(od, projectId, executionRequest, env, storageRoot);
    proof.push(...verifyHtmlArtifact(storageRoot.readFile(storageRoot.relative(artifact.absolutePath), { operation: 'artifact-proof-read' })));
    if (request.action === 'revise') {
      const changed = Boolean(previousArtifactSha256) && artifact.sha256 !== previousArtifactSha256;
      proof.push({
        check: 'revision-changed',
        result: changed ? 'passed' : 'failed',
        summary: changed ? 'artifact SHA-256 changed from the previous project state' : 'revision did not change the artifact SHA-256'
      });
    }

    if (request.screenshot.enabled) {
      screenshot = await captureScreenshot(artifact.absolutePath, executionRequest, env, storageRoot);
      proof.push({
        check: 'screenshot',
        result: 'passed',
        summary: `${screenshot.width}x${screenshot.height} PNG rendered in Chrome`
      });
    }

    const failedProof = proof.filter((entry) => entry.result !== 'passed');
    if (failedProof.length) errors.push(...failedProof.map((entry) => `${entry.check}: ${entry.summary}`));
    if (errors.length === 0) {
      references = preserveReferenceEvidence(references, executionRequest, stagingDir, storageRoot);
      promoteStaging(storageRoot, stagingDir, finalOutputDir);
      artifact = rebaseArtifact(artifact, stagingDir, finalOutputDir);
      screenshot = rebaseScreenshot(screenshot, stagingDir, finalOutputDir);
      runLogPath = rebasePath(runLogPath, stagingDir, finalOutputDir);
      references = rebaseReferences(references, stagingDir, finalOutputDir);
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
      storageRoot,
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
    orchestrator: request.orchestrator,
    references,
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
  let targetPath = path.resolve(request.artifact.outputDir);
  try {
    const targetRelative = options.storageRoot.relative(targetPath);
    if (!targetRelative) throw new Error(`cleanup target must stay within ${options.outputRoot}: ${targetPath}`);
    const stats = options.storageRoot.lstat(targetRelative);
    if (stats?.isSymbolicLink()) throw new Error(`cleanup target must not be a symbolic link: ${targetPath}`);
    if (stats && !stats.isDirectory()) throw new Error(`cleanup target must be a directory: ${targetPath}`);
  } catch (error) {
    errors.push(error.message);
  }
  if ([path.join(options.outputRoot, '.staging'), path.join(options.outputRoot, '.trash')]
    .some((reservedRoot) => targetPath === path.resolve(reservedRoot))) {
    errors.push('cleanup target cannot be a transient root directory');
  }
  if (options.resultPath) {
    try { assertResultPathOutsideBundle(targetPath, options.resultPath, 'cleanup --result path'); }
    catch (error) { errors.push(error.message); }
  }
  if (errors.length === 0) {
    try {
      assertRemovableDirectory(options.storageRoot, targetPath);
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
      const scratch = createStagingDir(options.storageRoot, `${request.requestId}-cleanup`);
      try {
        const od = resolveOdCommand(options.env);
        const cleanupRequest = { ...request, artifact: { ...request.artifact, outputDir: scratch } };
        await ensureDaemon(od, cleanupRequest, options.env, scratch, options.storageRoot);
        const deleted = await odCapture(od, ['project', 'delete', projectId], cleanupRequest, options.env, 30_000);
        if (deleted.code !== 0) throw new Error(deleted.stderr.trim() || deleted.stdout.trim());
        projectDeleted = true;
        proof.push({ check: 'project-cleanup', result: 'passed', summary: `deleted Open Design project ${projectId}` });
      } catch (error) {
        errors.push(`Open Design project cleanup failed: ${error.message}`);
      } finally {
        try {
          options.storageRoot.remove(options.storageRoot.relative(scratch), {
            operation: 'cleanup-scratch-remove',
            expectedType: 'directory'
          });
        } catch (error) {
          warnings.push(`failed cleanup scratch removal: ${error.message}`);
        }
      }
    }
  }

  if (errors.length === 0) {
    try {
      const targetRelative = options.storageRoot.relative(targetPath);
      if (!options.storageRoot.exists(targetRelative)) {
        warnings.push(`cleanup target already absent: ${targetPath}`);
        localAction = 'already-absent';
      } else if (request.cleanup.mode === 'trash') {
        const trashRoot = path.join(options.outputRoot, '.trash');
        const trashDirectory = options.storageRoot.openDirectory('.trash', { create: true });
        trashDirectory.close();
        trashPath = path.join(trashRoot, `${Date.now()}-${crypto.randomUUID()}-${path.basename(targetPath)}`);
        options.storageRoot.rename(targetRelative, options.storageRoot, options.storageRoot.relative(trashPath), {
          createParents: true,
          operation: 'cleanup-trash-rename'
        });
        const trashedAt = new Date();
        options.storageRoot.utimes(options.storageRoot.relative(trashPath), trashedAt, trashedAt, { operation: 'cleanup-trash-retention' });
        localAction = 'trashed';
      } else {
        options.storageRoot.remove(targetRelative, { operation: 'cleanup-delete', expectedType: 'directory' });
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
    orchestrator: request.orchestrator,
    references: previous?.references ?? null,
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

async function cleanupFailedRun({ cleanup, request, executionRequest, stagingDir, od, projectId, env, storageRoot, warnings }) {
  if (request.cleanup.onFailure === 'delete') {
    try {
      storageRoot.remove(storageRoot.relative(stagingDir), {
        operation: 'failed-staging-remove',
        expectedType: 'directory'
      });
      cleanup.stagingDeleted = !storageRoot.exists(storageRoot.relative(stagingDir));
    } catch (error) {
      warnings.push(`failed staging cleanup: ${error.message}`);
      cleanup.stagingDeleted = !storageRoot.exists(storageRoot.relative(stagingDir));
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

function createStagingDir(storageRoot, requestId) {
  const safeId = String(requestId).replace(/[^A-Za-z0-9._-]/g, '-');
  const staging = storageRoot.createUniqueDirectory('.staging', `${safeId}-`, { operation: 'staging-create' });
  const stagingDir = staging.absolutePath;
  staging.close();
  return stagingDir;
}

function promoteStaging(storageRoot, stagingDir, finalOutputDir) {
  assertPublicOutputPath(storageRoot.absolutePath, finalOutputDir);
  const stagingRelative = storageRoot.relative(stagingDir);
  const finalRelative = storageRoot.relative(finalOutputDir);
  if (storageRoot.exists(finalRelative)) {
    throw new Error(`output bundle appeared during execution; refusing to replace it: ${finalOutputDir}`);
  }
  try {
    storageRoot.renameNoReplace(stagingRelative, storageRoot, finalRelative, {
      createParents: true,
      operation: 'publish-rename',
      label: 'output publication parent'
    });
  } catch (error) {
    if (['EEXIST', 'ENOTEMPTY'].includes(error.code)) {
      throw new Error(`output bundle appeared during execution; refusing to replace it: ${finalOutputDir}`);
    }
    throw error;
  }
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

function sweepTransientRoot(storageRoot, directory, maxAgeHours) {
  if (!storageRoot.exists(directory)) return 0;
  const transientRoot = storageRoot.openDirectory(directory);
  const cutoff = Date.now() - (maxAgeHours * 60 * 60 * 1000);
  let removed = 0;
  try {
    for (const entry of transientRoot.entries()) {
      if (!entry.isDirectory() || entry.isSymbolicLink()) continue;
      const stats = transientRoot.lstat(entry.name);
      if (!stats?.isDirectory() || stats.isSymbolicLink() || stats.mtimeMs >= cutoff) continue;
      transientRoot.remove(entry.name, { operation: `${directory}-ttl-remove`, expectedType: 'directory' });
      removed += 1;
    }
  } finally {
    transientRoot.close();
  }
  return removed;
}

function assertRemovableDirectory(storageRoot, targetPath) {
  const stats = storageRoot.lstat(storageRoot.relative(targetPath));
  if (!stats) return;
  if (stats.isSymbolicLink()) throw new Error(`cleanup target must not be a symbolic link: ${targetPath}`);
  if (!stats.isDirectory()) throw new Error(`cleanup target must be a directory: ${targetPath}`);
}

function buildProductionPrompt(request) {
  const action = request.action === 'create'
    ? `Create the requested interface and write the canonical deliverable to ${request.artifact.entry}.`
    : `Inspect the current ${request.artifact.entry}, then revise that same artifact in place.`;
  const referenceLines = request.references
    ? [
        `Reference manifest: ${request.references.manifestPath}`,
        `Selected reference IDs: ${request.references.selectedIds.join(', ')}.`,
        `Reference strategy: ${request.references.strategy}.`,
        'Read context/centurion/reference-manifest.json before implementation.',
        'Use import-and-adapt references as ingredients, not as a full-page clone. Use inspire-only references for direction only; do not copy their code, assets, branding, or text.'
      ]
    : [];
  return [
    'You are the Open Design production executor inside a CENTURION proof-first workflow.',
    action,
    `User brief: ${request.brief}`,
    `Target viewport: ${request.screenshot.viewport.width}x${request.screenshot.viewport.height}.`,
    ...referenceLines,
    'Return a working implementation, not a prose-only design.',
    'Keep the primary artifact directly renderable in Chrome.',
    'Preserve valid existing behavior during revisions unless the brief explicitly replaces it.',
    'Verify the artifact before finishing. Do not delete unrelated project files.'
  ].join('\n');
}

async function stageReferences(od, projectId, request, env) {
  if (!request.references) return null;
  verifyReferenceManifest(request.references);
  const selected = request.references.manifest.references
    .filter((reference) => request.references.selectedIds.includes(reference.id));
  const manifest = portableReferenceManifest({
    ...request.references.manifest,
    strategy: request.references.strategy,
    references: selected
  });
  const manifestText = `${JSON.stringify(manifest, null, 2)}\n`;
  await odWrite(od, projectId, 'context/centurion/reference-manifest.json', Buffer.from(manifestText), request, env);
  const stagedSnippets = [];
  for (const reference of selected) {
    if (!reference.snippet?.absolutePath) continue;
    const snippet = readVerifiedReferenceSnippet(reference, request.references.manifestPath);
    const projectPath = `context/centurion/snippets/${referenceSnippetName(reference)}`;
    await odWrite(od, projectId, projectPath, snippet.bytes, request, env);
    stagedSnippets.push({ id: reference.id, projectPath, sha256: reference.snippet.sha256 });
  }
  return {
    manifestPath: request.references.manifestPath,
    manifestSha256: request.references.manifestSha256,
    projectManifestPath: 'context/centurion/reference-manifest.json',
    selectedIds: request.references.selectedIds,
    strategy: request.references.strategy,
    stagedSnippets
  };
}

function preserveReferenceEvidence(references, request, stagingDir, storageRoot) {
  if (!references) return null;
  verifyReferenceManifest(request.references);
  const evidenceDir = path.join(stagingDir, 'references');
  const manifestTarget = path.join(evidenceDir, 'reference-manifest.json');
  const acceptedManifest = portableReferenceManifest({
    ...request.references.manifest,
    strategy: request.references.strategy,
    references: request.references.manifest.references
      .filter((item) => request.references.selectedIds.includes(item.id))
  });
  storageRoot.writeFile(storageRoot.relative(manifestTarget), `${JSON.stringify(acceptedManifest, null, 2)}\n`, {
    operation: 'reference-evidence-manifest-write'
  });
  const snippetCopies = [];
  for (const reference of request.references.manifest.references
    .filter((item) => request.references.selectedIds.includes(item.id) && item.snippet?.absolutePath)) {
    const target = path.join(evidenceDir, 'snippets', referenceSnippetName(reference));
    const snippet = readVerifiedReferenceSnippet(reference, request.references.manifestPath);
    storageRoot.writeFile(storageRoot.relative(target), snippet.bytes, { operation: 'reference-evidence-snippet-write' });
    snippetCopies.push({
      id: reference.id,
      absolutePath: target,
      sha256: sha256Bytes(storageRoot.readFile(storageRoot.relative(target), { operation: 'reference-evidence-snippet-read' }))
    });
  }
  return {
    ...references,
    acceptedManifestPath: manifestTarget,
    acceptedManifestSha256: sha256Bytes(storageRoot.readFile(storageRoot.relative(manifestTarget), { operation: 'reference-evidence-manifest-read' })),
    acceptedSnippets: snippetCopies
  };
}

function verifyReferenceManifest(references) {
  const checked = assertPathWithinRoot(path.dirname(references.manifestPath), references.manifestPath, {
    label: 'reference manifest',
    rejectFinalSymlink: true,
    requireExisting: true
  });
  if (!checked.stats.isFile()) throw new Error(`reference manifest must be a regular file: ${references.manifestPath}`);
  const storageRoot = new AnchoredRoot(references.manifestRoot ?? path.dirname(references.manifestPath), { create: false });
  let bytes;
  try {
    bytes = storageRoot.readFile(storageRoot.relative(references.manifestPath), {
      operation: 'reference-manifest-read',
      label: 'reference manifest',
      maxBytes: MAX_JSON_INPUT_BYTES
    });
  } finally {
    storageRoot.close();
  }
  const actual = sha256Bytes(bytes);
  if (actual !== references.manifestSha256) throw new Error('reference manifest SHA-256 changed after validation');
}

function readVerifiedReferenceSnippet(reference, manifestPath) {
  const snippetPath = path.resolve(reference.snippet.absolutePath);
  const checked = assertPathWithinRoot(path.dirname(manifestPath), snippetPath, {
    allowRoot: false,
    label: `reference snippet ${reference.id}`,
    rejectFinalSymlink: true,
    requireExisting: true
  });
  if (!checked.stats.isFile()) throw new Error(`reference snippet missing or unsafe: ${reference.id}`);
  const storageRoot = new AnchoredRoot(path.dirname(manifestPath), { create: false });
  let bytes;
  try {
    bytes = storageRoot.readFile(storageRoot.relative(snippetPath), {
      operation: 'reference-snippet-read',
      label: `reference snippet ${reference.id}`,
      maxBytes: 48 * 1024
    });
  } finally {
    storageRoot.close();
  }
  const actual = crypto.createHash('sha256').update(bytes).digest('hex');
  if (actual !== reference.snippet.sha256) throw new Error(`reference snippet SHA-256 mismatch: ${reference.id}`);
  if (reference.snippet.bytes !== undefined && reference.snippet.bytes !== bytes.length) {
    throw new Error(`reference snippet byte count mismatch: ${reference.id}`);
  }
  return { bytes, sha256: actual };
}

function referenceSnippetName(reference) {
  const extension = path.extname(reference.snippet?.relativePath ?? '') || '.txt';
  return `${String(reference.id).replace(/[^A-Za-z0-9._-]/g, '-')}${extension}`;
}

function portableReferenceManifest(manifest) {
  return {
    ...manifest,
    references: manifest.references.map((reference) => ({
      ...reference,
      snippet: reference.snippet
        ? {
            relativePath: reference.snippet.relativePath,
            bytes: reference.snippet.bytes,
            sha256: reference.snippet.sha256,
            truncated: reference.snippet.truncated
          }
        : null
    }))
  };
}

function rebaseReferences(references, fromRoot, toRoot) {
  if (!references) return null;
  return {
    ...references,
    acceptedManifestPath: rebasePath(references.acceptedManifestPath, fromRoot, toRoot),
    acceptedSnippets: (references.acceptedSnippets ?? []).map((snippet) => ({
      ...snippet,
      absolutePath: rebasePath(snippet.absolutePath, fromRoot, toRoot)
    }))
  };
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

async function ensureDaemon(od, request, env, outputDir, storageRoot) {
  const status = await odCapture(od, ['status', '--json'], request, env, 15_000);
  if (status.code === 0) return false;
  if (!request.daemon.ensureRunning) throw new Error(`Open Design daemon is unavailable at ${request.daemon.url}`);

  const daemonLog = storageRoot.openAppendFile(storageRoot.relative(path.join(outputDir, 'open-design-daemon.log')), {
    operation: 'daemon-log-open'
  });
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

async function materializeProject(od, projectId, request, env, storageRoot) {
  const listing = await odJson(od, ['files', 'list', projectId, '--json'], request, env, 30_000);
  const files = Array.isArray(listing.files) ? listing.files : [];
  const regularFiles = files.filter((file) => file.type === 'file');
  if (regularFiles.length > MAX_PROJECT_FILES) {
    throw new Error(`Open Design project exceeds the ${MAX_PROJECT_FILES} file materialization limit`);
  }
  const declaredBytes = regularFiles.reduce((total, file) => {
    return total + (Number.isSafeInteger(file.size) && file.size > 0 ? file.size : 0);
  }, 0);
  if (declaredBytes > MAX_MATERIALIZED_BYTES) {
    throw new Error(`Open Design project exceeds the ${MAX_MATERIALIZED_BYTES} byte materialization limit`);
  }
  const entryFile = files.find((file) => file.path === request.artifact.entry)
    ?? files.find((file) => file.kind === 'html' && file.artifactManifest?.status === 'complete')
    ?? files.find((file) => file.kind === 'html');
  if (!entryFile) throw new Error('Open Design project contains no HTML artifact');

  const materialized = [];
  let materializedBytes = 0;
  for (const file of files) {
    if (file.type !== 'file') continue;
    if (!safeProjectPath(file.path)) throw new Error(`unsafe Open Design file path: ${file.path}`);
    const target = path.resolve(request.artifact.outputDir, file.path);
    const targetRelative = storageRoot.relative(target);
    const read = await odCapture(od, ['files', 'read', projectId, file.path], request, env, 30_000, false);
    if (read.code !== 0) throw new Error(`failed to read Open Design file ${file.path}: ${read.stderr.trim()}`);
    materializedBytes += read.stdoutBuffer.length;
    if (materializedBytes > MAX_MATERIALIZED_BYTES) {
      throw new Error(`Open Design project exceeds the ${MAX_MATERIALIZED_BYTES} byte materialization limit`);
    }
    storageRoot.writeFile(targetRelative, read.stdoutBuffer, {
      createParents: true,
      operation: 'materialize-write',
      label: `Open Design file ${file.path}`
    });
    materialized.push({ path: file.path, absolutePath: target, bytes: read.stdoutBuffer.length });
  }

  const absolutePath = path.resolve(request.artifact.outputDir, entryFile.path);
  const entryRelative = storageRoot.relative(absolutePath);
  const stats = storageRoot.lstat(entryRelative);
  if (!stats?.isFile() || stats.isSymbolicLink()) throw new Error(`materialized artifact missing: ${absolutePath}`);
  const bytes = stats.size;
  return {
    entry: entryFile.path,
    absolutePath,
    outputDir: request.artifact.outputDir,
    bytes,
    sha256: sha256Bytes(storageRoot.readFile(entryRelative, { operation: 'materialized-artifact-read' })),
    files: materialized
  };
}

function verifyHtmlArtifact(bytes) {
  const html = Buffer.isBuffer(bytes) ? bytes.toString('utf8') : String(bytes);
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

async function captureScreenshot(htmlFile, request, env, storageRoot) {
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
    const screenshotBytes = await page.screenshot({ fullPage: request.screenshot.fullPage });
    storageRoot.writeFile(storageRoot.relative(screenshotPath), screenshotBytes, { operation: 'screenshot-write' });
    const dimensions = pngDimensions(screenshotBytes);
    return {
      absolutePath: screenshotPath,
      bytes: screenshotBytes.length,
      sha256: sha256Bytes(screenshotBytes),
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

async function odWrite(od, projectId, relativePath, content, request, env) {
  const result = await odCapture(od, ['files', 'write', projectId, relativePath], request, env, 30_000, true, content);
  if (result.code !== 0) throw new Error(`failed to stage Open Design reference ${relativePath}: ${result.stderr.trim() || result.stdout.trim()}`);
}

async function odCapture(od, args, request, env, timeoutMs = 30_000, text = true, stdin = null) {
  const daemonArgs = ['--daemon-url', request.daemon.url];
  const finalArgs = [...od.prefix, ...args, ...daemonArgs];
  return runCommand(od.command, finalArgs, { env, timeoutMs, stdin });
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

function assertResultPathOutsideBundle(bundlePath, resultPath, label = '--result path') {
  const bundleReal = projectedRealPath(bundlePath);
  const resultReal = projectedRealPath(resultPath);
  if (isWithinPath(bundleReal, resultReal)) {
    throw new Error(`${label} must be outside the immutable bundle: ${path.resolve(bundlePath)}`);
  }
}

function runCommand(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { env: options.env, stdio: [options.stdin === null ? 'ignore' : 'pipe', 'pipe', 'pipe'] });
    const stdout = [];
    const stderr = [];
    let captured = 0;
    let captureExceeded = false;
    let timedOut = false;
    let settled = false;
    let killTimer = null;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGTERM');
      killTimer = setTimeout(() => child.kill('SIGKILL'), 2_000);
      killTimer.unref();
    }, options.timeoutMs);

    if (options.stdin !== null) {
      child.stdin.on('error', (error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (killTimer) clearTimeout(killTimer);
        child.kill('SIGTERM');
        reject(new Error(`Open Design command stdin failed: ${error.message}`));
      });
      child.stdin.end(options.stdin);
    }

    const collect = (target) => (chunk) => {
      if (captureExceeded) return;
      captured += chunk.length;
      if (captured > MAX_CAPTURE_BYTES) {
        captureExceeded = true;
        child.kill('SIGTERM');
        if (!killTimer) {
          killTimer = setTimeout(() => child.kill('SIGKILL'), 2_000);
          killTimer.unref();
        }
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
      if (captureExceeded) {
        reject(new Error(`Open Design command output exceeded ${MAX_CAPTURE_BYTES} bytes`));
        return;
      }
      if (timedOut) {
        reject(new Error(`Open Design command timed out after ${options.timeoutMs}ms`));
        return;
      }
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

function sha256Bytes(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function pngDimensions(bytes) {
  const header = Buffer.from(bytes).subarray(0, 24);
  if (header.length < 24 || header.toString('hex', 0, 8) !== '89504e470d0a1a0a') throw new Error('screenshot is not a valid PNG');
  return { width: header.readUInt32BE(16), height: header.readUInt32BE(20) };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
