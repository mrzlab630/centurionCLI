import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { runDesignRequest } from '../lib/bridge.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const mockOd = path.join(here, 'fixtures', 'mock-od.mjs');
const browserPath = ['/home/mrz/.local/bin/google-chrome', '/usr/bin/google-chrome', '/usr/bin/chromium']
  .find((candidate) => fs.existsSync(candidate));

test('create returns absolute artifact path and deterministic proof', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-bridge-'));
  try {
    const outputDir = path.join(root, 'out');
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-create',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.projectId, 'mock-project-1');
    assert.equal(result.artifact.absolutePath, path.join(outputDir, 'index.html'));
    assert(fs.existsSync(result.artifact.absolutePath));
    assert(result.proof.every((entry) => entry.result === 'passed'));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('revise reuses project identity from a previous result', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-revise-'));
  try {
    const previousPath = path.join(root, 'previous.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      projectId: 'mock-project-1',
      conversationId: 'mock-conversation-1',
      executor: { agent: 'codex', plugin: 'design-system-creative', model: null },
      artifact: { entry: 'index.html' }
    }));
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-revise',
      action: 'revise',
      brief: 'Improve the hero.',
      project: { previousResultPath: previousPath },
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.projectId, 'mock-project-1');
    assert.equal(result.revisionOf, previousPath);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('browser proof returns an absolute full-page PNG', { skip: !browserPath }, async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-browser-'));
  try {
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-browser',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: true, fullPage: true, viewport: { width: 1280, height: 720 } }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd]),
        CENTURION_BROWSER_BIN: browserPath
      }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.screenshot.width, 1280);
    assert(result.screenshot.height >= 720);
    assert(fs.existsSync(result.screenshot.absolutePath));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('unsafe OD file paths fail the result instead of being skipped', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-unsafe-'));
  try {
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-unsafe',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        MOCK_OD_UNSAFE_PATH: '1',
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('unsafe Open Design file path')));
    assert.equal(result.cleanup.stagingDeleted, true);
    assert.equal(result.cleanup.failedProjectDeleted, true);
    assert(fs.existsSync(path.join(root, 'state', 'project-deleted')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('existing artifact targets are immutable and cannot be overwritten', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-existing-'));
  try {
    const outputDir = path.join(root, 'out');
    fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(path.join(outputDir, 'index.html'), '<!doctype html><html><body>existing</body></html>');
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-existing',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        CENTURION_DESIGN_ROOT: root,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('output bundle already exists')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('concurrent creates cannot replace the same output bundle', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-concurrent-'));
  try {
    const outputDir = path.join(root, 'out');
    const run = (requestId) => runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId,
      action: 'create',
      brief: `Create ${requestId}.`,
      artifact: { outputDir },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, `state-${requestId}`),
        MOCK_OD_WATCH_DELAY_MS: '100',
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    const results = await Promise.all([run('concurrent-a'), run('concurrent-b')]);
    const done = results.filter((result) => result.status === 'done');
    const failed = results.filter((result) => result.status === 'failed');
    assert.equal(done.length, 1);
    assert.equal(failed.length, 1);
    assert(failed[0].errors.some((error) => error.includes('appeared during execution')));
    assert.equal(fs.existsSync(done[0].artifact.absolutePath), true);
    assert.equal(done[0].artifact.sha256, sha256File(done[0].artifact.absolutePath));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('failed validation can preserve staging for an explicit user decision', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-keep-failure-'));
  try {
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-keep-failure',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false },
      cleanup: { onFailure: 'ask' }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        MOCK_OD_UNSAFE_PATH: '1',
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'failed');
    assert.equal(result.cleanup.pending, true);
    assert(fs.existsSync(result.cleanup.preservedPath));
    assert.equal(fs.existsSync(path.join(root, 'state', 'project-deleted')), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('failed revise deletes staging but preserves the existing OD project', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-revise-failure-'));
  try {
    const previousPath = path.join(root, 'previous.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      projectId: 'mock-project-1',
      conversationId: 'mock-conversation-1',
      executor: { agent: 'codex', plugin: 'design-system-creative', model: null },
      artifact: { entry: 'index.html' }
    }));
    const stateDir = path.join(root, 'state');
    const outputDir = path.join(root, 'out');
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-revise-failure',
      action: 'revise',
      brief: 'Produce an invalid revision for cleanup proof.',
      project: { previousResultPath: previousPath },
      artifact: { outputDir },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: stateDir,
        CENTURION_DESIGN_ROOT: root,
        MOCK_OD_UNSAFE_PATH: '1',
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'failed');
    assert.equal(result.cleanup.stagingDeleted, true);
    assert.equal(result.cleanup.failedProjectDeleted, false);
    assert.equal(fs.existsSync(path.join(stateDir, 'project-deleted')), false);
    assert.equal(fs.existsSync(outputDir), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('request startup sweeps only expired staging and trash directories', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-ttl-'));
  try {
    const oldStaging = path.join(root, '.staging', 'old-job');
    const oldTrash = path.join(root, '.trash', 'old-bundle');
    const freshStaging = path.join(root, '.staging', 'fresh-job');
    const freshTrash = path.join(root, '.trash', 'fresh-bundle');
    for (const directory of [oldStaging, oldTrash, freshStaging, freshTrash]) {
      fs.mkdirSync(directory, { recursive: true });
      fs.writeFileSync(path.join(directory, 'marker.txt'), directory);
    }
    const expired = new Date(Date.now() - (2 * 60 * 60 * 1000));
    fs.utimesSync(oldStaging, expired, expired);
    fs.utimesSync(oldTrash, expired, expired);
    const linkedOutside = path.join(root, 'linked-outside');
    const stagingLink = path.join(root, '.staging', 'linked-directory');
    fs.mkdirSync(linkedOutside);
    fs.writeFileSync(path.join(linkedOutside, 'marker.txt'), 'keep');
    fs.symlinkSync(linkedOutside, stagingLink, 'dir');

    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'mock-ttl',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false },
      cleanup: { stagingMaxAgeHours: 1 }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.cleanup.staleStagingRemoved, 1);
    assert.equal(result.cleanup.staleTrashRemoved, 1);
    assert.equal(fs.existsSync(oldStaging), false);
    assert.equal(fs.existsSync(oldTrash), false);
    assert.equal(fs.existsSync(freshStaging), true);
    assert.equal(fs.existsSync(freshTrash), true);
    assert.equal(fs.lstatSync(stagingLink).isSymbolicLink(), true);
    assert.equal(fs.existsSync(path.join(linkedOutside, 'marker.txt')), true);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('cleanup action deletes a completed local bundle', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cleanup-'));
  try {
    const bundle = path.join(root, 'bundle');
    fs.mkdirSync(bundle, { recursive: true });
    fs.writeFileSync(path.join(bundle, 'index.html'), '<!doctype html><html><body>done</body></html>');
    const previousPath = path.join(bundle, 'result.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      projectId: 'mock-project-1',
      conversationId: 'mock-conversation-1',
      artifact: { outputDir: bundle, absolutePath: path.join(bundle, 'index.html') }
    }));
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'cleanup-local',
      action: 'cleanup',
      project: { previousResultPath: previousPath },
      cleanup: { mode: 'delete' }
    }, {
      cwd: root,
      resultPath: path.join(root, 'cleanup-result.json'),
      env: { ...process.env, CENTURION_DESIGN_ROOT: root }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.cleanup.localAction, 'deleted');
    assert.equal(fs.existsSync(bundle), false);
    assert.equal(result.cleanup.projectDeleted, false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('trash retention starts when an old bundle is moved to trash', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-trash-retention-'));
  try {
    const bundle = path.join(root, 'old-bundle');
    fs.mkdirSync(bundle, { recursive: true });
    fs.writeFileSync(path.join(bundle, 'index.html'), '<!doctype html><html><body>done</body></html>');
    const previousPath = path.join(bundle, 'result.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      artifact: { outputDir: bundle, absolutePath: path.join(bundle, 'index.html') }
    }));
    const expired = new Date(Date.now() - (2 * 60 * 60 * 1000));
    fs.utimesSync(bundle, expired, expired);

    const cleanupResult = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'trash-old-bundle',
      action: 'cleanup',
      project: { previousResultPath: previousPath },
      cleanup: { mode: 'trash', stagingMaxAgeHours: 1 }
    }, {
      cwd: root,
      resultPath: path.join(root, 'results', 'trash.json'),
      env: { ...process.env, CENTURION_DESIGN_ROOT: root }
    });
    assert.equal(cleanupResult.status, 'done');
    assert.equal(cleanupResult.cleanup.localAction, 'trashed');
    assert(fs.existsSync(cleanupResult.cleanup.trashPath));

    const nextResult = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'after-trash',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false },
      cleanup: { stagingMaxAgeHours: 1 }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(nextResult.status, 'done');
    assert.equal(nextResult.cleanup.staleTrashRemoved, 0);
    assert(fs.existsSync(cleanupResult.cleanup.trashPath));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('cleanup action deletes an OD project only with explicit consent', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cleanup-project-'));
  try {
    const bundle = path.join(root, 'bundle');
    fs.mkdirSync(bundle, { recursive: true });
    const previousPath = path.join(bundle, 'result.json');
    fs.writeFileSync(path.join(bundle, 'index.html'), '<!doctype html><html><body>done</body></html>');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      projectId: 'mock-project-1',
      artifact: { entry: 'index.html', outputDir: bundle, absolutePath: path.join(bundle, 'index.html') }
    }));
    const stateDir = path.join(root, 'state');
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'cleanup-project',
      action: 'cleanup',
      project: { previousResultPath: previousPath },
      cleanup: { mode: 'delete', deleteProject: true }
    }, {
      cwd: root,
      resultPath: path.join(root, 'cleanup-result.json'),
      env: {
        ...process.env,
        CENTURION_DESIGN_ROOT: root,
        MOCK_OD_STATE_DIR: stateDir,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.cleanup.projectDeleted, true);
    assert.equal(fs.readFileSync(path.join(stateDir, 'project-deleted'), 'utf8'), 'mock-project-1');
    assert.equal(fs.existsSync(bundle), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('cleanup rejects a result path inside the bundle and leaves the bundle intact', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cleanup-result-guard-'));
  try {
    const bundle = path.join(root, 'bundle');
    fs.mkdirSync(bundle, { recursive: true });
    const previousPath = path.join(bundle, 'result.json');
    fs.writeFileSync(path.join(bundle, 'index.html'), '<!doctype html><html><body>done</body></html>');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      artifact: { entry: 'index.html', outputDir: bundle, absolutePath: path.join(bundle, 'index.html') }
    }));
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'cleanup-result-guard',
      action: 'cleanup',
      project: { previousResultPath: previousPath }
    }, {
      cwd: root,
      resultPath: path.join(bundle, 'cleanup-result.json'),
      env: { ...process.env, CENTURION_DESIGN_ROOT: root }
    });
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('must be outside')));
    assert.equal(fs.existsSync(bundle), true);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('cleanup rejects a symbolic-link target without touching its destination', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cleanup-symlink-'));
  try {
    const designRoot = path.join(root, 'design');
    const stagingRoot = path.join(designRoot, '.staging');
    const outside = path.join(root, 'outside');
    const targetLink = path.join(stagingRoot, 'preserved-link');
    fs.mkdirSync(stagingRoot, { recursive: true });
    fs.mkdirSync(outside);
    fs.writeFileSync(path.join(outside, 'marker.txt'), 'keep');
    fs.symlinkSync(outside, targetLink, 'dir');
    const resultsRoot = path.join(designRoot, 'results');
    fs.mkdirSync(resultsRoot, { recursive: true });
    const previousPath = path.join(resultsRoot, 'failed-result.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'failed',
      cleanup: { preservedPath: targetLink }
    }));
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'cleanup-symlink',
      action: 'cleanup',
      project: { previousResultPath: previousPath }
    }, {
      cwd: root,
      resultPath: path.join(resultsRoot, 'cleanup-result.json'),
      env: { ...process.env, CENTURION_DESIGN_ROOT: designRoot }
    });
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('symbolic link')));
    assert.equal(fs.lstatSync(targetLink).isSymbolicLink(), true);
    assert.equal(fs.readFileSync(path.join(outside, 'marker.txt'), 'utf8'), 'keep');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('CLI writes cleanup result outside the bundle after deleting it', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cli-cleanup-'));
  try {
    const bundle = path.join(root, 'bundle');
    fs.mkdirSync(bundle, { recursive: true });
    fs.writeFileSync(path.join(bundle, 'index.html'), '<!doctype html><html><body>done</body></html>');
    const previousPath = path.join(bundle, 'result.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      artifact: { outputDir: bundle, absolutePath: path.join(bundle, 'index.html') }
    }));
    const requestPath = path.join(root, 'cleanup-request.json');
    const resultPath = path.join(root, 'results', 'cleanup-result.json');
    fs.writeFileSync(requestPath, JSON.stringify({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'cli-cleanup',
      action: 'cleanup',
      project: { previousResultPath: previousPath },
      cleanup: { mode: 'delete' }
    }));
    const cli = path.join(here, '..', 'bin', 'centurion-design.mjs');
    const run = spawnSync(process.execPath, [cli, '--request', requestPath, '--result', resultPath], {
      encoding: 'utf8',
      env: { ...process.env, CENTURION_DESIGN_ROOT: root }
    });
    assert.equal(run.status, 0, run.stderr || run.stdout);
    const result = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
    assert.equal(result.status, 'done');
    assert.equal(result.cleanup.localAction, 'deleted');
    assert.equal(fs.existsSync(bundle), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('CLI writes a structured failure to --result', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cli-failure-'));
  try {
    const requestPath = path.join(root, 'invalid.json');
    const resultPath = path.join(root, 'result.json');
    fs.writeFileSync(requestPath, '{');
    const cli = path.join(here, '..', 'bin', 'centurion-design.mjs');
    const run = spawnSync(process.execPath, [cli, '--request', requestPath, '--result', resultPath], { encoding: 'utf8' });
    assert.equal(run.status, 1);
    const result = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
    assert.equal(result.status, 'failed');
    assert(result.errors[0].includes('JSON'));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('CLI returns accepted artifact paths on stdout when --result cannot be written', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-cli-result-write-'));
  try {
    const requestPath = path.join(root, 'request.json');
    const resultPath = path.join(root, 'result-target');
    fs.mkdirSync(resultPath);
    fs.writeFileSync(requestPath, JSON.stringify({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'result-write-failure',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    }));
    const cli = path.join(here, '..', 'bin', 'centurion-design.mjs');
    const run = spawnSync(process.execPath, [cli, '--request', requestPath, '--result', resultPath], {
      encoding: 'utf8',
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(run.status, 1);
    const result = JSON.parse(run.stdout);
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('failed to write --result')));
    assert.equal(fs.existsSync(result.artifact.absolutePath), true);
    assert(result.warnings.some((warning) => warning.includes('stdout payload')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}
