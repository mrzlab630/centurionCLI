import fs from 'node:fs';
import path from 'node:path';

export const CONTROL_NAMESPACE_ROOT = '.centurion/agents_results';
export const AGY_RESULT_FILE = 'AGY_RESULT.json';
export const AGY_SNAPSHOT_FILE = 'AGY_SNAPSHOT.json';

const SAFE_ORDER_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/;
const CONTROL_FILES = new Set([AGY_RESULT_FILE, AGY_SNAPSHOT_FILE]);

function fail(message) {
  throw new Error(message);
}

export function validateOrderId(value, label = 'orderId') {
  if (typeof value !== 'string' || value.length === 0) fail(`${label} is required`);
  if (value !== value.trim() || !SAFE_ORDER_ID.test(value)) {
    fail(`${label} is unsafe; use 8-128 ASCII letters, digits, '_' or '-' with no separators or traversal`);
  }
  return value;
}

export function normalizeArtifactPath(value, label = 'control artifact path') {
  if (typeof value !== 'string' || value.length === 0) fail(`${label} is required`);
  if (value !== value.trim()) fail(`${label} must not have surrounding whitespace`);
  if (path.isAbsolute(value) || value.startsWith('/') || value.includes('\\')) {
    fail(`${label} must be a relative POSIX path inside the control namespace`);
  }
  const parts = value.split('/');
  if (parts.some((part) => !part || part === '.' || part === '..')) {
    fail(`${label} must not contain empty, '.' or '..' path segments`);
  }
  return parts.join('/');
}

export function controlArtifactPath(orderId, fileName) {
  const safeId = validateOrderId(orderId);
  if (!CONTROL_FILES.has(fileName)) fail(`unsupported AGY control file: ${fileName}`);
  return `${CONTROL_NAMESPACE_ROOT}/${safeId}/${fileName}`;
}

export function assertControlArtifactPath(value, orderId, fileName, label = 'control artifact path') {
  const normalized = normalizeArtifactPath(value, label);
  const expected = controlArtifactPath(orderId, fileName);
  if (normalized !== expected) fail(`${label} must be exactly ${expected}`);
  return normalized;
}

export function assertNamespacedArtifactPath(value, orderId, label = 'control artifact path') {
  const normalized = normalizeArtifactPath(value, label);
  const parts = normalized.split('/');
  const safeId = validateOrderId(orderId);
  if (parts.length !== 4 || parts[0] !== '.centurion' || parts[1] !== 'agents_results' || parts[2] !== safeId) {
    fail(`${label} must be inside the exact namespace ${CONTROL_NAMESPACE_ROOT}/${safeId}/`);
  }
  return normalized;
}

export function deriveOrderIdFromControlPath(value, _fileName, label = 'control artifact path') {
  const normalized = normalizeArtifactPath(value, label);
  const parts = normalized.split('/');
  if (parts.length !== 4 || parts[0] !== '.centurion' || parts[1] !== 'agents_results') {
    fail(`${label} must be namespaced as ${CONTROL_NAMESPACE_ROOT}/<orderId>/<file>`);
  }
  const orderId = validateOrderId(parts[2]);
  if (!parts[3]) fail(`${label} must include a control filename`);
  return orderId;
}

export function assertNoSymlinkComponents(target, label = 'path') {
  const absolute = path.resolve(target);
  const root = path.parse(absolute).root;
  let current = root;
  for (const segment of absolute.slice(root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, segment);
    let stat;
    try {
      stat = fs.lstatSync(current);
    } catch (error) {
      if (error.code === 'ENOENT') break;
      throw error;
    }
    if (stat.isSymbolicLink()) fail(`${label} contains a symlink alias: ${current}`);
  }
  return absolute;
}

export function resolveWorkspace(value, { requireExists = true } = {}) {
  if (typeof value !== 'string' || value.length === 0) fail('workspace is required');
  const workspace = assertNoSymlinkComponents(path.resolve(value), 'workspace');
  if (requireExists && !fs.existsSync(workspace)) fail(`workspace not found: ${workspace}`);
  if (requireExists && !fs.statSync(workspace).isDirectory()) fail(`workspace is not a directory: ${workspace}`);
  return workspace;
}

export function assertExternalCustodyPath(workspaceValue, value, label = 'snapshot path') {
  if (typeof value !== 'string' || !value.trim() || !path.isAbsolute(value)) {
    fail(`${label} must be an explicit absolute path outside the workspace for controller custody`);
  }
  const workspace = resolveWorkspace(workspaceValue);
  const target = assertNoSymlinkComponents(path.resolve(value), label);
  const relative = path.relative(workspace, target);
  if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
    fail(`${label} must be outside the workspace; in-workspace snapshots are unsafe controller custody`);
  }
  return target;
}

export function deriveControlPaths(workspaceValue, orderId, options = {}) {
  const workspace = resolveWorkspace(workspaceValue, { requireExists: options.requireWorkspace !== false });
  const safeId = validateOrderId(orderId);
  const resultRelative = options.resultPath === undefined
    ? controlArtifactPath(safeId, AGY_RESULT_FILE)
    : assertNamespacedArtifactPath(options.resultPath, safeId, 'result path');
  const snapshotRelative = options.snapshotPath === undefined
    ? controlArtifactPath(safeId, AGY_SNAPSHOT_FILE)
    : assertNamespacedArtifactPath(options.snapshotPath, safeId, 'snapshot path');
  const namespaceRelative = `${CONTROL_NAMESPACE_ROOT}/${safeId}`;
  const namespaceAbsolute = path.join(workspace, '.centurion', 'agents_results', safeId);
  const resultAbsolute = path.join(workspace, ...resultRelative.split('/'));
  const snapshotAbsolute = path.join(workspace, ...snapshotRelative.split('/'));
  assertNoSymlinkComponents(namespaceAbsolute, 'control namespace');
  assertNoSymlinkComponents(resultAbsolute, 'result path');
  assertNoSymlinkComponents(snapshotAbsolute, 'snapshot path');
  return {
    workspace,
    orderId: safeId,
    namespaceRelative,
    namespaceAbsolute,
    resultRelative,
    resultAbsolute,
    snapshotRelative,
    snapshotAbsolute
  };
}

export function ensureControlNamespace(paths) {
  assertNoSymlinkComponents(paths.namespaceAbsolute, 'control namespace');
  fs.mkdirSync(paths.namespaceAbsolute, { recursive: true });
  assertNoSymlinkComponents(paths.namespaceAbsolute, 'control namespace');
  return paths.namespaceAbsolute;
}
