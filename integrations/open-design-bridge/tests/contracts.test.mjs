import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { normalizedRequest, validateRequest } from '../lib/contracts.mjs';

test('accepts a minimal create request and applies deterministic defaults', () => {
  const request = normalizedRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    requestId: 'test-create',
    action: 'create',
    brief: 'Create a landing page.'
  }, { cwd: '/tmp' });
  assert.equal(request.executor.agent, 'codex');
  assert.equal(request.executor.plugin, 'design-system-creative');
  assert.equal(request.artifact.entry, 'index.html');
  assert.equal(request.screenshot.viewport.width, 1440);
  assert.equal(request.artifact.outputDir, '/tmp/.centurion/design/test-create');
});

test('defaults output into the configured design root', () => {
  const request = normalizedRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    requestId: 'custom-root',
    action: 'create',
    brief: 'Create a landing page.'
  }, { cwd: '/tmp/work', outputRoot: '/tmp/custom-design-root' });
  assert.equal(request.artifact.outputDir, '/tmp/custom-design-root/custom-root');
});

test('rejects revise without previous result or project id', () => {
  const failures = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'revise',
    brief: 'Improve the hero.'
  });
  assert(failures.some((failure) => failure.includes('previousResultPath')));
});

test('rejects unsafe artifact paths', () => {
  const failures = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'create',
    brief: 'Create a page.',
    artifact: { entry: '../outside.html' }
  });
  assert(failures.some((failure) => failure.includes('safe relative HTML path')));
});

test('rejects invalid timeout values', () => {
  const failures = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'create',
    brief: 'Create a page.',
    executor: { timeoutMs: 'soon' }
  });
  assert(failures.some((failure) => failure.includes('executor.timeoutMs')));
});

test('rejects non-loopback daemon URLs and broad capabilities', () => {
  const failures = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'create',
    brief: 'Create a page.',
    daemon: { url: 'https://example.com' },
    executor: { grantCapabilities: ['fs:write', 'network'] }
  });
  assert(failures.some((failure) => failure.includes('loopback')));
  assert(failures.some((failure) => failure.includes('may only include')));
});

test('rejects output paths outside the configured design root', () => {
  assert.throws(() => normalizedRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    requestId: 'outside',
    action: 'create',
    brief: 'Create a page.',
    artifact: { outputDir: '/var/tmp/outside' }
  }, { cwd: '/tmp/work', outputRoot: '/tmp/work/.centurion/design' }), /must stay within/);
});

test('cleanup requires a previous result and validates lifecycle options', () => {
  const missing = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'cleanup'
  });
  assert(missing.some((failure) => failure.includes('previousResultPath')));

  const invalid = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'create',
    brief: 'Create a page.',
    cleanup: { onFailure: 'forever', mode: 'erase', stagingMaxAgeHours: 0 }
  });
  assert(invalid.some((failure) => failure.includes('onFailure')));
  assert(invalid.some((failure) => failure.includes('mode')));
  assert(invalid.some((failure) => failure.includes('stagingMaxAgeHours')));
});

test('rejects nested scalar types that disagree with the request schema', () => {
  const failures = validateRequest({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    action: 'create',
    brief: 'Create a page.',
    project: { name: 42, projectId: '' },
    executor: { agent: [], model: 7, plugin: '' },
    artifact: { outputDir: '' },
    screenshot: { enabled: 'yes', fullPage: 1, allowNetwork: null },
    daemon: { ensureRunning: 'yes' }
  });
  for (const field of [
    'project.name', 'project.projectId', 'executor.agent', 'executor.model',
    'executor.plugin', 'artifact.outputDir', 'screenshot.enabled',
    'screenshot.fullPage', 'screenshot.allowNetwork', 'daemon.ensureRunning'
  ]) {
    assert(failures.some((failure) => failure.includes(field)), `missing validation for ${field}`);
  }
});

test('result schema rejects undeclared top-level properties', () => {
  const schema = JSON.parse(fs.readFileSync(new URL('../schemas/result.schema.json', import.meta.url), 'utf8'));
  assert.equal(schema.additionalProperties, false);
  assert(schema.properties.action.enum.includes('cleanup'));
});

test('cleanup rejects previous results with inconsistent artifact paths', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-contract-cleanup-'));
  try {
    const previousPath = path.join(root, 'forged-result.json');
    fs.writeFileSync(previousPath, JSON.stringify({
      resultVersion: 'CENTURION_OD_RESULT_V1',
      status: 'done',
      artifact: {
        entry: 'index.html',
        outputDir: path.join(root, 'bundle'),
        absolutePath: path.join(root, 'different-bundle', 'index.html')
      }
    }));
    assert.throws(() => normalizedRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      action: 'cleanup',
      project: { previousResultPath: previousPath }
    }, { cwd: root, outputRoot: root }), /must match/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
