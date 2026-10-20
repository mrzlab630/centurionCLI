#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { REPO_ROOT } from '../../codex-legion-kit/scripts/lib/surface-config.mjs';
const KIT_ROOT=path.join(REPO_ROOT,'integrations/hermes-legion-kit');
function assert(condition,message){if(!condition)throw new Error(message);}
function runPackagedPythonRegressions(scriptRoot) {
  assert(!process.env.PYTHONOPTIMIZE, 'PYTHONOPTIMIZE must be unset so packaged regression assertions cannot be stripped');
  // V3 lifecycle has its own entrypoint. The old runner/Gateway mains exercise
  // retired direct-dispatch and Loop V1 execution; they remain historical
  // fixtures, not active launch authority. Their shared parsers are covered by
  // the builder/envelope/lineage suites and the real V3 Gateway chain below.
  const scripts = ['regression_review_ladder.py', 'regression_agent_contract_runner.py', 'regression_agent_result_builder.py', 'regression_result_gateway_v3.py', 'regression_response_envelope.py', 'regression_artifact_lineage.py', 'regression_accepted_inputs.py', 'regression_accepted_inputs_gateway.py', 'regression_execution_state.py', 'regression_legion_handoffs.py', 'regression_order_preflight.py', 'regression_progress_drift_detector.py', 'regression_blocker_packet_projection.py'];
  const isolatedEnvironment = {
    ...process.env,
    HOME: path.join(path.dirname(scriptRoot), 'nonexistent-home'),
    HERMES_HOME: path.join(path.dirname(scriptRoot), 'nonexistent-hermes-home'),
    PYTHONDONTWRITEBYTECODE: '1'
  };
  const userSite = spawnSync('python3', ['-c', 'import site; print(site.getusersitepackages())'], { encoding: 'utf8' });
  assert(userSite.status === 0, `could not locate active Python user-site: ${userSite.stderr || userSite.stdout}`);
  const userSitePath = userSite.stdout.trim();
  assert(userSitePath, 'active Python user-site path is empty');
  isolatedEnvironment.PYTHONPATH = [userSitePath, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  delete isolatedEnvironment.PYTHONOPTIMIZE;
  delete isolatedEnvironment.AQUILA_AGENT_RESULT_SCHEMA;
  for (const script of scripts) {
    const args = script === 'regression_agent_contract_runner.py' ? [script, '--mission-only'] : [script];
    const result = spawnSync('python3', args, { cwd: scriptRoot, encoding: 'utf8', env: isolatedEnvironment, timeout: 240_000 });
    assert(result.status === 0, `${script} failed: ${result.stderr || result.stdout}`);
  }
}

try {
 const fixture=spawnSync(process.execPath,['--test',path.join(REPO_ROOT,'tests/install-owned-files.test.mjs')],{
  encoding:'utf8',env:{...process.env,CENTURION_INSTALL_CLIENT:'hermes'}});
 assert(fixture.status===0,fixture.stderr||fixture.stdout);
 const skillsOnly=process.argv.includes('--skills-only');
 if(!skillsOnly){
  const home=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-hermes-runtime-'));
  try{
   const install=spawnSync(process.execPath,[path.join(KIT_ROOT,'installer/install.mjs'),'--profile','core','--hermes-home',home],{encoding:'utf8'});
   assert(install.status===0,install.stderr||install.stdout);
   runPackagedPythonRegressions(path.join(home,'skills/autonomous-ai-agents/agent-contract-runner/scripts'));
  }finally{fs.rmSync(home,{recursive:true,force:true});}
 }
 console.log(JSON.stringify({ok:true,installedFixture:'pass',packagedRuntimeRegressions:skillsOnly?'not run: skills-only selection':'pass',historicalDispatchMains:'not run: retired direct runner and Loop V1 Gateway dispatch',liveCapability:'unverified'}));
}catch(e){console.error(e.message);process.exitCode=1;}
