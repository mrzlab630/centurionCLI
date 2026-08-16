import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const DIRECTORY_FLAGS = fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW;
const READ_FILE_FLAGS = fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW;
const WRITE_FILE_FLAGS = fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_NOFOLLOW;
const MAX_REMOVE_ENTRIES = 100_000;

function procFdPath(fd, name = '') {
  return name ? `/proc/self/fd/${fd}/${name}` : `/proc/self/fd/${fd}`;
}

function assertLinuxProcFd() {
  if (process.platform !== 'linux' || !fs.existsSync('/proc/self/fd')) {
    throw new Error('secure Open Design storage requires Linux /proc/self/fd support');
  }
}

function safeComponent(value) {
  return typeof value === 'string'
    && value.length > 0
    && value !== '.'
    && value !== '..'
    && !value.includes('/')
    && !value.includes('\0');
}

function relativeParts(relativePath) {
  const normalized = String(relativePath ?? '').replaceAll('\\', '/');
  if (normalized === '' || normalized === '.') return [];
  if (path.posix.isAbsolute(normalized) || /^[A-Za-z]:\//.test(normalized)) {
    throw new Error(`path must be relative: ${relativePath}`);
  }
  const parts = normalized.split('/');
  if (!parts.every(safeComponent)) throw new Error(`unsafe relative path: ${relativePath}`);
  return parts;
}

function openDuplicateDirectory(fd) {
  return fs.openSync(procFdPath(fd), fs.constants.O_RDONLY | fs.constants.O_DIRECTORY);
}

function walkDirectoryFd(startFd, parts, options = {}) {
  let currentFd = openDuplicateDirectory(startFd);
  const walked = [];
  try {
    for (const part of parts) {
      walked.push(part);
      const target = procFdPath(currentFd, part);
      let nextFd;
      try {
        nextFd = fs.openSync(target, DIRECTORY_FLAGS);
      } catch (error) {
        if (error.code === 'ELOOP' || error.code === 'ENOTDIR') {
          throw new Error(`path must stay within anchored storage: ${walked.join('/')}`);
        }
        if (error.code !== 'ENOENT' || !options.create) throw error;
        try {
          fs.mkdirSync(target, { mode: options.mode ?? 0o700 });
        } catch (mkdirError) {
          if (mkdirError.code !== 'EEXIST') throw mkdirError;
        }
        nextFd = fs.openSync(target, DIRECTORY_FLAGS);
      }
      fs.closeSync(currentFd);
      currentFd = nextFd;
    }
    return currentFd;
  } catch (error) {
    fs.closeSync(currentFd);
    throw error;
  }
}

function openAbsoluteDirectory(absolutePath, options = {}) {
  assertLinuxProcFd();
  const resolved = path.resolve(absolutePath);
  const parts = resolved.split(path.sep).filter(Boolean);
  const rootFd = fs.openSync(path.parse(resolved).root, DIRECTORY_FLAGS);
  try {
    const fd = walkDirectoryFd(rootFd, parts, options);
    return { absolutePath: resolved, fd };
  } finally {
    fs.closeSync(rootFd);
  }
}

function openParentFd(startFd, relativePath, options = {}) {
  const parts = relativeParts(relativePath);
  const name = parts.pop();
  if (!name) throw new Error(`path must name an entry: ${relativePath}`);
  return {
    fd: walkDirectoryFd(startFd, parts, options),
    name,
    parentParts: parts
  };
}

function assertRegularFile(fd, label) {
  const stats = fs.fstatSync(fd);
  if (!stats.isFile()) throw new Error(`${label} must be a regular file`);
  return stats;
}

function assertDirectoryBinding(fd, expectedPath, label) {
  let currentFd;
  try {
    currentFd = fs.openSync(expectedPath, DIRECTORY_FLAGS);
    const anchored = fs.fstatSync(fd);
    const current = fs.fstatSync(currentFd);
    if (anchored.dev !== current.dev || anchored.ino !== current.ino) {
      throw new Error(`${label} changed during the anchored filesystem operation: ${expectedPath}`);
    }
  } catch (error) {
    if (error.message?.includes('changed during the anchored filesystem operation')) throw error;
    throw new Error(`${label} changed during the anchored filesystem operation: ${expectedPath}`);
  } finally {
    if (currentFd !== undefined) fs.closeSync(currentFd);
  }
}

function assertEntryBinding(parentFd, name, entryFd, label) {
  let currentFd;
  try {
    currentFd = fs.openSync(procFdPath(parentFd, name), DIRECTORY_FLAGS);
    const anchored = fs.fstatSync(entryFd);
    const current = fs.fstatSync(currentFd);
    if (anchored.dev !== current.dev || anchored.ino !== current.ino) {
      throw new Error(`${label} changed during the anchored filesystem operation`);
    }
  } catch (error) {
    if (error.message?.includes('changed during the anchored filesystem operation')) throw error;
    throw new Error(`${label} changed during the anchored filesystem operation`);
  } finally {
    if (currentFd !== undefined) fs.closeSync(currentFd);
  }
}

function lstatEntry(parentFd, name) {
  try {
    return fs.lstatSync(procFdPath(parentFd, name));
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function removeEntry(parentFd, name, state) {
  if (!safeComponent(name)) throw new Error(`unsafe entry name: ${name}`);
  state.counter.count += 1;
  if (state.counter.count > MAX_REMOVE_ENTRIES) throw new Error('anchored cleanup exceeded its bounded entry limit');

  const target = procFdPath(parentFd, name);
  const stats = lstatEntry(parentFd, name);
  if (!stats) return false;
  if (state.depth === 0 && state.expectedType === 'directory' && !stats.isDirectory()) {
    throw new Error(`cleanup target must remain a directory: ${name}`);
  }
  if (state.depth === 0 && state.expectedType === 'file' && !stats.isFile()) {
    throw new Error(`cleanup target must remain a regular file: ${name}`);
  }
  if (stats.isSymbolicLink() || !stats.isDirectory()) {
    fs.unlinkSync(target);
    return true;
  }

  let childFd;
  try {
    childFd = fs.openSync(target, DIRECTORY_FLAGS);
  } catch (error) {
    if (error.code === 'ELOOP' || error.code === 'ENOTDIR') {
      if (state.depth === 0 && state.expectedType === 'directory') {
        throw new Error(`cleanup target changed during the anchored filesystem operation: ${name}`);
      }
      fs.unlinkSync(target);
      return true;
    }
    if (error.code === 'ENOENT') return false;
    throw error;
  }
  const openedStats = fs.fstatSync(childFd);
  if (openedStats.dev !== stats.dev || openedStats.ino !== stats.ino) {
    fs.closeSync(childFd);
    throw new Error(`cleanup target changed during the anchored filesystem operation: ${name}`);
  }
  try {
    while (true) {
      const entries = fs.readdirSync(procFdPath(childFd));
      if (entries.length === 0) break;
      for (const entry of entries) {
        removeEntry(childFd, entry, { counter: state.counter, depth: state.depth + 1, expectedType: null });
      }
    }
    assertEntryBinding(parentFd, name, childFd, `cleanup target ${name}`);
  } finally {
    fs.closeSync(childFd);
  }

  try {
    fs.rmdirSync(target);
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    if (error.code === 'ENOTDIR') {
      fs.unlinkSync(target);
      return true;
    }
    if (error.code === 'ENOTEMPTY') return removeEntry(parentFd, name, state);
    throw error;
  }
  return true;
}

export class AnchoredDirectory {
  constructor(root, fd, relativePath = '') {
    this.root = root;
    this.fd = fd;
    this.relativePath = relativePath;
    this.closed = false;
  }

  get absolutePath() {
    return this.relativePath ? path.join(this.root.basePath, this.relativePath) : this.root.basePath;
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    fs.closeSync(this.fd);
  }

  assertCurrentBinding(label = 'directory') {
    assertDirectoryBinding(this.fd, this.absolutePath, label);
  }

  relative(target) {
    const absoluteTarget = path.resolve(target);
    const relative = path.relative(this.absolutePath, absoluteTarget);
    if (relative === '') return '';
    if (relative.startsWith('..') || path.isAbsolute(relative)) {
      throw new Error(`path must stay within ${this.absolutePath}: ${absoluteTarget}`);
    }
    relativeParts(relative);
    return relative;
  }

  resolve(relativePath = '') {
    const parts = relativeParts(relativePath);
    return path.join(this.absolutePath, ...parts);
  }

  emitHook(operation, phase, relativePath) {
    this.root.hook?.({
      operation,
      phase,
      relativePath: path.join(this.relativePath, relativePath),
      absolutePath: this.resolve(relativePath)
    });
  }

  openDirectory(relativePath = '', options = {}) {
    const parts = relativeParts(relativePath);
    const fd = walkDirectoryFd(this.fd, parts, options);
    const directory = new AnchoredDirectory(this.root, fd, path.join(this.relativePath, ...parts));
    try {
      directory.assertCurrentBinding(options.label ?? 'directory');
      return directory;
    } catch (error) {
      directory.close();
      throw error;
    }
  }

  createDirectory(relativePath, options = {}) {
    const parent = openParentFd(this.fd, relativePath, {
      create: options.createParents === true,
      mode: options.parentMode ?? 0o700
    });
    const target = procFdPath(parent.fd, parent.name);
    try {
      this.emitHook(options.operation ?? 'create-directory', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'directory parent');
      fs.mkdirSync(target, { mode: options.mode ?? 0o700 });
      const fd = fs.openSync(target, DIRECTORY_FLAGS);
      return new AnchoredDirectory(this.root, fd, path.join(this.relativePath, ...parent.parentParts, parent.name));
    } finally {
      fs.closeSync(parent.fd);
    }
  }

  createUniqueDirectory(relativeParent, prefix, options = {}) {
    const parent = this.openDirectory(relativeParent, { create: true, mode: options.parentMode ?? 0o700 });
    try {
      for (let attempt = 0; attempt < 32; attempt += 1) {
        const name = `${prefix}${crypto.randomBytes(8).toString('hex')}`;
        try {
          return parent.createDirectory(name, { mode: options.mode ?? 0o700, operation: options.operation ?? 'create-unique-directory' });
        } catch (error) {
          if (error.code !== 'EEXIST') throw error;
        }
      }
      throw new Error('could not allocate a unique anchored directory');
    } finally {
      parent.close();
    }
  }

  exists(relativePath) {
    let parent;
    try {
      parent = openParentFd(this.fd, relativePath);
      return lstatEntry(parent.fd, parent.name) !== null;
    } catch (error) {
      if (error.code === 'ENOENT') return false;
      throw error;
    } finally {
      if (parent) fs.closeSync(parent.fd);
    }
  }

  lstat(relativePath) {
    let parent;
    try {
      parent = openParentFd(this.fd, relativePath);
      return lstatEntry(parent.fd, parent.name);
    } catch (error) {
      if (error.code === 'ENOENT') return null;
      throw error;
    } finally {
      if (parent) fs.closeSync(parent.fd);
    }
  }

  entries(relativePath = '', options = {}) {
    const directory = this.openDirectory(relativePath, options);
    try {
      return fs.readdirSync(procFdPath(directory.fd), { withFileTypes: true });
    } finally {
      directory.close();
    }
  }

  readFile(relativePath, options = {}) {
    const parent = openParentFd(this.fd, relativePath);
    let fileFd;
    try {
      this.emitHook(options.operation ?? 'read-file', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'file parent');
      try {
        fileFd = fs.openSync(procFdPath(parent.fd, parent.name), READ_FILE_FLAGS);
      } catch (error) {
        if (error.code === 'ELOOP' || error.code === 'ENOTDIR') {
          throw new Error(`${options.label ?? this.resolve(relativePath)} must be a regular file`);
        }
        throw error;
      }
      const stats = assertRegularFile(fileFd, options.label ?? this.resolve(relativePath));
      if (options.maxBytes !== undefined && stats.size > options.maxBytes) {
        throw new Error(`${options.label ?? this.resolve(relativePath)} exceeds ${options.maxBytes} bytes`);
      }
      return fs.readFileSync(fileFd, options.encoding);
    } finally {
      if (fileFd !== undefined) fs.closeSync(fileFd);
      fs.closeSync(parent.fd);
    }
  }

  writeFile(relativePath, data, options = {}) {
    const parent = openParentFd(this.fd, relativePath, {
      create: options.createParents !== false,
      mode: options.parentMode ?? 0o700
    });
    let fileFd;
    try {
      this.emitHook(options.operation ?? 'write-file', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'file parent');
      let flags = WRITE_FILE_FLAGS;
      if (options.append) flags |= fs.constants.O_APPEND;
      else if (options.exclusive !== false) flags |= fs.constants.O_EXCL;
      else flags |= fs.constants.O_TRUNC;
      fileFd = fs.openSync(procFdPath(parent.fd, parent.name), flags, options.mode ?? 0o600);
      assertRegularFile(fileFd, options.label ?? this.resolve(relativePath));
      if (options.append) fs.writeFileSync(fileFd, data);
      else fs.writeFileSync(fileFd, data);
      if (options.fsync !== false) fs.fsyncSync(fileFd);
      return fs.fstatSync(fileFd);
    } finally {
      if (fileFd !== undefined) fs.closeSync(fileFd);
      fs.closeSync(parent.fd);
    }
  }

  replaceFile(relativePath, data, options = {}) {
    const parent = openParentFd(this.fd, relativePath, {
      create: options.createParents !== false,
      mode: options.parentMode ?? 0o700
    });
    const temporaryName = `.${parent.name}.${crypto.randomBytes(8).toString('hex')}.tmp`;
    let fileFd;
    try {
      fileFd = fs.openSync(
        procFdPath(parent.fd, temporaryName),
        WRITE_FILE_FLAGS | fs.constants.O_EXCL,
        options.mode ?? 0o600
      );
      fs.writeFileSync(fileFd, data);
      fs.fsyncSync(fileFd);
      fs.closeSync(fileFd);
      fileFd = undefined;
      this.emitHook(options.operation ?? 'replace-file', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'file parent');
      fs.renameSync(procFdPath(parent.fd, temporaryName), procFdPath(parent.fd, parent.name));
      fs.fsyncSync(parent.fd);
    } finally {
      if (fileFd !== undefined) fs.closeSync(fileFd);
      try { fs.unlinkSync(procFdPath(parent.fd, temporaryName)); } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      fs.closeSync(parent.fd);
    }
  }

  openAppendFile(relativePath, options = {}) {
    const parent = openParentFd(this.fd, relativePath, { create: true, mode: options.parentMode ?? 0o700 });
    try {
      this.emitHook(options.operation ?? 'open-append-file', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'file parent');
      const fd = fs.openSync(
        procFdPath(parent.fd, parent.name),
        WRITE_FILE_FLAGS | fs.constants.O_APPEND,
        options.mode ?? 0o600
      );
      assertRegularFile(fd, options.label ?? this.resolve(relativePath));
      return fd;
    } finally {
      fs.closeSync(parent.fd);
    }
  }

  remove(relativePath, options = {}) {
    const parent = openParentFd(this.fd, relativePath);
    try {
      this.emitHook(options.operation ?? 'remove', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'removal parent');
      return removeEntry(parent.fd, parent.name, {
        counter: { count: 0 },
        depth: 0,
        expectedType: options.expectedType ?? null
      });
    } finally {
      fs.closeSync(parent.fd);
    }
  }

  utimes(relativePath, atime, mtime, options = {}) {
    const parent = openParentFd(this.fd, relativePath);
    try {
      this.emitHook(options.operation ?? 'utimes', 'before-syscall', relativePath);
      assertDirectoryBinding(parent.fd, this.resolve(parent.parentParts.join('/')), options.label ?? 'timestamp parent');
      fs.utimesSync(procFdPath(parent.fd, parent.name), atime, mtime);
    } finally {
      fs.closeSync(parent.fd);
    }
  }

  rename(relativePath, destination, destinationRelativePath, options = {}) {
    const sourceParent = openParentFd(this.fd, relativePath);
    const destinationParent = openParentFd(destination.fd, destinationRelativePath, {
      create: options.createParents === true,
      mode: options.parentMode ?? 0o700
    });
    let renamed = false;
    try {
      this.emitHook(options.operation ?? 'rename', 'before-syscall', relativePath);
      assertDirectoryBinding(sourceParent.fd, this.resolve(sourceParent.parentParts.join('/')), options.label ?? 'rename source parent');
      assertDirectoryBinding(
        destinationParent.fd,
        destination.resolve(destinationParent.parentParts.join('/')),
        options.label ?? 'rename destination parent'
      );
      fs.renameSync(
        procFdPath(sourceParent.fd, sourceParent.name),
        procFdPath(destinationParent.fd, destinationParent.name)
      );
      renamed = true;
      assertDirectoryBinding(sourceParent.fd, this.resolve(sourceParent.parentParts.join('/')), options.label ?? 'rename source parent');
      assertDirectoryBinding(
        destinationParent.fd,
        destination.resolve(destinationParent.parentParts.join('/')),
        options.label ?? 'rename destination parent'
      );
    } catch (error) {
      if (renamed && lstatEntry(destinationParent.fd, destinationParent.name) && !lstatEntry(sourceParent.fd, sourceParent.name)) {
        try {
          fs.renameSync(
            procFdPath(destinationParent.fd, destinationParent.name),
            procFdPath(sourceParent.fd, sourceParent.name)
          );
        } catch {}
      }
      throw error;
    } finally {
      fs.closeSync(sourceParent.fd);
      fs.closeSync(destinationParent.fd);
    }
  }

  renameNoReplace(relativePath, destination, destinationRelativePath, options = {}) {
    const sourceParent = openParentFd(this.fd, relativePath);
    const destinationParent = openParentFd(destination.fd, destinationRelativePath, {
      create: options.createParents === true,
      mode: options.parentMode ?? 0o700
    });
    try {
      this.emitHook(options.operation ?? 'rename-no-replace', 'before-syscall', relativePath);
      assertDirectoryBinding(sourceParent.fd, this.resolve(sourceParent.parentParts.join('/')), options.label ?? 'rename source parent');
      assertDirectoryBinding(
        destinationParent.fd,
        destination.resolve(destinationParent.parentParts.join('/')),
        options.label ?? 'rename destination parent'
      );
      const result = spawnSync('/usr/bin/mv', [
        '-T', '--no-copy', '--update=none-fail',
        `/proc/self/fd/3/${sourceParent.name}`,
        `/proc/self/fd/4/${destinationParent.name}`
      ], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'pipe', sourceParent.fd, destinationParent.fd]
      });
      if (result.status !== 0) {
        const message = `${result.stderr || ''}${result.stdout || ''}`.trim();
        const error = new Error(message || `atomic no-replace rename failed with status ${result.status}`);
        if (/not replacing|File exists/i.test(message)) error.code = 'EEXIST';
        throw error;
      }
      assertDirectoryBinding(sourceParent.fd, this.resolve(sourceParent.parentParts.join('/')), options.label ?? 'rename source parent');
      assertDirectoryBinding(
        destinationParent.fd,
        destination.resolve(destinationParent.parentParts.join('/')),
        options.label ?? 'rename destination parent'
      );
    } finally {
      fs.closeSync(sourceParent.fd);
      fs.closeSync(destinationParent.fd);
    }
  }

}

export class AnchoredRoot extends AnchoredDirectory {
  constructor(absolutePath, options = {}) {
    const opened = openAbsoluteDirectory(absolutePath, { create: options.create === true, mode: options.mode ?? 0o700 });
    const root = { basePath: opened.absolutePath, hook: options.hook ?? null };
    super(root, opened.fd, '');
  }
}

export function readFileAnchored(root, target, options = {}) {
  const anchored = new AnchoredRoot(root, { create: false, hook: options.hook });
  try {
    const relative = anchored.relative(target);
    if (!relative) throw new Error(`${options.label ?? 'file'} must not be the storage root`);
    return anchored.readFile(relative, options);
  } finally {
    anchored.close();
  }
}
