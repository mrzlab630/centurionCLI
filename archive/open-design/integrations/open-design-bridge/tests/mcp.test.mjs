import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import test from 'node:test';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const bridgeRoot = path.resolve(here, '..');
const server = path.join(bridgeRoot, 'mcp-server', 'index.mjs');
const mockOd = path.join(here, 'fixtures', 'mock-od.mjs');

function canonicalSchema(file) {
  const schema = JSON.parse(fs.readFileSync(path.join(bridgeRoot, 'schemas', file), 'utf8'));
  delete schema.$schema;
  delete schema.$id;
  delete schema.title;
  return schema;
}

function schemaWithoutInjectedProperty(schema, injectedProperty) {
  delete schema.properties[injectedProperty];
  schema.required = schema.required.filter((property) => property !== injectedProperty);
  return schema;
}

function createClient(root, options = {}) {
  const child = spawn(process.execPath, [server], {
    cwd: root,
    env: {
      ...process.env,
      CENTURION_DESIGN_ROOT: root,
      CENTURION_OD_JOB_ROOT: path.join(root, '.jobs'),
      CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd]),
      MOCK_OD_STATE_DIR: options.stateDir ?? path.join(root, 'state'),
      ...(options.env ?? {})
    },
    stdio: ['pipe', 'pipe', 'pipe']
  });
  const pending = new Map();
  let buffer = '';
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (chunk) => {
    buffer += chunk;
    while (buffer.includes('\n')) {
      const index = buffer.indexOf('\n');
      const line = buffer.slice(0, index).trim();
      buffer = buffer.slice(index + 1);
      if (!line) continue;
      const message = JSON.parse(line);
      pending.get(message.id)?.(message);
      pending.delete(message.id);
    }
  });
  let id = 0;
  return {
    child,
    call(method, params) {
      id += 1;
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`MCP timeout: ${method}`)), 10_000);
        pending.set(id, (message) => {
          clearTimeout(timer);
          resolve(message);
        });
        child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
      });
    }
  };
}

function readJsonLines(stream, count, timeoutMs = 10_000) {
  return new Promise((resolve, reject) => {
    const messages = [];
    let buffer = '';
    const timer = setTimeout(() => reject(new Error(`timed out waiting for ${count} MCP messages`)), timeoutMs);
    stream.setEncoding('utf8');
    stream.on('data', (chunk) => {
      buffer += chunk;
      while (buffer.includes('\n')) {
        const index = buffer.indexOf('\n');
        const line = buffer.slice(0, index).trim();
        buffer = buffer.slice(index + 1);
        if (!line) continue;
        messages.push(JSON.parse(line));
        if (messages.length === count) {
          clearTimeout(timer);
          resolve(messages);
        }
      }
    });
  });
}

test('MCP exposes async design lifecycle and canonical resultPath', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-'));
  const client = createClient(root);
  try {
    const initialized = await client.call('initialize', { protocolVersion: '2024-11-05' });
    assert.equal(initialized.result.serverInfo.name, 'centurion-open-design');
    assert.equal(initialized.result.serverInfo.version, '0.2.1');
    const listed = await client.call('tools/list', {});
    assert.deepEqual(listed.result.tools.map((tool) => tool.name), [
      'search_design_references', 'start_design', 'get_design', 'cleanup_design'
    ]);
    const started = await client.call('tools/call', {
      name: 'start_design',
      arguments: {
        request: {
          requestVersion: 'CENTURION_OD_REQUEST_V1',
          requestId: '../mcp-create',
          action: 'create',
          brief: 'Create a mock landing.',
          orchestrator: { client: 'codex', owner: 'PICTOR' },
          artifact: { outputDir: path.join(root, 'out') },
          screenshot: { enabled: false }
        }
      }
    });
    const startPayload = started.result.structuredContent;
    assert.equal(startPayload.status, 'running');
    let job;
    for (let attempt = 0; attempt < 50; attempt += 1) {
      const response = await client.call('tools/call', { name: 'get_design', arguments: { jobId: startPayload.jobId } });
      job = response.result.structuredContent;
      if (job.status !== 'running') break;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    assert.equal(job.status, 'done');
    assert(fs.existsSync(job.resultPath));
    assert.equal(job.resultPath, path.join(root, '.results', 'mcp-create.json'));
    assert.equal(job.resultPath.startsWith(`${job.result.artifact.outputDir}${path.sep}`), false);
    assert.equal(startPayload.jobId, 'mcp-create');
    assert.equal(job.result.orchestrator.client, 'codex');
    assert.equal(JSON.parse(fs.readFileSync(job.resultPath, 'utf8')).resultVersion, 'CENTURION_OD_RESULT_V1');
  } finally {
    client.child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('MCP discovery schemas preserve canonical request constraints', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-schemas-'));
  const client = createClient(root);
  try {
    const listed = await client.call('tools/list', {});
    const schemas = Object.fromEntries(listed.result.tools.map((tool) => [tool.name, tool.inputSchema]));
    const referenceSchema = schemaWithoutInjectedProperty(canonicalSchema('reference-request.schema.json'), 'requestVersion');
    const productionSchema = canonicalSchema('request.schema.json');

    assert.deepEqual(schemas.search_design_references, referenceSchema);
    assert.deepEqual(schemas.start_design.properties.request, {
      ...productionSchema,
      properties: {
        ...productionSchema.properties,
        action: { enum: ['create', 'revise'] }
      }
    });
    assert.deepEqual(schemas.cleanup_design.properties.request, {
      ...productionSchema,
      properties: {
        ...productionSchema.properties,
        action: { const: 'cleanup' }
      }
    });
    assert.deepEqual(schemas.get_design.properties.jobId, {
      type: 'string',
      minLength: 1,
      maxLength: 128,
      pattern: '^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$'
    });
    for (const tool of ['start_design', 'get_design', 'cleanup_design']) {
      assert.equal(schemas[tool].additionalProperties, false);
    }
  } finally {
    client.child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('MCP returns request ids on tool errors and fails orphaned running jobs', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-errors-'));
  const jobsRoot = path.join(root, '.jobs');
  fs.mkdirSync(jobsRoot, { recursive: true });
  fs.writeFileSync(path.join(jobsRoot, 'orphan.json'), JSON.stringify({
    jobVersion: 'CENTURION_OD_JOB_V1', jobId: 'orphan', status: 'running', result: null, error: null
  }));
  const client = createClient(root);
  try {
    await client.call('initialize', { protocolVersion: '2024-11-05' });
    const orphan = await client.call('tools/call', { name: 'get_design', arguments: { jobId: 'orphan' } });
    assert.equal(orphan.result.structuredContent.status, 'failed');
    const missing = await client.call('tools/call', { name: 'get_design', arguments: { jobId: 'missing' } });
    assert.equal(typeof missing.id, 'number');
    assert.equal(missing.error.code, -32000);
  } finally {
    client.child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('MCP rejects job and result roots outside their reserved design storage', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-roots-'));
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-roots-outside-'));
  const child = spawn(process.execPath, [server], {
    cwd: root,
    env: {
      ...process.env,
      CENTURION_DESIGN_ROOT: root,
      CENTURION_OD_JOB_ROOT: outside,
      CENTURION_OD_RESULT_ROOT: outside
    },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  try {
    const exitCode = await new Promise((resolve) => child.once('exit', resolve));
    assert.notEqual(exitCode, 0);
  } finally {
    child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(outside, { recursive: true, force: true });
  }
});

test('separate MCP server processes atomically claim the same jobId', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-claim-'));
  const first = createClient(root, {
    stateDir: path.join(root, 'state-first'),
    env: { MOCK_OD_WATCH_DELAY_MS: '1000' }
  });
  const second = createClient(root, {
    stateDir: path.join(root, 'state-second'),
    env: { MOCK_OD_WATCH_DELAY_MS: '1000' }
  });
  try {
    await Promise.all([
      first.call('initialize', { protocolVersion: '2024-11-05' }),
      second.call('initialize', { protocolVersion: '2024-11-05' })
    ]);
    const request = {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'shared-job',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    };
    const responses = await Promise.all([
      first.call('tools/call', { name: 'start_design', arguments: { request } }),
      second.call('tools/call', { name: 'start_design', arguments: { request } })
    ]);
    const started = responses.filter((response) => response.result?.structuredContent?.status === 'running');
    const rejected = responses.filter((response) => response.error?.message?.includes('design job already exists'));
    assert.equal(started.length, 1);
    assert.equal(rejected.length, 1);
    const receipt = JSON.parse(fs.readFileSync(path.join(root, '.jobs', 'shared-job.json'), 'utf8'));
    assert.equal(receipt.jobId, 'shared-job');
    assert.equal(receipt.status, 'running');
    const observer = rejected[0] === responses[0] ? first : second;
    const observed = await observer.call('tools/call', { name: 'get_design', arguments: { jobId: 'shared-job' } });
    assert.equal(observed.result.structuredContent.status, 'running');
  } finally {
    first.child.kill('SIGTERM');
    second.child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('job TTL preserves an old receipt owned by a live MCP process', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-live-ttl-'));
  const first = createClient(root, {
    stateDir: path.join(root, 'state-first'),
    env: { MOCK_OD_WATCH_DELAY_MS: '2000', CENTURION_OD_JOB_MAX_AGE_HOURS: '1' }
  });
  const second = createClient(root, {
    stateDir: path.join(root, 'state-second'),
    env: { MOCK_OD_WATCH_DELAY_MS: '2000', CENTURION_OD_JOB_MAX_AGE_HOURS: '1' }
  });
  try {
    await Promise.all([
      first.call('initialize', { protocolVersion: '2024-11-05' }),
      second.call('initialize', { protocolVersion: '2024-11-05' })
    ]);
    const request = {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'live-job',
      action: 'create',
      brief: 'Create a mock landing.',
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    };
    const started = await first.call('tools/call', { name: 'start_design', arguments: { request } });
    assert.equal(started.result.structuredContent.status, 'running');
    const receiptPath = path.join(root, '.jobs', 'live-job.json');
    const expired = new Date(Date.now() - (2 * 60 * 60 * 1000));
    fs.utimesSync(receiptPath, expired, expired);

    const duplicate = await second.call('tools/call', { name: 'start_design', arguments: { request } });
    assert(duplicate.error?.message?.includes('design job already exists'));
    assert.equal(fs.existsSync(receiptPath), true);
    const observed = await second.call('tools/call', { name: 'get_design', arguments: { jobId: 'live-job' } });
    assert.equal(observed.result.structuredContent.status, 'running');
  } finally {
    first.child.kill('SIGTERM');
    second.child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('MCP rejects null and oversized JSONL messages without terminating', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-input-'));
  const child = spawn(process.execPath, [server], {
    cwd: root,
    env: { ...process.env, CENTURION_DESIGN_ROOT: root },
    stdio: ['pipe', 'pipe', 'pipe']
  });
  try {
    const messages = readJsonLines(child.stdout, 3);
    child.stdin.write('null\n');
    child.stdin.write(`${'x'.repeat((1024 * 1024) + 1)}\n`);
    child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id: 7, method: 'ping', params: {} })}\n`);
    const [invalid, oversized, ping] = await messages;
    assert.equal(invalid.error.code, -32600);
    assert.equal(oversized.error.code, -32600);
    assert(oversized.error.message.includes('1048576'));
    assert.deepEqual(ping, { jsonrpc: '2.0', id: 7, result: {} });
    assert.equal(child.exitCode, null);
  } finally {
    child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('MCP validates requests before claiming jobs and bounds active work', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-open-design-mcp-capacity-'));
  const client = createClient(root, {
    stateDir: path.join(root, 'state'),
    env: { MOCK_OD_WATCH_DELAY_MS: '2000', CENTURION_OD_MAX_CONCURRENT_JOBS: '1' }
  });
  try {
    await client.call('initialize', { protocolVersion: '2024-11-05' });
    const invalid = await client.call('tools/call', {
      name: 'start_design',
      arguments: { request: { requestVersion: 'CENTURION_OD_REQUEST_V1', action: 'create', brief: '' } }
    });
    assert(invalid.error?.message.includes('request.brief'));
    assert.equal(fs.existsSync(path.join(root, '.jobs')), false);

    const request = {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'first-job',
      action: 'create',
      brief: 'Create a landing.',
      artifact: { outputDir: path.join(root, 'out-first') },
      screenshot: { enabled: false }
    };
    const first = await client.call('tools/call', { name: 'start_design', arguments: { request } });
    assert.equal(first.result.structuredContent.status, 'running');
    const second = await client.call('tools/call', {
      name: 'start_design',
      arguments: { request: { ...request, requestId: 'second-job', artifact: { outputDir: path.join(root, 'out-second') } } }
    });
    assert(second.error?.message.includes('active design job limit reached: 1'));
    const invalidId = await client.call('tools/call', { name: 'get_design', arguments: { jobId: '../first-job' } });
    assert(invalidId.error?.message.includes('invalid jobId'));
  } finally {
    client.child.kill('SIGTERM');
    fs.rmSync(root, { recursive: true, force: true });
  }
});
