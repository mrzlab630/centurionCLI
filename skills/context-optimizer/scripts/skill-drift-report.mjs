#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const inferredSkillsRoot = path.resolve(scriptDir, '..', '..');
const home = process.env.HOME || '';
const codexHome = process.env.CODEX_HOME || (home ? path.join(home, '.codex') : '');

const roots = [
  process.env.CENTURION_SKILLS_ROOT || inferredSkillsRoot,
  codexHome && path.join(codexHome, 'skills', '.system'),
  codexHome && path.join(codexHome, 'skills', 'migrate-to-codex'),
].filter(Boolean).filter(fs.existsSync);

function skillFiles(root) {
  const directSkill = path.join(root, 'SKILL.md');
  if (fs.existsSync(directSkill)) return [directSkill];
  return fs.readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(root, entry.name, 'SKILL.md'))
    .filter(fs.existsSync);
}

function frontmatter(text) {
  if (!text.startsWith('---')) return {};
  const end = text.indexOf('\n---', 3);
  if (end === -1) return {};
  const data = {};
  const lines = text.slice(3, end).split('\n');
  for (let i = 0; i < lines.length; i++) {
    const match = lines[i].match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
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

function hash(text) {
  return createHash('sha256').update(text).digest('hex');
}

const byName = new Map();
for (const root of roots) {
  for (const file of skillFiles(root)) {
    const text = fs.readFileSync(file, 'utf8');
    const meta = frontmatter(text);
    const name = meta.name || path.basename(path.dirname(file));
    if (!byName.has(name)) byName.set(name, []);
    byName.get(name).push({
      name,
      root,
      file,
      hash: hash(text),
      lines: text.split('\n').length,
      estTokens: Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.3),
      description: meta.description || '',
    });
  }
}

const drifted = [...byName.entries()]
  .filter(([, items]) => items.length > 1 && new Set(items.map((item) => item.hash)).size > 1)
  .map(([name, items]) => ({
    name,
    copies: items.map(({ file, lines, estTokens, description }) => ({ file, lines, estTokens, description })),
    recommendation: name === 'orchestrator' || name === 'researcher' || name === 'coder'
      ? 'manual review: likely harness-specific behavior mixed with shared doctrine'
      : 'manual review: either align shared doctrine or document intentional divergence',
  }))
  .sort((a, b) => a.name.localeCompare(b.name));

console.log(JSON.stringify({
  driftedCount: drifted.length,
  drifted,
  nextActions: [
    'Do not auto-merge drifted skills without reading both copies.',
    'Keep one active canonical skill name; archive superseded copies outside active roots.',
    'After manual alignment, rerun legion-skill-eval.mjs.',
  ],
}, null, 2));
