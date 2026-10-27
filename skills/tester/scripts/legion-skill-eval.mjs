#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { auditSurface,instructionViolations } from '../../context-optimizer/scripts/skill-surface-audit.mjs';
import { REPO_ROOT,LOAD_MAP,EXPECTED_SKILLS,selectSkills } from '../../../integrations/codex-legion-kit/scripts/lib/surface-config.mjs';
const audit=auditSurface();
const checks=[];
function check(name,fn) {try{fn();checks.push({name,status:'pass'});}catch(e){checks.push({name,status:'fail',summary:e.message});}}
check('all 37 root entrypoints have exactly one load classification',()=>{
 const actual=fs.readdirSync(path.join(REPO_ROOT,'skills')).filter(n=>fs.existsSync(path.join(REPO_ROOT,'skills',n,'SKILL.md'))).sort();
 assert.equal(EXPECTED_SKILLS.length,37); assert.equal(new Set(EXPECTED_SKILLS).size,37);assert.deepEqual(actual,EXPECTED_SKILLS);
});
check('one core entrypoint incorporates planning/context; excluded skills cannot install',()=>{
 assert.deepEqual(selectSkills('core'),['orchestrator']);
 for(const n of [...LOAD_MAP.excluded,...LOAD_MAP.incorporated]) assert.throws(()=>selectSkills('domain',[n]));
 assert.throws(()=>selectSkills('domain'));assert.throws(()=>selectSkills(undefined));
 assert.throws(()=>selectSkills('domain',['open-design-producer']));
 for(const name of ['aedilis','pictor','nomenclator','orator','tabularius']) assert(selectSkills('domain',[name]).includes(name));
});
check('active roots, references and bundle dependencies are coherent',()=>{
 assert.deepEqual(audit.violations,[]);assert.deepEqual(audit.brokenReferences,[]);assert.deepEqual(audit.bundleErrors,[]);
 assert.equal(audit.duplicateNameCount,0);assert.equal(audit.longDescriptions.length,0);
});
check('audit rejects actionable ceremony, retry, scope expansion and legacy routes',()=>{
 for(const s of ['Always run WAR ROOM.','Mandatory tribunal.','Require 80% coverage.',
  'Fix every failed test.','3 autonomous retries before failure.','Always delegate to TESTER.',
  'Use delegate_task for production.','Use gpt-6-sol as fallback.']) assert(instructionViolations(s).length,s);
 assert.equal(instructionViolations('No automatic retries. Historical tribunal is excluded.').length,0);
});
check('unrelated generated and dependency entrypoints cannot affect the active surface',()=>{
 assert(audit.records.every(r=>!/(?:node_modules|centurion-backup|\/backups\/|\/generated\/)/.test(r.file)));
});
const failed=checks.filter(c=>c.status!=='pass');console.log(JSON.stringify({status:failed.length?'fail':'pass',checks},null,2));if(failed.length)process.exitCode=1;
