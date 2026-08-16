#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const kitRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-od-smoke-'));
try {
  const requestPath = path.join(tempRoot, 'request.json');
  const resultPath = path.join(tempRoot, 'result.json');
  fs.writeFileSync(requestPath, JSON.stringify({
    requestVersion: 'CENTURION_OD_REQUEST_V1',
    requestId: 'smoke-create',
    action: 'create',
    brief: 'Create a compact landing page.',
    artifact: { outputDir: path.join(tempRoot, 'out') },
    screenshot: { enabled: false }
  }));
  const mockOd = path.join(kitRoot, 'tests', 'fixtures', 'mock-od.mjs');
  const result = spawnSync(process.execPath, [
    path.join(kitRoot, 'bin', 'centurion-design.mjs'),
    '--request', requestPath,
    '--result', resultPath
  ], {
    cwd: kitRoot,
    encoding: 'utf8',
    env: {
      ...process.env,
      MOCK_OD_STATE_DIR: path.join(tempRoot, 'state'),
      CENTURION_DESIGN_ROOT: tempRoot,
      CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
    }
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const payload = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
  assert.equal(payload.status, 'done');
  assert(fs.existsSync(payload.artifact.absolutePath));
  assert(payload.proof.every((entry) => entry.result === 'passed'));
  const referenceHelp = spawnSync(process.execPath, [path.join(kitRoot, 'bin', 'centurion-reference.mjs'), '--help'], { encoding: 'utf8' });
  assert.equal(referenceHelp.status, 0, referenceHelp.stderr || referenceHelp.stdout);
  assert(referenceHelp.stdout.includes('centurion-reference'), 'reference CLI help missing');
  assert(fs.existsSync(path.join(kitRoot, 'mcp-server', 'index.mjs')));
  process.stdout.write(`${JSON.stringify({ status: 'pass', resultPath, artifactPath: payload.artifact.absolutePath }, null, 2)}\n`);
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}
