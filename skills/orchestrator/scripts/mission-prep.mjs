#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const task = process.argv.slice(2).join(' ').trim();
if (!task) {
  console.error('Usage: mission-prep.mjs <task description>');
  process.exit(2);
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const inferredSkillsRoot = path.resolve(scriptDir, '..', '..');
const home = process.env.HOME || '';
const codexHome = process.env.CODEX_HOME || (home ? path.join(home, '.codex') : '');

const roots = [
  process.env.CENTURION_SKILLS_ROOT || inferredSkillsRoot,
  codexHome && path.join(codexHome, 'skills', '.system'),
].filter(Boolean).filter(fs.existsSync);

function frontmatter(text) {
  if (!text.startsWith('---')) return {};
  const end = text.indexOf('\n---', 3);
  if (end === -1) return {};
  const meta = {};
  const lines = text.slice(3, end).split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!match) continue;
    const key = match[1];
    let value = match[2].trim();
    if (value === '|' || value === '>') {
      const block = [];
      while (i + 1 < lines.length && (/^\s+/.test(lines[i + 1]) || lines[i + 1].trim() === '')) {
        i++;
        block.push(lines[i].replace(/^\s{2,}/, '').trimEnd());
      }
      value = value === '>' ? block.join(' ') : block.join('\n');
    }
    meta[key] = value.replace(/^['"]|['"]$/g, '');
  }
  return meta;
}

const skills = roots.flatMap((root) => fs.readdirSync(root, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => path.join(root, entry.name, 'SKILL.md'))
  .filter(fs.existsSync)
  .map((file) => {
    const text = fs.readFileSync(file, 'utf8');
    const meta = frontmatter(text);
    return {
      name: meta.name || path.basename(path.dirname(file)),
      description: meta.description || '',
      file,
      haystack: `${meta.name || ''} ${meta.description || ''} ${path.basename(path.dirname(file))}`.toLowerCase(),
    };
  }));

const keywords = [...new Set(task.toLowerCase()
  .replace(/[^a-z0-9а-яё_\-\s]/giu, ' ')
  .split(/\s+/)
  .filter((word) => word.length >= 4))];

const skillAliases = {
  orchestrator: ['легион', 'легионер', 'маршрут', 'route', 'orchestr', 'мисси', 'координац'],
  planner: ['план', 'roadmap', 'todo', 'декомпоз', 'milestone'],
  'context-optimizer': ['контекст', 'context window', 'token budget', 'token load', 'токен бюджет', 'memory', 'памят', 'навык', 'скил', 'skill'],
  tester: ['eval', 'test', 'тест', 'проверк', 'coverage', 'qa'],
  security: ['security', 'безопас', 'секрет', 'secret', 'mcp', 'supply', 'dependency', 'vulner'],
  reviewer: ['review', 'ревью', 'code review', 'diff', 'pr', 'pre merge', 'bug risk'],
  researcher: ['research', 'изуч', 'github', 'repo', 'docs', 'web', 'докум'],
  coder: ['code', 'код', 'implement', 'реализ', 'feature', 'api', 'endpoint', 'исправь код'],
  refactorer: ['refactor', 'рефактор', 'cleanup', 'tech debt', 'техдолг', 'без изменения поведения'],
  documenter: ['readme', 'docs', 'documentation', 'документац', 'jsdoc', 'api docs'],
  'error-handler': ['debug', 'stack trace', 'logs', 'логи', 'crash', 'runtime', 'root cause', 'flaky'],
  'skill-quartermaster': ['findskills', 'external skill', 'установ', 'install skill', 'новый навык'],
  pontifex: ['docker', 'infra', 'инфра', 'deploy', 'ci', 'postgres', 'database', 'db'],
  architect: ['architecture', 'архитект', 'module boundary', 'adr', 'system design'],
  aedilis: ['ui', 'ux', 'дизайн', 'interface', 'layout', 'shadcn', 'radix', 'dashboard', 'форма', 'таблица'],
  pictor: ['frontend', 'react', 'vue', 'tailwind', 'css', 'web app', 'landing page', 'лендинг', 'html prototype'],
  'open-design-producer': ['open design', 'open-design', 'landing page', 'лендинг', 'dashboard', 'прототип', 'screenshot', 'скриншот'],
  praeco: ['telegram api', 'bot api', 'mini apps sdk', 'grammy', 'callback_data', 'telegram payments'],
  ludifex: ['telegram mini app game', 'игра', 'game', 'core loop', 'screen map', 'reward model'],
  nomenclator: ['cta', 'microcopy', 'ux writing', 'ux-writing', 'empty state', 'error state', 'naming', 'назван', 'текст интерфейс'],
  glossator: ['i18n', 'localization', 'localisation', 'translation', 'translate', 'перевод', 'plural', 'rtl', 'locale'],
  aleator: ['gamification', 'геймификац', 'rewards', 'streak', 'achievement', 'motivation', 'retention mechanics'],
  mercator: ['marketing', 'growth', 'маркетинг', 'campaign strategy', 'funnel', 'positioning', 'go-to-market'],
  orator: ['social', 'twitter', 'reddit', 'x.com', 'post', 'posts', 'thread', 'caption', 'hashtags', 'посты'],
  indagator: ['seo', 'search engine', 'ranking', 'keywords', 'schema', 'sitemap', 'serp', 'organic'],
  augur: ['phantom1225', 'scamnet', 'dump timing', 'sniper', 'bonding curve'],
  quaestor: ['dex', 'crypto token', 'on-chain', 'onchain', 'technical analysis', 'risk model', 'trading strategy'],
  praemonitor: ['premortem', 'премортем', 'stress test', 'what could kill', 'что может убить'],
};

function aliasScore(skillName, lowerTask) {
  return (skillAliases[skillName] || []).reduce((sum, alias) => sum + (lowerTask.includes(alias) ? 2 : 0), 0);
}

const lower = task.toLowerCase();

const scored = skills.map((skill) => ({
  ...skill,
  score: keywords.reduce((sum, word) => sum + (skill.haystack.includes(word) ? 1 : 0), 0) + aliasScore(skill.name, lower),
}))
  .filter((skill) => skill.score > 0)
  .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));

const dedupedScored = [];
const seenSkills = new Set();
for (const skill of scored) {
  if (seenSkills.has(skill.name)) continue;
  seenSkills.add(skill.name);
  dedupedScored.push(skill);
}

const routeRules = [
  ['orchestrator', ['plan', 'план', 'route', 'orchestr', 'war room', 'мисси', 'легион']],
  ['ludifex', ['telegram mini app game', 'игра', 'game', 'core loop', 'screen map', 'экраны', 'reward model']],
  ['nomenclator', ['cta', 'microcopy', 'ux writing', 'ux-writing', 'empty state', 'error state', 'naming', 'назван', 'текст интерфейс']],
  ['glossator', ['i18n', 'localization', 'localisation', 'translation', 'translate', 'перевод', 'plural', 'rtl', 'locale']],
  ['pictor', ['open design', 'open-design', 'landing page', 'лендинг', 'html prototype', 'create dashboard', 'revise dashboard', 'создать интерфейс', 'изменить интерфейс', 'реализовать интерфейс']],
  ['aedilis', ['ui', 'ux', 'interface', 'интерфейс', 'layout', 'shadcn', 'radix', 'dashboard', 'form', 'table']],
  ['praeco', ['telegram api', 'bot api', 'mini apps sdk', 'grammy', 'callback_data', 'telegram payments']],
  ['orator', ['twitter', 'reddit', 'social', 'посты', 'posts', 'thread', 'caption', 'hashtags']],
  ['indagator', ['seo', 'keyword', 'schema', 'sitemap', 'serp', 'organic', 'search visibility']],
  ['aleator', ['gamification', 'геймификац', 'streak', 'achievement', 'retention mechanics', 'motivation']],
  ['mercator', ['marketing', 'growth', 'campaign', 'funnel', 'positioning', 'go-to-market']],
  ['augur', ['phantom1225', 'scamnet', 'dump timing', 'sniper', 'bonding curve']],
  ['quaestor', ['dex', 'crypto token', 'on-chain', 'onchain', 'technical analysis', 'risk model', 'trading strategy']],
  ['refactorer', ['refactor', 'рефактор', 'cleanup', 'tech debt', 'без изменения поведения']],
  ['documenter', ['readme', 'documentation', 'документац', 'jsdoc', 'api docs']],
  ['error-handler', ['debug', 'stack trace', 'logs', 'логи', 'crash', 'runtime', 'root cause']],
  ['architect', ['architecture', 'архитект', 'system design', 'adr', 'module boundary']],
  ['researcher', ['research', 'изучи', 'изуч', 'docs', 'github', 'repo', 'web']],
  ['coder', ['code', 'код', 'implement', 'реализ', 'fix code', 'исправь код', 'api', 'endpoint']],
  ['tester', ['test', 'coverage', 'eval', 'проверк', 'qa', 'тест']],
  ['reviewer', ['review', 'code review', 'diff', 'pr', 'bug risk', 'ревью кода']],
  ['security', ['security', 'secret', 'vulner', 'mcp', 'install', 'supply', 'безопас', 'защит']],
  ['context-optimizer', ['context', 'context window', 'token budget', 'token load', 'skill surface', 'memory', 'контекст', 'навык', 'скил']],
  ['skill-quartermaster', ['findskills', 'external skill', 'install skill', 'new skill']],
  ['planner', ['roadmap', 'todo', 'milestone', 'knowledge', 'план']],
];

let legionaries = routeRules
  .filter(([, terms]) => terms.some((term) => lower.includes(term)))
  .map(([name]) => name);

function prioritize(items, owner) {
  return items.includes(owner) ? [owner, ...items.filter((item) => item !== owner)] : items;
}

const openDesignProductionIntent = [
  'open design', 'open-design', 'landing page html', 'html prototype',
  'создать лендинг', 'создать интерфейс', 'изменить интерфейс',
  'реализовать интерфейс', 'revise dashboard', 'create dashboard'
].some((term) => lower.includes(term));
const uxArchitectureIntent = [
  'ux', 'visual review', 'design brief', 'дизайн бриф', 'спроектировать',
  'информационная архитектура', 'user flow'
].some((term) => lower.includes(term));

if (openDesignProductionIntent) legionaries = prioritize(legionaries, 'pictor');
else if (uxArchitectureIntent) legionaries = prioritize(legionaries, 'aedilis');

const guardianHardTerms = ['install', 'mcp', 'secret', 'wallet', 'prod', 'cloud', 'external', 'curl', 'npx', 'безопас', 'security', 'supply', 'vulner', 'опас'];
const guardianRiskContext = /(risk|risky|риск)/.test(lower)
  && /(skill|capability|ability|install|mcp|external|способн|навык|скил|установ)/.test(lower);
const guardianTokenContext = /token/.test(lower)
  && /(api|access|auth|secret|credential|env|ключ|секрет|доступ)/.test(lower);
const guardianNeeded = guardianHardTerms.some((term) => lower.includes(term))
  || guardianRiskContext
  || guardianTokenContext;

const routedLegionaries = guardianNeeded && !legionaries.includes('security')
  ? [...legionaries, 'security']
  : legionaries;

console.log(JSON.stringify({
  mission: task,
  doctrine: 'Praeparatio -> Dispositio -> Actio -> Probatio -> Disciplina',
  localSkillCandidates: dedupedScored.slice(0, 8).map(({ name, score, file, description }) => ({ name, score, file, description })),
  primaryLegionary: routedLegionaries[0] || 'orchestrator',
  adjacentLegionaries: [...new Set(routedLegionaries.slice(1))],
  guardianGate: guardianNeeded,
  proofGate: guardianNeeded ? 'security scan + task-specific validation' : 'task-specific validation evidence',
  nextAction: dedupedScored.length ? 'Use local skills first; call Skill Quartermaster only if coverage remains weak.' : 'No strong local skill match; inspect adjacent Legionaries before external discovery.',
}, null, 2));
