import fs from 'node:fs';
import path from 'node:path';

export const REQUEST_VERSION = 'CENTURION_OD_REQUEST_V1';
export const RESULT_VERSION = 'CENTURION_OD_RESULT_V1';
const ACTIONS = new Set(['create', 'revise', 'cleanup']);
const ALLOWED_CAPABILITIES = new Set(['fs:write', 'prompt:inject']);
const FAILURE_POLICIES = new Set(['delete', 'keep', 'ask']);
const CLEANUP_MODES = new Set(['delete', 'trash']);

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

export function validateRequest(request) {
  const failures = [];
  if (!isObject(request)) return ['request must be a JSON object'];
  if (request.requestVersion !== REQUEST_VERSION) failures.push(`request.requestVersion must be ${REQUEST_VERSION}`);
  if (!ACTIONS.has(request.action)) failures.push('request.action must be create, revise, or cleanup');
  if (request.action !== 'cleanup' && (typeof request.brief !== 'string' || !request.brief.trim())) {
    failures.push('request.brief must be a non-empty string');
  }
  if (request.action === 'cleanup' && request.brief !== undefined
    && (typeof request.brief !== 'string' || !request.brief.trim())) {
    failures.push('request.brief must be a non-empty string when provided');
  }

  if (request.requestId !== undefined && (typeof request.requestId !== 'string' || !request.requestId.trim())) {
    failures.push('request.requestId must be a non-empty string when provided');
  }
  if (request.project !== undefined && !isObject(request.project)) failures.push('request.project must be an object');
  if (request.executor !== undefined && !isObject(request.executor)) failures.push('request.executor must be an object');
  if (request.artifact !== undefined && !isObject(request.artifact)) failures.push('request.artifact must be an object');
  if (request.screenshot !== undefined && !isObject(request.screenshot)) failures.push('request.screenshot must be an object');
  if (request.daemon !== undefined && !isObject(request.daemon)) failures.push('request.daemon must be an object');
  if (request.cleanup !== undefined && !isObject(request.cleanup)) failures.push('request.cleanup must be an object');

  for (const [value, label, allowNull] of [
    [request.project?.name, 'request.project.name', false],
    [request.project?.projectId, 'request.project.projectId', false],
    [request.project?.conversationId, 'request.project.conversationId', false],
    [request.project?.previousResultPath, 'request.project.previousResultPath', false],
    [request.executor?.agent, 'request.executor.agent', false],
    [request.executor?.model, 'request.executor.model', true],
    [request.executor?.plugin, 'request.executor.plugin', false],
    [request.artifact?.outputDir, 'request.artifact.outputDir', false]
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
  }
  if (request.executor?.inputs !== undefined && !isObject(request.executor.inputs)) {
    failures.push('request.executor.inputs must be an object');
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

export function loadPreviousResult(file, cwd = process.cwd()) {
  const absolutePath = path.resolve(cwd, file);
  const data = JSON.parse(fs.readFileSync(absolutePath, 'utf8'));
  if (data.resultVersion !== RESULT_VERSION) throw new Error(`previous result must use ${RESULT_VERSION}`);
  return { absolutePath, data };
}

export function normalizedRequest(request, options = {}) {
  const failures = validateRequest(request);
  if (failures.length) throw new Error(failures.join('; '));
  const cwd = options.cwd ?? process.cwd();
  const outputRoot = path.resolve(options.outputRoot ?? path.join(cwd, '.centurion', 'design'));
  const previous = request.project?.previousResultPath
    ? loadPreviousResultWithinRoot(request.project.previousResultPath, cwd, outputRoot)
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
  if (!isWithin(outputRoot, outputDir)) {
    throw new Error(`request.artifact.outputDir must stay within CENTURION_DESIGN_ROOT: ${outputRoot}`);
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
      deleteFailedProject: request.cleanup?.deleteFailedProject !== false,
      stagingMaxAgeHours: request.cleanup?.stagingMaxAgeHours ?? 24
    }
  };
}

function loadPreviousResultWithinRoot(file, cwd, outputRoot) {
  const absolutePath = path.resolve(cwd, file);
  if (!isWithin(outputRoot, absolutePath)) {
    throw new Error(`request.project.previousResultPath must stay within CENTURION_DESIGN_ROOT: ${outputRoot}`);
  }
  return loadPreviousResult(absolutePath);
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
  const expectedArtifactPath = path.resolve(target, entry);
  if (path.resolve(artifact.absolutePath) !== expectedArtifactPath) {
    throw new Error('previous result artifact.absolutePath must match artifact.outputDir and artifact.entry');
  }
  return target;
}

function isWithin(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function createRequestId() {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
  const random = Math.random().toString(36).slice(2, 8);
  return `od-${stamp}-${random}`;
}
