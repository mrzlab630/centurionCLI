#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { runDesignRequest } from '../lib/bridge.mjs';
import { validateRequest } from '../lib/contracts.mjs';
import { MAX_JSON_INPUT_BYTES } from '../lib/json-input.mjs';
import { searchDesignReferences } from '../lib/references.mjs';
import { assertPathWithinRoot } from '../lib/path-safety.mjs';
import { AnchoredRoot } from '../lib/descriptor-fs.mjs';

const jobs = new Map();
const designRoot = path.resolve(process.env.CENTURION_DESIGN_ROOT ?? path.join(process.cwd(), '.centurion', 'design'));
const jobBase = path.join(designRoot, '.jobs');
const resultBase = path.join(designRoot, '.results');
const jobRoot = path.resolve(process.env.CENTURION_OD_JOB_ROOT ?? jobBase);
const resultRoot = path.resolve(process.env.CENTURION_OD_RESULT_ROOT ?? resultBase);
const jobMaxAgeHours = Number(process.env.CENTURION_OD_JOB_MAX_AGE_HOURS ?? 168);
const maxConcurrentJobs = Number(process.env.CENTURION_OD_MAX_CONCURRENT_JOBS ?? 4);
const MAX_JOB_RECEIPT_BYTES = 4 * 1024 * 1024;
const JOB_ID_PATTERN = '^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$';
const JOB_ID_RE = new RegExp(JOB_ID_PATTERN);
if (!Number.isInteger(maxConcurrentJobs) || maxConcurrentJobs < 1 || maxConcurrentJobs > 32) {
  throw new Error('CENTURION_OD_MAX_CONCURRENT_JOBS must be an integer from 1 to 32');
}
assertPathWithinRoot(designRoot, jobRoot, { allowRoot: false, label: 'CENTURION_OD_JOB_ROOT', rejectFinalSymlink: true });
assertPathWithinRoot(designRoot, resultRoot, { allowRoot: false, label: 'CENTURION_OD_RESULT_ROOT', rejectFinalSymlink: true });
assertPathWithinRoot(jobBase, jobRoot, { label: 'CENTURION_OD_JOB_ROOT', rejectFinalSymlink: true });
assertPathWithinRoot(resultBase, resultRoot, { label: 'CENTURION_OD_RESULT_ROOT', rejectFinalSymlink: true });
const storageRoot = new AnchoredRoot(designRoot, { create: true });
const jobRootRelative = storageRoot.relative(jobRoot);
const resultRootRelative = storageRoot.relative(resultRoot);

function canonicalSchema(file) {
  const schema = JSON.parse(fs.readFileSync(new URL(`../schemas/${file}`, import.meta.url), 'utf8'));
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

const referenceToolSchema = schemaWithoutInjectedProperty(canonicalSchema('reference-request.schema.json'), 'requestVersion');
const productionRequestSchema = canonicalSchema('request.schema.json');
const startRequestSchema = structuredClone(productionRequestSchema);
startRequestSchema.properties.action = { enum: ['create', 'revise'] };
const cleanupRequestSchema = structuredClone(productionRequestSchema);
cleanupRequestSchema.properties.action = { const: 'cleanup' };

const tools = [
  {
    name: 'search_design_references',
    description: 'Search curated web-design references and return a temporary manifest for Open Design production.',
    inputSchema: referenceToolSchema
  },
  {
    name: 'start_design',
    description: 'Start an asynchronous proof-first Open Design create or revise job. Returns immediately with a jobId.',
    inputSchema: {
      type: 'object',
      required: ['request'],
      properties: { request: startRequestSchema },
      additionalProperties: false
    }
  },
  {
    name: 'get_design',
    description: 'Read the current state or final JSON result of an Open Design job.',
    inputSchema: {
      type: 'object',
      required: ['jobId'],
      properties: {
        jobId: { type: 'string', minLength: 1, maxLength: 128, pattern: JOB_ID_PATTERN }
      },
      additionalProperties: false
    }
  },
  {
    name: 'cleanup_design',
    description: 'Run a bounded cleanup request. Open Design project deletion still requires cleanup.deleteProject=true from an explicit user decision.',
    inputSchema: {
      type: 'object',
      required: ['request'],
      properties: { request: cleanupRequestSchema },
      additionalProperties: false
    }
  }
];

function isWithin(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function jobPath(jobId) {
  const safe = String(jobId);
  if (!JOB_ID_RE.test(safe)) throw new Error('invalid jobId');
  const target = path.join(jobRoot, `${safe}.json`);
  if (!isWithin(jobRoot, target)) throw new Error('invalid jobId');
  return target;
}

function normalizeJobId(value) {
  const safe = String(value).replace(/[^A-Za-z0-9._-]/g, '-').replace(/^[.-]+|[.-]+$/g, '');
  return safe || `design-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function processStartTime(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    const closingParenthesis = stat.lastIndexOf(')');
    if (closingParenthesis < 0) return null;
    return stat.slice(closingParenthesis + 2).trim().split(/\s+/)[19] ?? null;
  } catch {
    return null;
  }
}

function ownerIsAlive(owner) {
  return Number.isInteger(owner?.pid)
    && typeof owner.startTime === 'string'
    && processStartTime(owner.pid) === owner.startTime;
}

function sweepJobs() {
  if (!storageRoot.exists(jobRootRelative) || !Number.isFinite(jobMaxAgeHours) || jobMaxAgeHours < 1) return 0;
  const cutoff = Date.now() - jobMaxAgeHours * 60 * 60 * 1000;
  let removed = 0;
  const jobsDirectory = storageRoot.openDirectory(jobRootRelative);
  try {
    for (const entry of jobsDirectory.entries()) {
      if (!entry.isFile() || entry.isSymbolicLink() || !entry.name.endsWith('.json')) continue;
      const stats = jobsDirectory.lstat(entry.name);
      if (!stats?.isFile() || stats.isSymbolicLink() || stats.mtimeMs >= cutoff) continue;
      try {
        const receipt = JSON.parse(jobsDirectory.readFile(entry.name, {
          encoding: 'utf8',
          operation: 'job-ttl-receipt-read',
          maxBytes: MAX_JOB_RECEIPT_BYTES
        }));
        if (receipt.status === 'running' && ownerIsAlive(receipt.ownerProcess)) continue;
      } catch {
        // Invalid or unreadable expired receipts are stale state and remain eligible for bounded removal.
      }
      jobsDirectory.remove(entry.name, { operation: 'job-ttl-remove', expectedType: 'file' });
      removed += 1;
    }
  } finally {
    jobsDirectory.close();
  }
  return removed;
}

function persist(job, options = {}) {
  const jobsDirectory = storageRoot.openDirectory(jobRootRelative, { create: true });
  jobsDirectory.close();
  const relative = storageRoot.relative(jobPath(job.jobId));
  if (options.claim) {
    storageRoot.writeFile(relative, `${JSON.stringify(job, null, 2)}\n`, {
      operation: 'job-receipt-claim'
    });
  } else {
    storageRoot.replaceFile(relative, `${JSON.stringify(job, null, 2)}\n`, {
      operation: 'job-receipt-replace'
    });
  }
}

function loadJob(jobId) {
  if (jobs.has(jobId)) return jobs.get(jobId);
  const file = jobPath(jobId);
  const relative = storageRoot.relative(file);
  if (!storageRoot.exists(relative)) throw new Error(`unknown design job: ${jobId}`);
  const job = JSON.parse(storageRoot.readFile(relative, {
    encoding: 'utf8',
    operation: 'job-receipt-read',
    maxBytes: MAX_JOB_RECEIPT_BYTES
  }));
  if (job.status === 'running') {
    if (ownerIsAlive(job.ownerProcess)) return job;
    job.status = 'failed';
    job.error = 'MCP server restarted before the bridge finalized this job; inspect Open Design state before retrying.';
    persist(job);
  }
  return job;
}

function jsonContent(value) {
  return { content: [{ type: 'text', text: JSON.stringify(value, null, 2) }], structuredContent: value };
}

function startJob(request) {
  const failures = validateRequest(request);
  if (failures.length) throw new Error(failures.join('; '));
  if (jobs.size >= maxConcurrentJobs) {
    throw new Error(`active design job limit reached: ${maxConcurrentJobs}`);
  }
  const staleJobsRemoved = sweepJobs();
  const jobId = normalizeJobId(request.requestId?.trim() || `design-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const normalizedRequest = { ...request, requestId: jobId };
  const existingPath = jobPath(jobId);
  const existingResultPath = path.join(resultRoot, `${jobId}.json`);
  if (jobs.has(jobId) || storageRoot.exists(storageRoot.relative(existingPath)) || storageRoot.exists(storageRoot.relative(existingResultPath))) {
    throw new Error(`design job already exists: ${jobId}`);
  }
  const job = {
    jobVersion: 'CENTURION_OD_JOB_V1',
    jobId,
    status: 'running',
    requestId: jobId,
    ownerProcess: { pid: process.pid, startTime: processStartTime(process.pid) },
    result: null,
    error: null
  };
  try {
    persist(job, { claim: true });
  } catch (error) {
    if (error.code === 'EEXIST') throw new Error(`design job already exists: ${jobId}`);
    throw error;
  }
  jobs.set(jobId, job);
  void runDesignRequest(normalizedRequest, { cwd: process.cwd(), env: process.env })
    .then((result) => {
      const resultPath = path.join(resultRoot, `${jobId}.json`);
      if (!isWithin(resultRoot, resultPath)) throw new Error('invalid result path');
      const resultsDirectory = storageRoot.openDirectory(resultRootRelative, { create: true });
      resultsDirectory.close();
      storageRoot.writeFile(storageRoot.relative(resultPath), `${JSON.stringify(result, null, 2)}\n`, {
        operation: 'design-result-receipt-write'
      });
      Object.assign(job, { status: result.status, resultPath, result, error: null });
      persist(job);
      jobs.delete(jobId);
    })
    .catch((error) => {
      Object.assign(job, { status: 'failed', result: null, error: error.message });
      persist(job);
      jobs.delete(jobId);
    });
  return { jobId, status: 'running', jobPath: jobPath(jobId), staleJobsRemoved, pollAfterSeconds: 30 };
}

async function callTool(name, args) {
  if (name === 'search_design_references') {
    return jsonContent(await searchDesignReferences({ ...args, requestVersion: 'CENTURION_REFERENCE_REQUEST_V1' }, { cwd: process.cwd(), env: process.env }));
  }
  if (name === 'start_design') {
    if (!args.request || args.request.action === 'cleanup') throw new Error('start_design requires a create or revise request');
    return jsonContent(startJob(args.request));
  }
  if (name === 'get_design') return jsonContent(loadJob(args.jobId));
  if (name === 'cleanup_design') {
    if (!args.request || args.request.action !== 'cleanup') throw new Error('cleanup_design requires action=cleanup');
    return jsonContent(await runDesignRequest(args.request, { cwd: process.cwd(), env: process.env }));
  }
  throw new Error(`unknown tool: ${name}`);
}

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

async function handle(message) {
  if (!message || typeof message !== 'object' || Array.isArray(message)) {
    send({ jsonrpc: '2.0', id: null, error: { code: -32600, message: 'Invalid Request: expected a JSON object' } });
    return;
  }
  const { id, method, params } = message;
  if (method === 'initialize') {
    send({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: params?.protocolVersion || '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'centurion-open-design', version: '0.2.1' },
        instructions: 'Use search_design_references before design production when references help. Then call start_design, poll get_design every 30-60 seconds, inspect artifact and screenshot proof, and revise through previousResultPath. Never delete an Open Design project without explicit user consent.'
      }
    });
  } else if (method === 'tools/list') send({ jsonrpc: '2.0', id, result: { tools } });
  else if (method === 'tools/call') send({ jsonrpc: '2.0', id, result: await callTool(params?.name, params?.arguments ?? {}) });
  else if (method === 'ping') send({ jsonrpc: '2.0', id, result: {} });
  else if (id !== undefined) send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
}

let buffer = '';
let bufferBytes = 0;
let discardingOversizedLine = false;

function rejectOversizedMessage() {
  send({
    jsonrpc: '2.0',
    id: null,
    error: { code: -32600, message: `Invalid Request: JSONL message exceeds ${MAX_JSON_INPUT_BYTES} bytes` }
  });
}

function processLine(line) {
  if (!line.trim()) return;
  let message;
  try {
    message = JSON.parse(line);
  } catch (error) {
    send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: error.message } });
    return;
  }
  void handle(message).catch((error) => send({
    jsonrpc: '2.0',
    id: message?.id ?? null,
    error: { code: -32000, message: error.message }
  }));
}

process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  let remaining = chunk;
  while (remaining.length > 0) {
    if (discardingOversizedLine) {
      const newline = remaining.indexOf('\n');
      if (newline === -1) return;
      remaining = remaining.slice(newline + 1);
      discardingOversizedLine = false;
      continue;
    }

    const newline = remaining.indexOf('\n');
    const segment = newline === -1 ? remaining : remaining.slice(0, newline);
    const segmentBytes = Buffer.byteLength(segment);
    if (bufferBytes + segmentBytes > MAX_JSON_INPUT_BYTES) {
      buffer = '';
      bufferBytes = 0;
      rejectOversizedMessage();
      if (newline === -1) {
        discardingOversizedLine = true;
        return;
      }
      remaining = remaining.slice(newline + 1);
      continue;
    }

    buffer += segment;
    bufferBytes += segmentBytes;
    if (newline === -1) return;
    processLine(buffer);
    buffer = '';
    bufferBytes = 0;
    remaining = remaining.slice(newline + 1);
  }
});
