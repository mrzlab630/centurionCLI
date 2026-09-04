import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

function siblingPath(target, kind) {
  return path.join(path.dirname(target), `.${path.basename(target)}.centurion-${kind}-${crypto.randomUUID()}`);
}

function ensureParent(target) {
  const missing = [];
  let cursor = path.dirname(target);
  while (!fs.existsSync(cursor)) {
    missing.push(cursor);
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
    cursor = parent;
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  return missing;
}

function removeEmptyParents(operations) {
  const parents = [...new Set(operations.flatMap((operation) => operation.createdParents ?? []))]
    .sort((left, right) => right.length - left.length);
  for (const parent of parents) {
    try { fs.rmdirSync(parent); } catch (error) {
      if (!['ENOENT', 'ENOTEMPTY', 'EEXIST'].includes(error.code)) throw error;
    }
  }
}

function cleanupFailedStage(staged, createdParents) {
  fs.rmSync(staged, { recursive: true, force: true });
  removeEmptyParents([{ createdParents }]);
}

export function copyTree(source, destination, options = {}) {
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (options.skip?.(entry.name)) continue;
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) copyTree(sourcePath, destinationPath, options);
    else {
      fs.copyFileSync(sourcePath, destinationPath);
      const mode = options.mode?.(sourcePath) ?? (fs.statSync(sourcePath).mode & 0o777);
      fs.chmodSync(destinationPath, mode);
    }
  }
}

export function stageDirectory(source, target, options = {}) {
  const createdParents = ensureParent(target);
  const staged = siblingPath(target, 'stage');
  try {
    copyTree(source, staged, options);
    return { target, staged, backup: null, createdParents };
  } catch (error) {
    cleanupFailedStage(staged, createdParents);
    throw error;
  }
}

export function stageFile(source, target, options = {}) {
  const createdParents = ensureParent(target);
  const staged = siblingPath(target, 'stage');
  try {
    fs.copyFileSync(source, staged);
    fs.chmodSync(staged, options.mode ?? (fs.statSync(source).mode & 0o777));
    return { target, staged, backup: null, createdParents };
  } catch (error) {
    cleanupFailedStage(staged, createdParents);
    throw error;
  }
}

export function stageFileContent(content, target, options = {}) {
  const createdParents = ensureParent(target);
  const staged = siblingPath(target, 'stage');
  try {
    fs.writeFileSync(staged, content, { mode: options.mode ?? 0o600 });
    return { target, staged, backup: null, createdParents };
  } catch (error) {
    cleanupFailedStage(staged, createdParents);
    throw error;
  }
}

export function snapshotFile(file) {
  if (!fs.existsSync(file)) return { file, existed: false, content: null, mode: null };
  const stats = fs.lstatSync(file);
  if (!stats.isFile() || stats.isSymbolicLink()) throw new Error(`transaction snapshot target must be a regular file: ${file}`);
  return { file, existed: true, content: fs.readFileSync(file), mode: stats.mode & 0o777 };
}

export function restoreFile(snapshot) {
  if (!snapshot.existed) {
    fs.rmSync(snapshot.file, { force: true });
    return;
  }
  fs.mkdirSync(path.dirname(snapshot.file), { recursive: true });
  fs.writeFileSync(snapshot.file, snapshot.content, { mode: snapshot.mode });
  fs.chmodSync(snapshot.file, snapshot.mode);
}

export function discardStaged(operations, options = {}) {
  for (const operation of operations) {
    fs.rmSync(operation.staged, { recursive: true, force: true });
    if (options.removeBackups && operation.backup) {
      fs.rmSync(operation.backup, { recursive: true, force: true });
    }
  }
  removeEmptyParents(operations);
}

export function commitTransaction(operations, afterSwap) {
  const touched = [];
  try {
    for (const operation of operations) {
      touched.push(operation);
      operation.backedUp = false;
      operation.installed = false;
      if (fs.existsSync(operation.target)) {
        operation.backup = siblingPath(operation.target, 'backup');
        fs.renameSync(operation.target, operation.backup);
        operation.backedUp = true;
      }
      fs.renameSync(operation.staged, operation.target);
      operation.installed = true;
    }
    afterSwap?.();
  } catch (error) {
    const rollbackErrors = [];
    for (const operation of [...touched].reverse()) {
      try {
        if (operation.installed) fs.rmSync(operation.target, { recursive: true, force: true });
        if (operation.backedUp && operation.backup && fs.existsSync(operation.backup)) {
          fs.renameSync(operation.backup, operation.target);
        }
      } catch (rollbackError) {
        rollbackErrors.push(`${operation.target}: ${rollbackError.message}`);
      }
    }
    discardStaged(operations, { removeBackups: rollbackErrors.length === 0 });
    if (rollbackErrors.length) {
      throw new Error(`${error.message}; rollback incomplete: ${rollbackErrors.join('; ')}`);
    }
    throw error;
  }
  for (const operation of touched) {
    if (!operation.backup) continue;
    try {
      fs.rmSync(operation.backup, { recursive: true, force: true });
    } catch (error) {
      process.emitWarning(`installed target kept but backup cleanup failed for ${operation.target}: ${error.message}`);
    }
  }
}
