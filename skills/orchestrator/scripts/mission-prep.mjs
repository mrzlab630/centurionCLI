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
  'context-optimizer': ['контекст', 'context', 'token', 'токен', 'memory', 'памят', 'навык', 'скил', 'skill'],
  tester: ['eval', 'test', 'тест', 'проверк', 'coverage', 'qa'],
  security: ['security', 'безопас', 'секрет', 'secret', 'mcp', 'supply', 'dependency', 'vulner'],
  reviewer: ['review', 'ревью', 'audit', 'аудит', 'bug', 'ошиб', 'risk', 'риск'],
  researcher: ['research', 'изуч', 'github', 'repo', 'docs', 'web', 'докум'],
  coder: ['code', 'код', 'implement', 'добав', 'исправ', 'refactor', 'рефактор'],
  'skill-quartermaster': ['findskills', 'external skill', 'установ', 'install skill', 'новый навык'],
  pontifex: ['docker', 'infra', 'инфра', 'deploy', 'ci', 'postgres', 'database', 'db'],
  aedilis: ['ui', 'ux', 'дизайн', 'interface', 'layout'],
  pictor: ['frontend', 'react', 'vue', 'tailwind', 'css', 'web app'],
  praeco: ['telegram', 'bot', 'mini app', 'grammy'],
  mercator: ['marketing', 'growth', 'маркетинг', 'retention', 'campaign'],
  indagator: ['seo', 'search engine', 'ranking', 'keywords'],
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
  ['researcher', ['research', 'изучи', 'изуч', 'analy', 'docs', 'github', 'repo', 'web']],
  ['coder', ['code', 'implement', 'fix', 'refactor', 'созд', 'исправ', 'добав', 'действуй']],
  ['tester', ['test', 'coverage', 'eval', 'проверк', 'qa', 'тест']],
  ['reviewer', ['review', 'audit', 'bug', 'risk', 'ошиб', 'ревью', 'проверь']],
  ['security', ['security', 'secret', 'vulner', 'mcp', 'install', 'supply', 'безопас', 'защит']],
  ['context-optimizer', ['context', 'token', 'skill', 'memory', 'контекст', 'навык', 'скил']],
  ['skill-quartermaster', ['findskills', 'external skill', 'install skill', 'new skill']],
  ['planner', ['roadmap', 'todo', 'milestone', 'knowledge', 'план']],
];

const legionaries = routeRules
  .filter(([, terms]) => terms.some((term) => lower.includes(term)))
  .map(([name]) => name);

const guardianNeeded = ['install', 'mcp', 'secret', 'token', 'wallet', 'prod', 'cloud', 'external', 'curl', 'npx', 'безопас', 'security', 'supply', 'risk', 'risky', 'риск', 'опас']
  .some((term) => lower.includes(term));

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
