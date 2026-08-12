#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { runDesignRequest } from '../lib/bridge.mjs';
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
assertPathWithinRoot(designRoot, jobRoot, { allowRoot: false, label: 'CENTURION_OD_JOB_ROOT', rejectFinalSymlink: true });
assertPathWithinRoot(designRoot, resultRoot, { allowRoot: false, label: 'CENTURION_OD_RESULT_ROOT', rejectFinalSymlink: true });
assertPathWithinRoot(jobBase, jobRoot, { label: 'CENTURION_OD_JOB_ROOT', rejectFinalSymlink: true });
assertPathWithinRoot(resultBase, resultRoot, { label: 'CENTURION_OD_RESULT_ROOT', rejectFinalSymlink: true });
const storageRoot = new AnchoredRoot(designRoot, { create: true });
const jobRootRelative = storageRoot.relative(jobRoot);
const resultRootRelative = storageRoot.relative(resultRoot);

const tools = [
  {
    name: 'search_design_references',
    description: 'Search curated web-design references and return a temporary manifest for Open Design production.',
    inputSchema: {
      type: 'object',
      required: ['query'],
      properties: {
        query: { type: 'string' },
        artifactType: { type: 'string' },
        platform: { type: 'string' },
        sources: { type: 'array', items: { enum: ['shadcn', 'magicui', 'hyperui', 'tabler', 'landbook'] } },
        limit: { type: 'integer', minimum: 1, maximum: 10 }
      }
    }
  },
  {
    name: 'start_design',
    description: 'Start an asynchronous proof-first Open Design create or revise job. Returns immediately with a jobId.',
    inputSchema: { type: 'object', required: ['request'], properties: { request: { type: 'object' } } }
  },
  {
    name: 'get_design',
    description: 'Read the current state or final JSON result of an Open Design job.',
    inputSchema: { type: 'object', required: ['jobId'], properties: { jobId: { type: 'string' } } }
  },
  {
    name: 'cleanup_design',
    description: 'Run a bounded cleanup request. Open Design project deletion still requires cleanup.deleteProject=true from an explicit user decision.',
    inputSchema: { type: 'object', required: ['request'], properties: { request: { type: 'object' } } }
  }
];

function isWithin(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function jobPath(jobId) {
  const safe = String(jobId).replace(/[^A-Za-z0-9._-]/g, '-');
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
          operation: 'job-ttl-receipt-read'
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
  const job = JSON.parse(storageRoot.readFile(relative, { encoding: 'utf8', operation: 'job-receipt-read' }));
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
  const { id, method, params } = message;
  if (method === 'initialize') {
    send({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: params?.protocolVersion || '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'centurion-open-design', version: '0.2.0' },
        instructions: 'Use search_design_references before design production when references help. Then call start_design, poll get_design every 30-60 seconds, inspect artifact and screenshot proof, and revise through previousResultPath. Never delete an Open Design project without explicit user consent.'
      }
    });
  } else if (method === 'tools/list') send({ jsonrpc: '2.0', id, result: { tools } });
  else if (method === 'tools/call') send({ jsonrpc: '2.0', id, result: await callTool(params?.name, params?.arguments ?? {}) });
  else if (method === 'ping') send({ jsonrpc: '2.0', id, result: {} });
  else if (id !== undefined) send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
}

let buffer = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buffer += chunk;
  while (buffer.includes('\n')) {
    const index = buffer.indexOf('\n');
    const line = buffer.slice(0, index).trim();
    buffer = buffer.slice(index + 1);
    if (!line) continue;
    let message;
    try {
      message = JSON.parse(line);
    } catch (error) {
      send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: error.message } });
      continue;
    }
    void handle(message).catch((error) => send({ jsonrpc: '2.0', id: message.id ?? null, error: { code: -32000, message: error.message } }));
  }
});
