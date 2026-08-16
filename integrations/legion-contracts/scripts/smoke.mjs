#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import {
  LEGION_ORDER_VERSION,
  LEGION_RESULT_VERSION,
  LEGION_REVIEW_VERSION,
  validateDelegationResult,
  validateLegionOrder,
  validateLegionReview
} from '../lib/contracts.mjs';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function run(command, args) {
  return spawnSync(command, args, { cwd: KIT_ROOT, encoding: 'utf8' });
}

function smokeValidators() {
  const order = {
    orderVersion: LEGION_ORDER_VERSION,
    owner: 'PICTOR',
    executor: 'agy',
    task: 'Refactor the hero component only.',
    workspace: '/tmp/example',
    allowedPaths: ['src/Hero.tsx'],
    nonGoals: ['Do not change routes.'],
    forbiddenPatterns: ['font-size\\s*:[^;]*vw'],
    proofCommands: ['npm test -- Hero'],
    acceptanceCriteria: ['Hero tests pass.'],
    resultFile: 'AGY_RESULT.json'
  };
  assert(validateLegionOrder(order).length === 0, 'valid LEGION_ORDER_V1 should pass');
  assert(validateLegionOrder({ ...order, allowedPaths: [] }).some((item) => item.includes('allowedPaths')), 'empty allowedPaths should fail');

  const result = {
    contractVersion: LEGION_RESULT_VERSION,
    owner: 'PICTOR',
    executor: 'agy',
    status: 'done',
    filesChanged: ['src/Hero.tsx', 'AGY_RESULT.json'],
    proof: [{ command: 'npm test -- Hero', result: 'passed', summary: 'passed' }],
    selfReviewFixed: 'yes',
    scopeViolations: [],
    forbiddenPatternHits: [],
    remainingRisks: []
  };
  assert(validateDelegationResult(result).length === 0, 'valid LEGION_RESULT_V1 should pass');
  assert(validateDelegationResult({ ...result, proof: [] }).some((item) => item.includes('proof')), 'done result without proof should fail');

  const legacy = { ...result, contractVersion: undefined, orderVersion: 'AGY_ORDER_V1' };
  assert(validateDelegationResult(legacy, { acceptedOrderVersions: ['AGY_ORDER_V1'] }).length === 0, 'legacy AGY_ORDER_V1 result should pass when accepted');

  const review = {
    reviewVersion: LEGION_REVIEW_VERSION,
    reviewer: 'REVIEWER',
    targetExecutor: 'agy',
    targetResultFile: 'AGY_RESULT.json',
    verdict: 'accepted',
    summary: 'Scope and proof accepted.',
    findings: [],
    proofReviewed: ['npm test -- Hero'],
    requiredFixes: [],
    remainingRisks: []
  };
  assert(validateLegionReview(review).length === 0, 'valid LEGION_REVIEW_V1 should pass');
  assert(validateLegionReview({ ...review, verdict: 'accepted', requiredFixes: ['fix scope'] }).some((item) => item.includes('accepted review')), 'accepted review with fixes should fail');
}

function smokeCli() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'legion-contract-'));
  try {
    const resultFile = path.join(tempRoot, 'LEGION_RESULT.json');
    fs.writeFileSync(resultFile, JSON.stringify({
      contractVersion: LEGION_RESULT_VERSION,
      owner: 'PICTOR',
      executor: 'codex',
      status: 'done',
      filesChanged: ['README.md'],
      proof: [{ command: 'npm test', result: 'passed', summary: 'passed' }],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    }, null, 2));
    const ok = run(process.execPath, [path.join(KIT_ROOT, 'scripts', 'legion-contract.mjs'), 'validate-result', '--file', resultFile]);
    assert(ok.status === 0, `CLI validate-result should pass: ${ok.stderr || ok.stdout}`);
    fs.writeFileSync(resultFile, '{ bad json');
    const bad = run(process.execPath, [path.join(KIT_ROOT, 'scripts', 'legion-contract.mjs'), 'validate-result', '--file', resultFile]);
    assert(bad.status !== 0, 'CLI validate-result should fail on invalid JSON');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

try {
  smokeValidators();
  smokeCli();
  process.stdout.write('legion-contracts smoke: pass\n');
} catch (error) {
  process.stderr.write(`legion-contracts smoke: fail: ${error.message}\n`);
  process.exitCode = 1;
}
