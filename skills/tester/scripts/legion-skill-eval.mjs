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

function missionPrep(task) {
  return runJson('node', [skillScript('orchestrator', 'mission-prep.mjs'), task]);
}

const routeCases = [
  {
    task: 'написать CTA и empty state для игры Telegram Mini App',
    primary: 'nomenclator',
    forbidden: ['quaestor'],
  },
  {
    task: 'создать экраны и core loop для Telegram Mini App игры',
    primary: 'ludifex',
  },
  {
    task: 'создать посты для Twitter и Reddit',
    primary: 'orator',
  },
  {
    task: 'составить SEO keyword brief and schema audit',
    primary: 'indagator',
  },
  {
    task: 'проанализировать live Phantom1225 ScamNet pool dump timing',
    primary: 'augur',
  },
  {
    task: 'проанализировать DEX token risk model and technical analysis',
    primary: 'quaestor',
    guardianGate: false,
  },
];

const routeResults = routeCases.map((item) => {
  const result = missionPrep(item.task);
  const selected = [result.primaryLegionary, ...result.adjacentLegionaries];
  const forbidden = item.forbidden || [];
  return {
    ...item,
    actualPrimary: result.primaryLegionary,
    actualGuardianGate: result.guardianGate,
    selected,
    pass: result.primaryLegionary === item.primary
      && (item.guardianGate === undefined || result.guardianGate === item.guardianGate)
      && forbidden.every((name) => !selected.includes(name)),
  };
});

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
  {
    name: 'mission prep routes specialized Legionaries without overlap regressions',
    pass: routeResults.every((item) => item.pass),
    detail: routeResults.map((item) => `${item.primary}:${item.actualPrimary}:${item.actualGuardianGate}`).join(', '),
  },
];

const failed = checks.filter((check) => !check.pass);
console.log(JSON.stringify({ status: failed.length ? 'fail' : 'pass', checks }, null, 2));
process.exit(failed.length ? 1 : 0);
