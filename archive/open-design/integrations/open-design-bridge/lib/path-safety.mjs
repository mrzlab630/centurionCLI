import fs from 'node:fs';
import path from 'node:path';

export function isWithinPath(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

export function projectedRealPath(value) {
  const absolutePath = path.resolve(value);
  const missing = [];
  let cursor = absolutePath;

  while (true) {
    try {
      fs.lstatSync(cursor);
      return path.resolve(fs.realpathSync(cursor), ...missing);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      const parent = path.dirname(cursor);
      if (parent === cursor) throw error;
      missing.unshift(path.basename(cursor));
      cursor = parent;
    }
  }
}

export function assertPathWithinRoot(root, target, options = {}) {
  const label = options.label ?? 'path';
  const absoluteRoot = path.resolve(root);
  const absoluteTarget = path.resolve(target);
  let stats = null;
  try {
    stats = fs.lstatSync(absoluteTarget);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    if (options.requireExisting) throw new Error(`${label} does not exist: ${absoluteTarget}`);
  }
  if (stats?.isSymbolicLink() && options.rejectFinalSymlink) {
    throw new Error(`${label} must not be a symbolic link: ${absoluteTarget}`);
  }
  const realRoot = projectedRealPath(absoluteRoot);
  const realTarget = projectedRealPath(absoluteTarget);

  if (!isWithinPath(realRoot, realTarget) || (options.allowRoot === false && realRoot === realTarget)) {
    throw new Error(`${label} must stay within ${absoluteRoot}: ${absoluteTarget}`);
  }
  return { absoluteRoot, absoluteTarget, realRoot, realTarget, stats };
}

export function assertPublicOutputPath(outputRoot, target) {
  const checked = assertPathWithinRoot(outputRoot, target, {
    allowRoot: false,
    label: 'request.artifact.outputDir',
    rejectFinalSymlink: true
  });
  for (const directory of ['.staging', '.trash', '.results', '.jobs', '.reference-cache']) {
    const reserved = projectedRealPath(path.join(outputRoot, directory));
    if (isWithinPath(reserved, checked.realTarget)) {
      throw new Error(`request.artifact.outputDir cannot use reserved ${directory} storage: ${checked.absoluteTarget}`);
    }
  }
  return checked;
}
