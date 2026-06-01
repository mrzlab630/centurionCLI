#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillsRoot = process.env.CENTURION_SKILLS_ROOT || path.resolve(scriptDir, '..', '..');

function skillScript(skillName, scriptName) {
  return path.join(skillsRoot, skillName, 'scripts', scriptName);
}

function runJson(command, args) {
  return JSON.parse(execFileSync(command, args, {
    encoding: 'utf8',
    env: { ...process.env, CENTURION_SKILLS_ROOT: skillsRoot },
  }));
}

const audit = runJson('node', [skillScript('context-optimizer', 'skill-surface-audit.mjs')]);
const drift = runJson('node', [skillScript('context-optimizer', 'skill-drift-report.mjs')]);
const prep = runJson('node', [
  skillScript('orchestrator', 'mission-prep.mjs'),
  'улучшить навыки легионеров, контекст, eval, security и поиск смежных навыков',
]);
const riskPrep = runJson('node', [
  skillScript('orchestrator', 'mission-prep.mjs'),
  'проверь риск новой способности и вызови смежных легионеров',
]);

const checks = [
  {
    name: 'skill surface has no long descriptions',
    pass: audit.longDescriptions.length === 0,
    detail: `${audit.longDescriptions.length} long descriptions`,
  },
  {
    name: 'skill surface has no duplicate active names',
    pass: audit.duplicateNameCount === 0 && audit.driftedDuplicateCount === 0,
    detail: `${audit.duplicateNameCount} duplicates, ${audit.driftedDuplicateCount} drifted`,
  },
  {
    name: 'drift report is available',
    pass: drift.driftedCount === 0 && Array.isArray(drift.drifted),
    detail: `${drift.driftedCount} drifted skills reported`,
  },
  {
    name: 'mission prep routes context/security/eval task',
    pass: [prep.primaryLegionary, ...prep.adjacentLegionaries].some((name) => ['tester', 'security', 'context-optimizer', 'orchestrator'].includes(name)),
    detail: `${prep.primaryLegionary} -> ${prep.adjacentLegionaries.join(',')}`,
  },
  {
    name: 'mission prep deduplicates and ranks skill candidates',
    pass: new Set(prep.localSkillCandidates.map((item) => item.name)).size === prep.localSkillCandidates.length
      && ['context-optimizer', 'tester', 'orchestrator', 'security'].some((name) => prep.localSkillCandidates.map((item) => item.name).includes(name)),
    detail: prep.localSkillCandidates.map((item) => item.name).join(','),
  },
  {
    name: 'risk language triggers guardian gate',
    pass: riskPrep.guardianGate === true
      && [riskPrep.primaryLegionary, ...riskPrep.adjacentLegionaries].includes('security'),
    detail: `${riskPrep.guardianGate} ${riskPrep.primaryLegionary} -> ${riskPrep.adjacentLegionaries.join(',')}`,
  },
];

const failed = checks.filter((check) => !check.pass);
console.log(JSON.stringify({ status: failed.length ? 'fail' : 'pass', checks }, null, 2));
process.exit(failed.length ? 1 : 0);
