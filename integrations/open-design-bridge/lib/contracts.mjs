import fs from 'node:fs';
import path from 'node:path';
import { MAX_JSON_INPUT_BYTES } from './json-input.mjs';
import { normalizeDesignReferences } from './references.mjs';
import { readFileAnchored } from './descriptor-fs.mjs';
import { assertPathWithinRoot, assertPublicOutputPath, isWithinPath } from './path-safety.mjs';

export const REQUEST_VERSION = 'CENTURION_OD_REQUEST_V1';
export const RESULT_VERSION = 'CENTURION_OD_RESULT_V1';
const ACTIONS = new Set(['create', 'revise', 'cleanup']);
const ALLOWED_CAPABILITIES = new Set(['fs:write', 'prompt:inject']);
const FAILURE_POLICIES = new Set(['delete', 'keep', 'ask']);
const CLEANUP_MODES = new Set(['delete', 'trash']);
const MAX_REQUEST_ID_LENGTH = 128;
const MAX_BRIEF_LENGTH = 100_000;
const MAX_SELECTED_REFERENCES = 10;
const OBJECT_KEYS = Object.freeze({
  request: new Set(['requestVersion', 'requestId', 'action', 'brief', 'project', 'orchestrator', 'executor', 'artifact', 'references', 'screenshot', 'daemon', 'cleanup']),
  project: new Set(['name', 'projectId', 'conversationId', 'previousResultPath']),
  orchestrator: new Set(['client', 'owner']),
  executor: new Set(['agent', 'model', 'plugin', 'inputs', 'grantCapabilities', 'timeoutMs']),
  artifact: new Set(['entry', 'outputDir']),
  references: new Set(['manifestPath', 'selectedIds', 'strategy']),
  screenshot: new Set(['enabled', 'fullPage', 'allowNetwork', 'waitMs', 'viewport']),
  viewport: new Set(['width', 'height']),
  daemon: new Set(['url', 'ensureRunning', 'startupTimeoutMs']),
  cleanup: new Set(['onFailure', 'mode', 'deleteProject', 'deleteFailedProject', 'stagingMaxAgeHours'])
});

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function optionalStringFailure(value, label, allowNull = false) {
  if (value === undefined || (allowNull && value === null)) return null;
  if (typeof value !== 'string' || !value.trim()) return `${label} must be a non-empty string`;
  return null;
}

function safeRelativePath(value) {
  if (typeof value !== 'string' || !value.trim()) return false;
  const normalized = value.replaceAll('\\', '/');
  return !path.posix.isAbsolute(normalized)
    && !/^[A-Za-z]:\//.test(normalized)
    && !normalized.split('/').includes('..')
    && !normalized.includes('\0');
}

function rejectUnknownKeys(value, label, allowed, failures) {
  if (!isObject(value)) return;
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) failures.push(`${label}.${key} is not allowed`);
  }
}

export function validateRequest(request) {
  const failures = [];
  if (!isObject(request)) return ['request must be a JSON object'];
  try {
    if (Buffer.byteLength(JSON.stringify(request)) > MAX_JSON_INPUT_BYTES) {
      failures.push(`request must not exceed ${MAX_JSON_INPUT_BYTES} bytes`);
    }
  } catch {
    return ['request must be JSON-serializable'];
  }
  rejectUnknownKeys(request, 'request', OBJECT_KEYS.request, failures);
  if (request.requestVersion !== REQUEST_VERSION) failures.push(`request.requestVersion must be ${REQUEST_VERSION}`);
  if (!ACTIONS.has(request.action)) failures.push('request.action must be create, revise, or cleanup');
  if (request.action !== 'cleanup' && (typeof request.brief !== 'string' || !request.brief.trim())) {
    failures.push('request.brief must be a non-empty string');
  }
  if (request.action === 'cleanup' && request.brief !== undefined
    && (typeof request.brief !== 'string' || !request.brief.trim())) {
    failures.push('request.brief must be a non-empty string when provided');
  }

  if (request.requestId !== undefined
    && (typeof request.requestId !== 'string' || !request.requestId.trim() || request.requestId.length > MAX_REQUEST_ID_LENGTH)) {
    failures.push(`request.requestId must be a non-empty string up to ${MAX_REQUEST_ID_LENGTH} characters when provided`);
  }
  if (typeof request.brief === 'string' && request.brief.length > MAX_BRIEF_LENGTH) {
    failures.push(`request.brief must not exceed ${MAX_BRIEF_LENGTH} characters`);
  }
  if (request.project !== undefined && !isObject(request.project)) failures.push('request.project must be an object');
  if (request.executor !== undefined && !isObject(request.executor)) failures.push('request.executor must be an object');
  if (request.artifact !== undefined && !isObject(request.artifact)) failures.push('request.artifact must be an object');
  if (request.screenshot !== undefined && !isObject(request.screenshot)) failures.push('request.screenshot must be an object');
  if (request.daemon !== undefined && !isObject(request.daemon)) failures.push('request.daemon must be an object');
  if (request.cleanup !== undefined && !isObject(request.cleanup)) failures.push('request.cleanup must be an object');
  if (request.orchestrator !== undefined && !isObject(request.orchestrator)) failures.push('request.orchestrator must be an object');
  if (request.references !== undefined && !isObject(request.references)) failures.push('request.references must be an object');

  rejectUnknownKeys(request.project, 'request.project', OBJECT_KEYS.project, failures);
  rejectUnknownKeys(request.orchestrator, 'request.orchestrator', OBJECT_KEYS.orchestrator, failures);
  rejectUnknownKeys(request.executor, 'request.executor', OBJECT_KEYS.executor, failures);
  rejectUnknownKeys(request.artifact, 'request.artifact', OBJECT_KEYS.artifact, failures);
  rejectUnknownKeys(request.references, 'request.references', OBJECT_KEYS.references, failures);
  rejectUnknownKeys(request.screenshot, 'request.screenshot', OBJECT_KEYS.screenshot, failures);
  rejectUnknownKeys(request.screenshot?.viewport, 'request.screenshot.viewport', OBJECT_KEYS.viewport, failures);
  rejectUnknownKeys(request.daemon, 'request.daemon', OBJECT_KEYS.daemon, failures);
  rejectUnknownKeys(request.cleanup, 'request.cleanup', OBJECT_KEYS.cleanup, failures);
  if (isObject(request.references)
    && (typeof request.references.manifestPath !== 'string' || !request.references.manifestPath.trim())) {
    failures.push('request.references.manifestPath must be a non-empty string');
  }

  for (const [value, label, allowNull] of [
    [request.project?.name, 'request.project.name', false],
    [request.project?.projectId, 'request.project.projectId', false],
    [request.project?.conversationId, 'request.project.conversationId', false],
    [request.project?.previousResultPath, 'request.project.previousResultPath', false],
    [request.executor?.agent, 'request.executor.agent', false],
    [request.executor?.model, 'request.executor.model', true],
    [request.executor?.plugin, 'request.executor.plugin', false],
    [request.artifact?.outputDir, 'request.artifact.outputDir', false],
    [request.orchestrator?.client, 'request.orchestrator.client', false],
    [request.orchestrator?.owner, 'request.orchestrator.owner', false],
    [request.references?.manifestPath, 'request.references.manifestPath', false]
  ]) {
    const failure = optionalStringFailure(value, label, allowNull);
    if (failure) failures.push(failure);
  }
  for (const [value, label] of [
    [request.screenshot?.enabled, 'request.screenshot.enabled'],
    [request.screenshot?.fullPage, 'request.screenshot.fullPage'],
    [request.screenshot?.allowNetwork, 'request.screenshot.allowNetwork'],
    [request.daemon?.ensureRunning, 'request.daemon.ensureRunning']
  ]) {
    if (value !== undefined && typeof value !== 'boolean') failures.push(`${label} must be boolean`);
  }

  const entry = request.artifact?.entry ?? 'index.html';
  if (!safeRelativePath(entry) || !entry.toLowerCase().endsWith('.html')) {
    failures.push('request.artifact.entry must be a safe relative HTML path');
  }
  const viewport = request.screenshot?.viewport;
  if (viewport !== undefined) {
    if (!isObject(viewport)) failures.push('request.screenshot.viewport must be an object');
    else {
      if (!Number.isInteger(viewport.width) || viewport.width < 320 || viewport.width > 4096) {
        failures.push('request.screenshot.viewport.width must be an integer from 320 to 4096');
      }
      if (!Number.isInteger(viewport.height) || viewport.height < 480 || viewport.height > 4096) {
        failures.push('request.screenshot.viewport.height must be an integer from 480 to 4096');
      }
    }
  }

  const grants = request.executor?.grantCapabilities;
  if (grants !== undefined && (!Array.isArray(grants) || !grants.every((item) => typeof item === 'string'))) {
    failures.push('request.executor.grantCapabilities must contain only strings');
  } else if (grants?.some((item) => !ALLOWED_CAPABILITIES.has(item))) {
    failures.push(`request.executor.grantCapabilities may only include: ${[...ALLOWED_CAPABILITIES].join(', ')}`);
  } else if (grants && new Set(grants).size !== grants.length) {
    failures.push('request.executor.grantCapabilities must not contain duplicates');
  }
  if (request.executor?.inputs !== undefined && !isObject(request.executor.inputs)) {
    failures.push('request.executor.inputs must be an object');
  }
  if (request.references?.selectedIds !== undefined
    && (!Array.isArray(request.references.selectedIds)
      || request.references.selectedIds.length > MAX_SELECTED_REFERENCES
      || !request.references.selectedIds.every((item) => typeof item === 'string' && item.trim()))) {
    failures.push(`request.references.selectedIds must contain at most ${MAX_SELECTED_REFERENCES} non-empty strings`);
  } else if (request.references?.selectedIds && new Set(request.references.selectedIds).size !== request.references.selectedIds.length) {
    failures.push('request.references.selectedIds must not contain duplicates');
  }
  if (request.references?.strategy !== undefined && !['compose', 'adapt', 'inspire'].includes(request.references.strategy)) {
    failures.push('request.references.strategy must be compose, adapt, or inspire');
  }
  for (const [value, label, minimum, maximum] of [
    [request.executor?.timeoutMs, 'request.executor.timeoutMs', 1_000, 3_600_000],
    [request.screenshot?.waitMs, 'request.screenshot.waitMs', 0, 60_000],
    [request.daemon?.startupTimeoutMs, 'request.daemon.startupTimeoutMs', 1_000, 300_000],
    [request.cleanup?.stagingMaxAgeHours, 'request.cleanup.stagingMaxAgeHours', 1, 720]
  ]) {
    if (value !== undefined && (!Number.isInteger(value) || value < minimum || value > maximum)) {
      failures.push(`${label} must be an integer from ${minimum} to ${maximum}`);
    }
  }

  if (request.action === 'revise') {
    const previousResultPath = request.project?.previousResultPath;
    const projectId = request.project?.projectId;
    if (!previousResultPath && !projectId) {
      failures.push('revise requires request.project.previousResultPath or request.project.projectId');
    }
  }
  if (request.action === 'cleanup') {
    const previousResultPath = request.project?.previousResultPath;
    if (!previousResultPath) failures.push('cleanup requires request.project.previousResultPath');
  }
  if (request.cleanup?.onFailure !== undefined && !FAILURE_POLICIES.has(request.cleanup.onFailure)) {
    failures.push('request.cleanup.onFailure must be delete, keep, or ask');
  }
  if (request.cleanup?.mode !== undefined && !CLEANUP_MODES.has(request.cleanup.mode)) {
    failures.push('request.cleanup.mode must be delete or trash');
  }
  if (request.cleanup?.deleteProject !== undefined && typeof request.cleanup.deleteProject !== 'boolean') {
    failures.push('request.cleanup.deleteProject must be boolean');
  }
  if (request.cleanup?.deleteFailedProject !== undefined && typeof request.cleanup.deleteFailedProject !== 'boolean') {
    failures.push('request.cleanup.deleteFailedProject must be boolean');
  }
  if (request.daemon?.url !== undefined) {
    try {
      const url = new URL(request.daemon.url);
      const loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
      if (!['http:', 'https:'].includes(url.protocol) || !loopback) {
        failures.push('request.daemon.url must be an HTTP(S) loopback URL');
      }
    } catch {
      failures.push('request.daemon.url must be a valid URL');
    }
  }
  return failures;
}

export function loadPreviousResult(file, cwd = process.cwd(), options = {}) {
  const absolutePath = path.resolve(cwd, file);
  const bytes = options.storageRoot
      ? options.storageRoot.readFile(options.storageRoot.relative(absolutePath), {
        operation: 'previous-result-read',
        label: 'request.project.previousResultPath',
        maxBytes: MAX_JSON_INPUT_BYTES
      })
    : readFileAnchored(path.dirname(absolutePath), absolutePath, {
        operation: 'previous-result-read',
        label: 'request.project.previousResultPath',
        maxBytes: MAX_JSON_INPUT_BYTES,
        hook: options.storageHook
      });
  const data = JSON.parse(bytes.toString('utf8'));
  if (data.resultVersion !== RESULT_VERSION) throw new Error(`previous result must use ${RESULT_VERSION}`);
  return { absolutePath, data };
}

export function normalizedRequest(request, options = {}) {
  const failures = validateRequest(request);
  if (failures.length) throw new Error(failures.join('; '));
  const cwd = options.cwd ?? process.cwd();
  const outputRoot = path.resolve(options.outputRoot ?? path.join(cwd, '.centurion', 'design'));
  const references = normalizeDesignReferences(request.references, {
    cwd,
    allowedRoots: [outputRoot, options.referenceRoot ?? path.join(outputRoot, '.reference-cache')],
    storageHook: options.storageHook
  });
  const previous = request.project?.previousResultPath
    ? loadPreviousResultWithinRoot(request.project.previousResultPath, cwd, outputRoot, options)
    : null;
  const requestId = request.requestId?.trim() || createRequestId();
  const entry = request.artifact?.entry ?? previous?.data.artifact?.entry ?? 'index.html';
  const cleanupTarget = request.action === 'cleanup'
    ? cleanupTargetFromPrevious(previous, outputRoot, entry)
    : null;
  const outputDir = request.action === 'cleanup'
    ? cleanupTarget
    : request.artifact?.outputDir
      ? path.resolve(cwd, request.artifact.outputDir)
      : path.join(outputRoot, requestId);
  if (request.action === 'cleanup' && !outputDir) {
    throw new Error('previous result contains no cleanup target or artifact outputDir');
  }
  if (request.action === 'cleanup') {
    if (!isWithinPath(outputRoot, outputDir) || path.resolve(outputRoot) === path.resolve(outputDir)) {
      throw new Error(`cleanup target must stay within CENTURION_DESIGN_ROOT: ${outputRoot}`);
    }
  } else {
    assertPublicOutputPath(outputRoot, outputDir);
  }
  if (request.action === 'revise' && !(request.project?.projectId ?? previous?.data.projectId)) {
    throw new Error('previous result does not contain projectId');
  }

  return {
    requestVersion: REQUEST_VERSION,
    requestId,
    action: request.action,
    brief: request.brief?.trim() ?? '',
    project: {
      name: request.project?.name?.trim() || `CENTURION Design ${requestId}`,
      projectId: request.project?.projectId ?? previous?.data.projectId ?? null,
      conversationId: request.project?.conversationId ?? previous?.data.conversationId ?? null,
      previousResultPath: previous?.absolutePath ?? null,
      previousResult: previous?.data ?? null
    },
    orchestrator: {
      client: request.orchestrator?.client ?? previous?.data.orchestrator?.client ?? 'unknown',
      owner: request.orchestrator?.owner ?? previous?.data.orchestrator?.owner ?? null
    },
    executor: {
      agent: request.executor?.agent ?? previous?.data.executor?.agent ?? 'codex',
      model: request.executor?.model ?? previous?.data.executor?.model ?? null,
      plugin: request.executor?.plugin ?? previous?.data.executor?.plugin ?? 'design-system-creative',
      inputs: {
        artifactKind: 'landing page',
        brief: request.brief?.trim() ?? '',
        ...(request.executor?.inputs ?? {})
      },
      grantCapabilities: request.executor?.grantCapabilities ?? ['fs:write'],
      timeoutMs: request.executor?.timeoutMs ?? 900_000
    },
    artifact: {
      entry,
      outputDir
    },
    references,
    screenshot: {
      enabled: request.screenshot?.enabled !== false,
      fullPage: request.screenshot?.fullPage !== false,
      viewport: {
        width: request.screenshot?.viewport?.width ?? 1440,
        height: request.screenshot?.viewport?.height ?? 1000
      },
      waitMs: request.screenshot?.waitMs ?? 500,
      allowNetwork: request.screenshot?.allowNetwork === true
    },
    daemon: {
      url: request.daemon?.url ?? 'http://127.0.0.1:7456',
      ensureRunning: request.daemon?.ensureRunning !== false,
      startupTimeoutMs: request.daemon?.startupTimeoutMs ?? 30_000
    },
    cleanup: {
      onFailure: request.cleanup?.onFailure ?? 'delete',
      mode: request.cleanup?.mode ?? 'delete',
      deleteProject: request.cleanup?.deleteProject === true,
      deleteFailedProject: request.cleanup?.deleteFailedProject === true,
      stagingMaxAgeHours: request.cleanup?.stagingMaxAgeHours ?? 24
    }
  };
}

function loadPreviousResultWithinRoot(file, cwd, outputRoot, options = {}) {
  const absolutePath = path.resolve(cwd, file);
  const storageRoot = options.storageRoot;
  if (!storageRoot) {
    const checked = assertPathWithinRoot(outputRoot, absolutePath, {
      allowRoot: false,
      label: 'request.project.previousResultPath',
      rejectFinalSymlink: true,
      requireExisting: true
    });
    if (!checked.stats.isFile()) throw new Error(`request.project.previousResultPath must be a regular file: ${absolutePath}`);
  }
  return loadPreviousResult(absolutePath, cwd, { storageRoot, storageHook: options.storageHook });
}

function cleanupTargetFromPrevious(previous, outputRoot, entry) {
  const preservedPath = previous?.data.cleanup?.preservedPath ?? null;
  if (preservedPath) {
    if (!path.isAbsolute(preservedPath)) {
      throw new Error('previous result cleanup.preservedPath must be absolute');
    }
    const target = path.resolve(preservedPath);
    const stagingRoot = path.resolve(outputRoot, '.staging');
    if (path.dirname(target) !== stagingRoot) {
      throw new Error('previous result cleanup.preservedPath must be a direct child of CENTURION_DESIGN_ROOT/.staging');
    }
    return target;
  }

  const artifact = previous?.data.artifact;
  if (!artifact?.outputDir) return null;
  if (!path.isAbsolute(artifact.outputDir) || !path.isAbsolute(artifact.absolutePath ?? '')) {
    throw new Error('previous result artifact cleanup paths must be absolute');
  }
  const target = path.resolve(artifact.outputDir);
  if (!isWithinPath(outputRoot, target) || path.resolve(outputRoot) === target) {
    throw new Error(`previous result artifact.outputDir must stay within CENTURION_DESIGN_ROOT: ${outputRoot}`);
  }
  const expectedArtifactPath = path.resolve(target, entry);
  if (path.resolve(artifact.absolutePath) !== expectedArtifactPath) {
    throw new Error('previous result artifact.absolutePath must match artifact.outputDir and artifact.entry');
  }
  return target;
}

function createRequestId() {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
  const random = Math.random().toString(36).slice(2, 8);
  return `od-${stamp}-${random}`;
}
