#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {
  validateAgentResult,
  validateDelegationResult,
  validateLegionOrder,
  validateLegionReview,
  parseStrictJson
} from '../lib/contracts.mjs';

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const args = { command };
  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = rest[index + 1];
    if (!next || next.startsWith('--')) args[key] = true;
    else {
      args[key] = next;
      index += 1;
    }
  }
  return args;
}

function usage() {
  return `Usage:\n  node scripts/legion-contract.mjs validate-order --file <LEGION_ORDER.json>\n  node scripts/legion-contract.mjs validate-result --file <RESULT.json> [--accept-order-version <AGY_ORDER_V1,CLAUDE_ORDER_V1>]\n  node scripts/legion-contract.mjs validate-result --canonical --file <AGENT_RESULT.json> [--order-id <id>] [--executor <id>] [--status <done,blocked,failed>]\n  node scripts/legion-contract.mjs validate-agent-result --file <AGENT_RESULT.json> [--order-id <id>] [--executor <id>] [--status <done,blocked,failed>]\n  node scripts/legion-contract.mjs validate-canonical-result --file <AGENT_RESULT.json> [--order-id <id>] [--executor <id>] [--status <done,blocked,failed>]\n  node scripts/legion-contract.mjs validate-review --file <LEGION_REVIEW.json>\n`;
}

function readJson(file) {
  return parseStrictJson(fs.readFileSync(file, 'utf8'), `JSON file ${file}`);
}

function splitList(value) {
  if (!value || value === true) return [];
  return String(value).split(',').map((item) => item.trim()).filter(Boolean);
}

function validate(args) {
  if (!args.file || args.file === true) throw new Error('--file is required');
  const file = path.resolve(String(args.file));
  const data = readJson(file);
  let failures;
  if (args.command === 'validate-order') failures = validateLegionOrder(data);
  else if (args.command === 'validate-agent-result' || args.command === 'validate-canonical-result' || (args.command === 'validate-result' && args.canonical)) failures = validateAgentResult(data, {
    expectedOrderId: args['order-id'],
    expectedExecutor: args.executor,
    expectedStatus: args.status
  });
  else if (args.command === 'validate-result') failures = validateDelegationResult(data, {
    acceptedOrderVersions: splitList(args['accept-order-version'])
  });
  else if (args.command === 'validate-review') failures = validateLegionReview(data);
  else throw new Error(`unknown command: ${args.command || '<missing>'}`);

  const report = { ok: failures.length === 0, file, failures };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (failures.length) process.exitCode = 1;
}

try {
  const args = parseArgs(process.argv.slice(2));
  if (!args.command || args.help) {
    process.stdout.write(usage());
    process.exitCode = args.help ? 0 : 1;
  } else {
    validate(args);
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
