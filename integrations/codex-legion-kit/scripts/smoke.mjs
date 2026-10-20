#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { parseTomlLite } from './codex-surface-audit.mjs';
import { REPO_ROOT } from './lib/surface-config.mjs';
const KIT_ROOT=path.join(REPO_ROOT,'integrations/codex-legion-kit');
function assert(condition,message){if(!condition)throw new Error(message);}
function run(command,args,options={}){return spawnSync(command,args,{cwd:KIT_ROOT,encoding:'utf8',...options});}
function smokeTomlParsing() {
  const parsed = parseTomlLite(`
model = "gpt-6.1-sol" # keep this comment outside the value
description = "keep # inside double quotes"
literal = 'keep # inside single quotes'
[features]
memories = true # trailing comment
`);
  assert(parsed.model === 'gpt-6.1-sol', 'TOML parser should strip trailing comments');
  assert(parsed.description === 'keep # inside double quotes', 'TOML parser should preserve # in double-quoted values');
  assert(parsed.literal === 'keep # inside single quotes', 'TOML parser should preserve # in single-quoted values');
  assert(parsed.features.memories === true, 'TOML parser should keep nested booleans with trailing comments');
}

function smokeLegionContracts() {
  const validator = path.join(REPO_ROOT, 'integrations', 'legion-contracts', 'scripts', 'legion-contract.mjs');
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-legion-contract-'));
  try {
    const resultFile = path.join(tempRoot, 'LEGION_RESULT.json');
    fs.writeFileSync(resultFile, JSON.stringify({
      contractVersion: 'LEGION_RESULT_V1',
      owner: 'REVIEWER',
      executor: 'codex',
      status: 'done',
      filesChanged: ['README.md'],
      proof: [{ command: 'npm run smoke', result: 'passed', summary: 'contract smoke' }],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    }, null, 2));
    const ok = run(process.execPath, [validator, 'validate-result', '--file', resultFile], { cwd: REPO_ROOT });
    assert(ok.status === 0, `LEGION_RESULT validator failed: ${ok.stderr || ok.stdout}`);
    fs.writeFileSync(resultFile, JSON.stringify({
      contractVersion: 'LEGION_RESULT_V1',
      owner: 'REVIEWER',
      executor: 'codex',
      status: 'done',
      filesChanged: ['README.md'],
      proof: [],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    }, null, 2));
    const bad = run(process.execPath, [validator, 'validate-result', '--file', resultFile], { cwd: REPO_ROOT });
    assert(bad.status !== 0, 'LEGION_RESULT validator should fail on done result without proof');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

try {
 smokeTomlParsing();smokeLegionContracts();
 for(const args of [[path.join(KIT_ROOT,'scripts/codex-surface-audit.mjs'),'--repo-only'],
  [path.join(REPO_ROOT,'skills/tester/scripts/legion-skill-eval.mjs')],
  ['--test',path.join(REPO_ROOT,'tests/install-owned-files.test.mjs')]]) {
  const r=run(process.execPath,args,{env:{...process.env,CENTURION_INSTALL_CLIENT:'codex'}});
  assert(r.status===0,r.stderr||r.stdout);
 }
 console.log('codex-legion-kit smoke: pass (offline installed selection, parser and compatibility validation)');
}catch(e){console.error(e.message);process.exitCode=1;}
