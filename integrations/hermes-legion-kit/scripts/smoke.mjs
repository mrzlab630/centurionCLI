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
  const scripts = ['regression_review_ladder.py', 'regression_agent_contract_runner.py', 'regression_agent_result_builder.py', 'regression_result_gateway.py', 'regression_response_envelope.py', 'regression_artifact_lineage.py', 'regression_accepted_inputs.py', 'regression_accepted_inputs_gateway.py', 'regression_execution_state.py', 'regression_legion_handoffs.py'];
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
    const result = spawnSync('python3', [script], { cwd: scriptRoot, encoding: 'utf8', env: isolatedEnvironment });
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
 console.log(JSON.stringify({ok:true,installedFixture:'pass',packagedRuntimeRegressions:skillsOnly?'not run: W2/W3 integration required':'pass',liveCapability:'unverified'}));
}catch(e){console.error(e.message);process.exitCode=1;}
