#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import {
  AGENT_RESULT_VERSION,
  LEGION_ORDER_VERSION,
  LEGION_RESULT_VERSION,
  LEGION_REVIEW_VERSION,
  validateAgentResult,
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

  const canonical = {
    resultVersion: AGENT_RESULT_VERSION,
    orderId: 'canonical-contract-core-20260826-codex-direct-attempt2',
    executor: 'codex',
    status: 'done',
    summary: 'Canonical result accepted.',
    filesChanged: [{ path: 'integrations/legion-contracts/lib/contracts.mjs', action: 'modified' }],
    artifacts: [{ path: 'CODEX_RESULT.json', exists: true, type: 'AGENT_RESULT_JSON_V1', note: 'validated' }],
    proof: [{ command: 'node --check file.mjs', cwd: '/tmp/example', status: 'pass', exitCode: 0, summary: 'passed' }],
    selfReview: { performed: true, findings: [], fixesApplied: [] },
    scopeDeviations: [],
    forbiddenPatternHits: [],
    remainingRisks: [],
    questions: [],
    errors: [],
    stdoutSummary: '',
    stderrSummary: ''
  };
  const identity = { orderId: canonical.orderId, executor: canonical.executor, status: canonical.status };
  assert(validateAgentResult(canonical, { expectedIdentity: identity }).length === 0, 'valid AGENT_RESULT_JSON_V1 should pass');
  assert(validateAgentResult({ ...canonical, resultVersion: 'AGENT_RESULT_JSON_V0' }).some((item) => item.includes('resultVersion')), 'wrong canonical result version should fail');
  assert(validateAgentResult({ ...canonical, orderId: undefined }).some((item) => item.includes('orderId')), 'missing canonical order identity should fail');
  assert(validateAgentResult({ ...canonical, orderId: 'wrong-order' }, { expectedIdentity: identity }).some((item) => item.includes('orderId')), 'wrong canonical order identity should fail');
  assert(validateAgentResult({ ...canonical, executor: undefined }).some((item) => item.includes('executor')), 'missing canonical executor identity should fail');
  assert(validateAgentResult({ ...canonical, status: 'unknown' }).some((item) => item.includes('status')), 'invalid canonical status should fail');
  assert(validateAgentResult({ ...canonical, filesChanged: ['file.mjs'] }).some((item) => item.includes('filesChanged[0]')), 'string canonical filesChanged item should fail');
  assert(validateAgentResult({ ...canonical, artifacts: [{ path: 'x' }] }).some((item) => item.includes('artifacts[0].exists')), 'incomplete canonical artifact should fail');
  assert(validateAgentResult({ ...canonical, proof: [{ command: 'x', cwd: '/tmp', status: 'passed', exitCode: 0, summary: '' }] }).some((item) => item.includes('proof[0].status')), 'invalid canonical proof status should fail');
  assert(validateAgentResult({ ...canonical, selfReview: [] }).some((item) => item.includes('selfReview')), 'non-object canonical selfReview should fail');
  assert(validateAgentResult({ ...canonical, remainingRisks: [42] }).some((item) => item.includes('remainingRisks')), 'non-string canonical array entry should fail');
  for (const field of ['contractVersion', 'orderVersion', 'owner', 'selfReviewFixed', 'scopeViolations']) {
    assert(validateAgentResult({ ...canonical, [field]: 'legacy' }).some((item) => item.includes('legacy fields')), `canonical result with legacy ${field} must fail`);
  }
  assert(validateAgentResult({ ...canonical, proof: [{ command: 'x', cwd: '/tmp', status: 'pass', exitCode: 0, summary: '', result: 'passed' }] }).some((item) => item.includes('legacy result')), 'canonical proof.result field must fail');
  assert(validateAgentResult({ ...canonical, proof: [] }).some((item) => item.includes('at least one proof')), 'done canonical result without proof must fail');
  assert(validateAgentResult({ ...canonical, proof: [{ command: 'x', cwd: '/tmp', status: 'fail', exitCode: 1, summary: 'failed' }] }).some((item) => item.includes('every proof[].status')), 'done canonical result with failed proof must fail');
  assert(validateAgentResult({ ...canonical, selfReview: { performed: false, findings: [], fixesApplied: [] } }).some((item) => item.includes('selfReview.performed=true')), 'done canonical result without performed self-review must fail');
  assert(validateAgentResult({ ...canonical, scopeDeviations: ['outside scope'] }).some((item) => item.includes('scope deviations')), 'done canonical result with scope deviations must fail');
  assert(validateAgentResult({ ...canonical, forbiddenPatternHits: ['forbidden'] }).some((item) => item.includes('forbidden pattern hits')), 'done canonical result with forbidden pattern hits must fail');
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

    const canonicalFile = path.join(tempRoot, 'AGENT_RESULT.json');
    fs.writeFileSync(canonicalFile, JSON.stringify({
      resultVersion: AGENT_RESULT_VERSION,
      orderId: 'canonical-contract-core-20260826-codex-direct-attempt2',
      executor: 'codex',
      status: 'done',
      summary: 'passed',
      filesChanged: [],
      artifacts: [],
      proof: [{ command: 'node --check file.mjs', cwd: KIT_ROOT, status: 'pass', exitCode: 0, summary: 'passed' }],
      selfReview: { performed: true, findings: [], fixesApplied: [] },
      scopeDeviations: [],
      forbiddenPatternHits: [],
      remainingRisks: [],
      questions: [],
      errors: [],
      stdoutSummary: '',
      stderrSummary: ''
    }, null, 2));
    const canonical = run(process.execPath, [path.join(KIT_ROOT, 'scripts', 'legion-contract.mjs'), 'validate-agent-result', '--file', canonicalFile, '--order-id', 'canonical-contract-core-20260826-codex-direct-attempt2', '--executor', 'codex', '--status', 'done']);
    assert(canonical.status === 0, `CLI validate-agent-result should pass: ${canonical.stderr || canonical.stdout}`);
    const canonicalAlias = run(process.execPath, [path.join(KIT_ROOT, 'scripts', 'legion-contract.mjs'), 'validate-result', '--canonical', '--file', canonicalFile]);
    assert(canonicalAlias.status === 0, `CLI validate-result --canonical should pass: ${canonicalAlias.stderr || canonicalAlias.stdout}`);
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
