#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const adapter = require('./monid-adapter.js');

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'monid-adapter-test-'));
const argvLog = path.join(tempDir, 'argv.jsonl');
const envLog = path.join(tempDir, 'env.json');
const fakeCli = path.join(tempDir, 'fake-monid.js');
const isolatedHome = fs.mkdtempSync(path.join(os.tmpdir(), 'monid-parent-home-'));
const isolatedConfig = fs.mkdtempSync(path.join(os.tmpdir(), 'monid-parent-config-'));
const adapterPath = path.resolve(__dirname, 'monid-adapter.js');
let fixtureMode = 'discover';
let runInvocationCount = 0;
let lastTimeoutChild;

fs.writeFileSync(fakeCli, `#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const args = process.argv.slice(2);
fs.appendFileSync(${JSON.stringify(argvLog)}, JSON.stringify(args) + '\\n');
fs.writeFileSync(${JSON.stringify(envLog)}, JSON.stringify({HOME:process.env.HOME, XDG_CONFIG_HOME:process.env.XDG_CONFIG_HOME, XDG_CACHE_HOME:process.env.XDG_CACHE_HOME, SECRET_TOKEN:process.env.SECRET_TOKEN || null}));
const mode = process.env.FIXTURE_MODE || 'discover';
if (mode === 'malformed') process.stdout.write('not-json');
else if (mode === 'nonzero') { process.stderr.write('Bearer fixture-secret-12345678'); process.exit(7); }
else if (mode === 'timeout' && args[0] === 'run') setTimeout(() => process.stdout.write(JSON.stringify({status:'COMPLETED'})), 500);
else if (mode === 'sigterm-ignore' && args[0] === 'run') { process.on('SIGTERM', () => {}); setInterval(() => {}, 1000); }
else if (args[0] === 'discover') process.stdout.write(JSON.stringify({items:[{url:'https://candidate.example/a'},{url:'http://127.0.0.1/private'},{url:'https://safe.example/path?token=secret'}]}));
else if (args[0] === 'inspect') process.stdout.write(JSON.stringify({provider:args[2], endpoint:args[4], estimatedCost: mode === 'negative-cost' ? -1 : mode === 'invalid-cost' ? '0.02' : mode === 'unverifiable' ? null : 0.02, currency: mode === 'currency-mismatch' ? 'EUR' : 'USD', schema:{type:'object'}}));
else if (args[0] === 'run') {
  if (mode === 'blocked') process.stdout.write(JSON.stringify({runId:'run-blocked',status:'BLOCKED',controls:['review-cost']}));
  else if (mode === 'failed') process.stdout.write(JSON.stringify({runId:'run-failed',status:'FAILED'}));
  else if (mode === 'unknown') process.stdout.write(JSON.stringify({runId:'run-unknown',status:'MYSTERY'}));
  else if (mode === 'completed-negative-cost') process.stdout.write(JSON.stringify({runId:'run-complete',status:'COMPLETED',cost:-0.01,currency:'USD'}));
  else if (mode === 'completed-invalid-cost') process.stdout.write(JSON.stringify({runId:'run-complete',status:'COMPLETED',cost:'0.02',currency:'USD'}));
  else if (mode === 'completed-currency-mismatch') process.stdout.write(JSON.stringify({runId:'run-complete',status:'COMPLETED',cost:0.02,currency:'EUR'}));
  else if (mode === 'completed-over-cost') process.stdout.write(JSON.stringify({runId:'run-complete',status:'COMPLETED',cost:0.06,currency:'USD'}));
  else if (mode === 'completed') process.stdout.write(JSON.stringify({runId:'run-complete',status:'COMPLETED',cost:0.02,currency:'USD',result:{url:'https://safe.example/result'}}));
  else process.stdout.write(JSON.stringify({runId:'run-pending',status:'RUNNING',cost:0.01}));
} else if (args[0] === 'runs' && args[1] === 'get') {
  if (mode === 'poll-completed-negative-cost') process.stdout.write(JSON.stringify({runId:'run-pending',status:'COMPLETED',cost:-0.03,currency:'USD'}));
  else if (mode === 'poll-completed-invalid-cost') process.stdout.write(JSON.stringify({runId:'run-pending',status:'COMPLETED',cost:'0.03',currency:'USD'}));
  else if (mode === 'poll-completed-currency-mismatch') process.stdout.write(JSON.stringify({runId:'run-pending',status:'COMPLETED',cost:0.03,currency:'EUR'}));
  else if (mode === 'poll-completed-over-cost') process.stdout.write(JSON.stringify({runId:'run-pending',status:'COMPLETED',cost:0.06,currency:'USD'}));
  else if (mode === 'poll-completed') process.stdout.write(JSON.stringify({runId:'run-pending',status:'COMPLETED',cost:0.03,currency:'USD',result:{url:'https://safe.example/result'}}));
  else if (mode === 'poll-blocked') process.stdout.write(JSON.stringify({runId:'run-pending',status:'BLOCKED',controls:['manual-review']}));
  else if (mode === 'poll-unknown') process.stdout.write(JSON.stringify({runId:'run-pending',status:'MYSTERY'}));
  else process.stdout.write(JSON.stringify({runId:'run-pending',status:'RUNNING'}));
}
`, { mode: 0o700 });

function readArgv() { return fs.existsSync(argvLog) ? fs.readFileSync(argvLog, 'utf8').trim().split('\n').filter(Boolean).map((line) => JSON.parse(line)) : []; }

function fixtureSpawn(binary, args, options) {
  assert.equal(binary, process.execPath);
  assert.equal(options.shell, false);
  if (args[0] === 'run') runInvocationCount += 1;
  const env = { ...options.env, FIXTURE_MODE: fixtureMode };
  const child = spawn(process.execPath, [fakeCli, ...args], { ...options, env });
  if (fixtureMode === 'sigterm-ignore' && args[0] === 'run') lastTimeoutChild = child;
  return child;
}

const baseOptions = (extra = {}) => ({ enable: true, provider: 'demo', endpoint: '/v1/run', input: '{"text":"safe"}', authorization: JSON.stringify({ provider: 'demo', endpoint: '/v1/run', maxCost: 0.05, currency: 'USD', expiresAt: new Date(Date.now() + 60000).toISOString() }), wait: true, 'confirm-cost': true, 'poll-interval-ms': '0', ...extra });
const deps = { binary: process.execPath, spawnImpl: fixtureSpawn };

async function rejectsCode(action, code) { await assert.rejects(action, (error) => error?.result?.error?.code === code); }

function throwsCode(action, code) { assert.throws(action, (error) => error?.result?.error?.code === code); }

async function run() {
  const oldHome = process.env.HOME; const oldConfig = process.env.XDG_CONFIG_HOME; const oldSecret = process.env.SECRET_TOKEN;
  process.env.HOME = isolatedHome; process.env.XDG_CONFIG_HOME = isolatedConfig; process.env.SECRET_TOKEN = 'parent-secret-value';
  fs.rmSync(argvLog, { force: true });
  assert.equal(await adapter.main(['discover', '--query', 'no spawn']), 1);
  assert.deepEqual(readArgv(), []);

  fixtureMode = 'discover';
  assert.deepEqual(adapter.parseArgs(['discover', '--query', 'bounded', '--limit', '5', '--enable']), { command: 'discover', options: { query: 'bounded', limit: '5', enable: true } });
  throwsCode(() => adapter.parseArgs(['discover', '--query', 'x', '--wait', '--enable']), 'INVALID_ARGUMENT');
  throwsCode(() => adapter.parseArgs(['inspect', '--provider', 'demo', '--endpoint', '/v1/schema', '--limit', '2', '--enable']), 'INVALID_ARGUMENT');
  await rejectsCode(() => adapter.runCommand('discover', { enable: true, query: 'bounded', limit: '11' }, deps), 'INVALID_ARGUMENT');
  const beforeInapplicable = readArgv().length;
  await rejectsCode(() => adapter.runCommand('discover', { enable: true, query: 'x', wait: true }, deps), 'INVALID_ARGUMENT');
  assert.equal(readArgv().length, beforeInapplicable);
  let result = await adapter.runCommand('discover', { enable: true, query: 'a ; quoted', limit: '5' }, deps);
  assert.deepEqual(readArgv().at(-1), ['discover', '-q', 'a ; quoted', '--limit', '5', '--json']);
  assert.deepEqual(result.provenance, { kind: 'candidate-unverified', urls: ['https://candidate.example/a'] });
  assert.equal(result.data.items[2].url, 'https://safe.example/path?token=[REDACTED]');
  const childEnv = JSON.parse(fs.readFileSync(envLog, 'utf8'));
  assert.notEqual(childEnv.HOME, isolatedHome); assert.notEqual(childEnv.XDG_CONFIG_HOME, isolatedConfig); assert.equal(childEnv.SECRET_TOKEN, null);

  result = await adapter.runCommand('inspect', { enable: true, provider: 'demo.provider', endpoint: '/v1/schema' }, deps);
  assert.deepEqual(readArgv().at(-1), ['inspect', '-p', 'demo.provider', '-e', '/v1/schema', '--json']);
  assert.equal(result.data.provider, 'demo.provider');

  const beforeConfirmation = readArgv().length;
  await rejectsCode(() => adapter.runCommand('run', { enable: true, provider: 'demo', endpoint: '/v1/run', input: '{"text":"x"}', wait: true }, deps), 'COST_CONFIRMATION_REQUIRED');
  assert.equal(readArgv().length, beforeConfirmation);
  const beforeAuthValidation = readArgv().length;
  await rejectsCode(() => adapter.runCommand('run', baseOptions({ authorization: JSON.stringify({ provider: 'other', endpoint: '/v1/run', maxCost: 1, currency: 'USD', expiresAt: new Date(Date.now() + 60000).toISOString() }) }), deps), 'COST_AUTH_INVALID');
  assert.equal(readArgv().length, beforeAuthValidation);
  await rejectsCode(() => adapter.runCommand('run', baseOptions({ authorization: JSON.stringify({ provider: 'demo', endpoint: '/v1/run', maxCost: 0.01, currency: 'USD', expiresAt: new Date(Date.now() + 60000).toISOString() }) }), deps), 'COST_UNVERIFIABLE');
  await rejectsCode(() => adapter.runCommand('run', baseOptions({ authorization: JSON.stringify({ provider: 'demo', endpoint: '/v1/run', maxCost: 1, currency: 'USD', expiresAt: new Date(Date.now() - 1000).toISOString() }) }), deps), 'COST_AUTH_EXPIRED');
  fixtureMode = 'currency-mismatch'; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'COST_UNVERIFIABLE');
  fixtureMode = 'unverifiable'; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'COST_UNVERIFIABLE');
  fixtureMode = 'negative-cost'; const beforeNegativeRuns = runInvocationCount; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'COST_UNVERIFIABLE'); assert.equal(runInvocationCount, beforeNegativeRuns);
  fixtureMode = 'invalid-cost'; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'COST_UNVERIFIABLE'); assert.equal(runInvocationCount, beforeNegativeRuns);

  const beforeInvalidPollBounds = readArgv().length;
  for (const [field, value] of [['poll-timeout-ms', '0'], ['max-polls', '0'], ['poll-interval-ms', '-1']]) {
    await rejectsCode(() => adapter.runCommand('run', baseOptions({ [field]: value }), deps), 'INVALID_ARGUMENT');
  }
  assert.equal(readArgv().length, beforeInvalidPollBounds);

  fixtureMode = 'completed'; result = await adapter.runCommand('run', baseOptions(), deps);
  const completedArgs = readArgv().filter((entry) => entry[0] === 'run').at(-1);
  assert.deepEqual(completedArgs.slice(0, 8), ['run', '-p', 'demo', '-e', '/v1/run', '-i', '{"text":"safe"}', '--wait']);
  assert.equal(result.status, 'COMPLETED');
  for (const mode of ['completed-negative-cost', 'completed-invalid-cost', 'completed-currency-mismatch', 'completed-over-cost']) {
    fixtureMode = mode;
    await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'COST_UNVERIFIABLE');
  }
  fixtureMode = 'blocked'; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'MONID_BLOCKED');
  const blockedTail = readArgv().slice(-2); assert.equal(blockedTail.filter((entry) => entry[0] === 'runs').length, 0);
  fixtureMode = 'failed'; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'MONID_TERMINAL_FAILURE');
  fixtureMode = 'unknown'; await rejectsCode(() => adapter.runCommand('run', baseOptions(), deps), 'MONID_UNKNOWN_STATUS');
  fixtureMode = 'poll-completed'; result = await adapter.runCommand('run', baseOptions({ 'max-polls': '2' }), deps); assert.equal(result.status, 'COMPLETED');
  const pollArgs = readArgv().at(-1); assert.deepEqual(pollArgs, ['runs', 'get', '-r', 'run-pending', '--wait', '--json']);
  for (const mode of ['poll-completed-negative-cost', 'poll-completed-invalid-cost', 'poll-completed-currency-mismatch', 'poll-completed-over-cost']) {
    fixtureMode = mode;
    await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'max-polls': '2' }), deps), 'COST_UNVERIFIABLE');
  }
  fixtureMode = 'poll-unknown'; await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'max-polls': '2' }), deps), 'MONID_UNKNOWN_STATUS');
  fixtureMode = 'poll-blocked'; await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'max-polls': '2' }), deps), 'MONID_BLOCKED');
  fixtureMode = 'discover'; await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'max-polls': '2' }), deps), 'MONID_POLL_LIMIT');

  const pollTimeouts = [];
  const boundedPollDeps = {
    binary: process.execPath,
    spawnJson: async (args, timeout) => {
      if (args[0] === 'inspect') return { payload: { estimatedCost: 0.02, currency: 'USD' } };
      if (args[0] === 'run') return { payload: { runId: 'bounded-run', status: 'RUNNING' } };
      pollTimeouts.push(timeout);
      await new Promise((resolve) => setTimeout(resolve, 25));
      return { payload: { runId: 'bounded-run', status: 'RUNNING' } };
    }
  };
  await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'timeout-ms': '1000', 'poll-timeout-ms': '20', 'max-polls': '2' }), boundedPollDeps), 'MONID_POLL_TIMEOUT');
  assert.equal(pollTimeouts.length, 1);
  assert.ok(pollTimeouts[0] <= 20);

  fixtureMode = 'timeout'; const beforeTimeoutStarts = runInvocationCount; await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'timeout-ms': '200' }), deps), 'MONID_TIMEOUT'); assert.equal(runInvocationCount, beforeTimeoutStarts + 1);
  fixtureMode = 'sigterm-ignore'; lastTimeoutChild = undefined; await rejectsCode(() => adapter.runCommand('run', baseOptions({ 'timeout-ms': '200' }), deps), 'MONID_TIMEOUT');
  assert.ok(lastTimeoutChild);
  await new Promise((resolve, reject) => {
    const deadline = Date.now() + 1000;
    const check = () => {
      if (lastTimeoutChild.exitCode !== null || lastTimeoutChild.signalCode !== null) resolve();
      else if (Date.now() >= deadline) reject(new Error('SIGTERM-ignoring fixture remained alive after escalation window.'));
      else setTimeout(check, 10);
    };
    check();
  });
  assert.equal(lastTimeoutChild.signalCode, 'SIGKILL');
  await rejectsCode(() => adapter.runCommand('discover', { enable: true, query: 'x' }, { ...deps, spawnImpl: () => { throw new Error('fixture spawn failure'); } }), 'MONID_SPAWN_FAILED');
  await rejectsCode(() => adapter.runCommand('discover', { enable: true, query: 'x' }, { ...deps, spawnJson: async () => ({ payload: adapter.parseJsonValue('{"a":1,"a":2}', 'Monid output') }) }), 'INVALID_JSON_INPUT');
  fixtureMode = 'malformed'; await rejectsCode(() => adapter.runCommand('discover', { enable: true, query: 'x' }, deps), 'INVALID_JSON_INPUT');
  assert.equal(adapter.validateCandidateUrl('https://user:pass@example.com/a'), false);
  assert.equal(adapter.validateCandidateUrl('https://user%3Apass@example.com/a'), false);
  assert.equal(adapter.validateCandidateUrl('https://example.com/?to%2565n=secret'), false);
  assert.equal(adapter.validateCandidateUrl('https://example.com/a?api_key=secret'), false);
  assert.equal(adapter.validateCandidateUrl('https://example.com/a?state=sk%5FencodedSecret123'), false);
  assert.equal(adapter.validateCandidateUrl('https://example.com/a'), true);
  const forbiddenLiteralUrls = [
    'http://10.0.0.1/x',
    'http://172.16.0.1/x',
    'http://192.168.1.1/x',
    'http://127.0.0.1/x',
    'http://169.254.169.254/x',
    'http://0.0.0.0/x',
    'http://100.64.0.1/x',
    'http://192.0.2.1/x',
    'http://198.18.0.1/x',
    'http://198.51.100.1/x',
    'http://203.0.113.1/x',
    'http://224.0.0.1/x',
    'http://240.0.0.1/x',
    'http://127.0.0.1./x',
    'http://localhost./x',
    'http://foo.localhost./x',
    'http://metadata.google.internal./x',
    'http://instance-data.ec2.internal./x',
    'http://2130706433/x',
    'http://[::]/x',
    'http://[::1]/x',
    'http://[fc00::1]/x',
    'http://[fe80::1]/x',
    'http://[ff02::1]/x',
    'http://[::ffff:127.0.0.1]/x',
    'http://[::ffff:192.0.2.1]/x',
    'http://[2001:db8::1]/x',
    'http://[2001:2::1]/x',
    'http://[2001:1::1]/x',
    'http://[2001:3::1]/x',
    'http://[2001:4:112::1]/x',
    'http://[2002::1]/x',
    'http://[64:ff9b::1]/x',
    'http://[64:ff9b::192.0.2.1]/x',
    'http://[64:ff9b:1::1]/x',
    'http://[100::1]/x'
  ];
  for (const url of forbiddenLiteralUrls) assert.equal(adapter.validateCandidateUrl(url), false, url);
  for (const url of ['http://example.com:80/x', 'https://example.com:443/x', 'http://example.com:00080/x', 'https://example.com:000443/x', 'http://example.com:8080/x']) {
    assert.equal(adapter.validateCandidateUrl(url), false, url);
  }
  assert.equal(adapter.validateCandidateUrl('https://example.com/x'), true);
  assert.equal(adapter.validateCandidateUrl('https://8.8.8.8/dns'), true);
  assert.equal(adapter.validateCandidateUrl('https://[2001:4860:4860::8888]/dns'), true);
  assert.equal(adapter.validateCandidateUrl('https://[::ffff:8.8.8.8]/dns'), true);
  assert.equal(adapter.validateCandidateUrl('https://[2001:30::1]/x'), false);
  fixtureMode = 'nonzero'; await rejectsCode(() => adapter.runCommand('discover', { enable: true, query: 'x' }, deps), 'MONID_EXIT_NONZERO');
  const sanitized = adapter.sanitize({ token: 'secret-value', nested: 'Bearer abc.def.ghi', url: 'https://example.com/path?token=secret-value&api_key=another-secret&ok=visible' });
  assert.equal(JSON.stringify(sanitized).includes('secret-value'), false);
  assert.equal(JSON.stringify(sanitized).includes('another-secret'), false);
  assert.equal(sanitized.url, 'https://example.com/path?token=[REDACTED]&api_key=[REDACTED]&ok=visible');
  const encoded = adapter.sanitize({ url: 'https://example.com/path?state=sk%5FencodedSecret123&next=https%3A%2F%2Fexample.com%2F%3Ftoken%3Dsecret12345#access_token=fragmentSecret12345' });
  assert.equal(encoded.url, 'https://example.com/path?state=[REDACTED]&next=[REDACTED]');
  assert.deepEqual(adapter.candidateProvenance({ url: 'https://example.com/path#access_token=fragmentSecret12345' }), { kind: 'candidate-unverified', urls: ['https://example.com/path'] });
  let deeplyEncodedCredential = 'token=deepEncodedSecret12345';
  for (let depth = 0; depth < 4; depth += 1) deeplyEncodedCredential = encodeURIComponent(deeplyEncodedCredential);
  const deeplyEncoded = adapter.sanitize({ url: `https://example.com/path?state=${deeplyEncodedCredential}` });
  assert.equal(deeplyEncoded.url, 'https://example.com/path?state=[REDACTED]');
  assert.equal(JSON.stringify(deeplyEncoded).includes(deeplyEncodedCredential), false);
  assert.deepEqual(adapter.candidateProvenance({ url: `https://example.com/path?state=${deeplyEncodedCredential}` }), { kind: 'candidate-unverified', urls: ['https://example.com/path?state=[REDACTED]'] });
  const leadingWhitespaceUrl = '\t  https://example.com/path?ok=visible#access_token=fragmentSecret12345';
  assert.equal(adapter.sanitize({ url: leadingWhitespaceUrl }).url, 'https://example.com/path?ok=visible');
  for (const authority of ['user:pass@example.com', 'user%3Apass@example.com', 'user%253Apass@example.com', 'user%253Apass%2540example.com', 'sk_fixtureSecret123.example.com']) {
    const url = `https://${authority}/a?ok=visible#fragment`;
    assert.equal(adapter.sanitize(url), '[REDACTED]');
    assert.deepEqual(adapter.candidateProvenance({ nested: [url] }), { kind: 'candidate-unverified', urls: [] });
  }
  for (const key of ['to%2565n', 'to%256ben', 'api%255fkey', 'to%ZZ%256ben', `to%${'25'.repeat(12)}6ben`]) {
    const url = `https://example.com/?${key}=fixture`;
    assert.equal(adapter.validateCandidateUrl(url), false, key);
    assert.deepEqual(adapter.candidateProvenance({ url }), { kind: 'candidate-unverified', urls: [] });
  }
  assert.equal(adapter.validateCandidateUrl('https://example.com/?%71=visible'), true);
  assert.deepEqual(adapter.candidateProvenance({ url: leadingWhitespaceUrl }), { kind: 'candidate-unverified', urls: ['https://example.com/path?ok=visible'] });
  assert.equal(adapter.sanitize({ text: ' \tplain text #fragment' }).text, ' \tplain text #fragment');

  if (oldHome === undefined) delete process.env.HOME; else process.env.HOME = oldHome;
  if (oldConfig === undefined) delete process.env.XDG_CONFIG_HOME; else process.env.XDG_CONFIG_HOME = oldConfig;
  if (oldSecret === undefined) delete process.env.SECRET_TOKEN; else process.env.SECRET_TOKEN = oldSecret;
  process.stdout.write('PASS hardened Monid adapter offline adversarial coverage\n');
}

run().finally(() => fs.rmSync(tempDir, { recursive: true, force: true })).catch((error) => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
