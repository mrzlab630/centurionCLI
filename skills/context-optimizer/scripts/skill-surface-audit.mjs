#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const inferredSkillsRoot = path.resolve(scriptDir, '..', '..');
const home = process.env.HOME || '';
const codexHome = process.env.CODEX_HOME || (home ? path.join(home, '.codex') : '');
const roots = [
  process.env.CENTURION_SKILLS_ROOT || inferredSkillsRoot,
  codexHome && path.join(codexHome, 'skills', '.system'),
  codexHome && path.join(codexHome, 'skills', 'migrate-to-codex'),
].filter(Boolean).filter((root) => fs.existsSync(root));

function walkSkillFiles(root) {
  const directSkill = path.join(root, 'SKILL.md');
  if (fs.existsSync(directSkill)) return [directSkill];
  return fs.readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(root, entry.name, 'SKILL.md'))
    .filter((file) => fs.existsSync(file));
}

function rootKind(root) {
  if (root.includes('/.codex/skills/.system')) return 'system';
  if (root.includes('/.codex/skills/')) return 'codex-extra';
  return 'legion';
}

function frontmatter(text) {
  if (!text.startsWith('---')) return {};
  const end = text.indexOf('\n---', 3);
  if (end === -1) return {};
  const data = {};
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
    data[key] = value.replace(/^['"]|['"]$/g, '');
  }
  return data;
}

const records = roots.flatMap((root) => walkSkillFiles(root).map((file) => {
  const text = fs.readFileSync(file, 'utf8');
  const meta = frontmatter(text);
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return {
    name: meta.name || path.basename(path.dirname(file)),
    kind: rootKind(root),
    root,
    file,
    lines: text.split('\n').length,
    estTokens: Math.round(words * 1.3),
    descriptionWords: (meta.description || '').split(/\s+/).filter(Boolean).length,
    hash: null,
    text,
  };
}));

const { createHash } = await import('node:crypto');
for (const record of records) {
  record.hash = createHash('sha256').update(record.text).digest('hex');
  delete record.text;
}

const byName = new Map();
for (const record of records) {
  if (!byName.has(record.name)) byName.set(record.name, []);
  byName.get(record.name).push(record);
}

const duplicates = [...byName.entries()]
  .filter(([, items]) => items.length > 1)
  .map(([name, items]) => ({
    name,
    count: items.length,
    drift: new Set(items.map((item) => item.hash)).size > 1,
    files: items.map((item) => item.file),
  }));

const driftedDuplicates = duplicates.filter((item) => item.drift);

const heavy = [...records].sort((a, b) => b.estTokens - a.estTokens).slice(0, 12);
const longDescriptions = records
  .filter((record) => record.kind !== 'system')
  .filter((record) => record.descriptionWords > 30)
  .sort((a, b) => b.descriptionWords - a.descriptionWords)
  .slice(0, 12);
const systemLongDescriptions = records
  .filter((record) => record.kind === 'system')
  .filter((record) => record.descriptionWords > 30)
  .sort((a, b) => b.descriptionWords - a.descriptionWords)
  .slice(0, 12);

console.log(JSON.stringify({
  scannedRoots: roots,
  skillCount: records.length,
  duplicateNameCount: duplicates.length,
  driftedDuplicateCount: driftedDuplicates.length,
  totalEstimatedTokens: records.reduce((sum, record) => sum + record.estTokens, 0),
  heavy,
  longDescriptions,
  systemLongDescriptions,
  duplicates: duplicates.slice(0, 20),
  driftedDuplicates: driftedDuplicates.slice(0, 20),
  nextActions: [
    'Review duplicate names for drift before archiving or merging copies.',
    'Move long examples from heavy SKILL.md files into references or scripts.',
    'Shorten descriptions over 30 words because metadata is always visible to skill selection.',
  ],
}, null, 2));
