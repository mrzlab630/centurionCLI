#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT, LOAD_MAP, INTEGRATION_MAP, BUNDLE_MAP, walkFiles } from '../../../integrations/codex-legion-kit/scripts/lib/surface-config.mjs';

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export function instructionViolations(text) {
  const hits = [];
  // Match actionable instructions, not merely historical names or negated prohibitions.
  for (const [i,line] of text.split('\n').entries()) {
    const clauses = line.split(/(?<=[.!;])\s+/);
    for (const clause of clauses) {
      if (/\b(?:no|never|not|excluded|historical|without|optional|only if specified)\b/i.test(clause)) continue;
      const patterns = [
        /\b(?:always|must|mandatory|required|run|use|invoke|load)\b.*\b(?:WAR ROOM|tribunal|delegate_task|agy|kanban|mission_control\.py|evocate\.sh)\b/i,
        /\b(?:80\s*%|80 percent)\s*(?:test\s*)?coverage\b/i,
        /\b(?:fix|repair)\b.*\b(?:every|all|any)\b.*\b(?:fail|test)/i,
        /\b(?:3|three)\s+(?:autonomous\s+|mandatory\s+)?retr(?:y|ies)/i,
        /\b(?:automatically|always|must)\b.*\b(?:publish|install skills?|create helpers?|delegate|call (?:TESTER|REVIEWER|CODER|GUARDIAN|EXPLORATOR|CURATOR))\b/i,
      ];
      if (patterns.some(re=>re.test(clause))) hits.push({ line:i+1, reason:'active ceremony or unbounded authority', text:clause.trim() });
    }
  }
  const stale = /\b(?:gpt-6-sol|gpt-5[\w.-]*|claude-sonnet[\w.-]*|claude-fable[\w.-]*|gemini[\w.-]*|claude-opus-5(?!-5)[\w.-]*)\b/gi;
  for (const m of text.matchAll(stale)) hits.push({ reason:'stale model route', text:m[0] });
  return hits;
}
export function auditSurface({ consumerRoots = [], skillsRoot = path.join(REPO_ROOT,'skills') } = {}) {
  const roots = [skillsRoot,
    path.join(REPO_ROOT,'integrations/hermes-legion-kit/skills'),
    path.join(REPO_ROOT,'integrations/hermes-legion-kit/overrides'),
    path.join(REPO_ROOT,'integrations/codex-legion-kit/skills'),
    path.join(REPO_ROOT,'integrations/claude-legion-kit/plugin'),
    path.join(REPO_ROOT,'integrations/antigravity-legion-kit/agy-plugin/skills'),
    ...consumerRoots];
  const files = [...new Set(roots.flatMap(walkFiles))];
  const skillFiles = files.filter(f=>path.basename(f)==='SKILL.md');
  const records = skillFiles.map(file=>{
    const text = fs.readFileSync(file,'utf8');
    const name = text.match(/^name:\s*(.+)$/m)?.[1] || path.basename(path.dirname(file));
    const description = text.match(/^description:\s*(.+)$/m)?.[1] || '';
    const layer = Object.entries(LOAD_MAP).find(([,names])=>names.includes(name))?.[0] || 'integration';
    const excluded = layer==='excluded' || file.includes('/antigravity-') || file.includes('/research-paper-writing/');
    return { name, file, layer, excluded, hash:sha256(text), lines:text.split('\n').length,
      estTokens:Math.round(text.split(/\s+/).length*1.3), descriptionWords:description.split(/\s+/).length };
  });
  const activeFiles = files.filter(file=>/\/(?:SKILL|AGENTS|CLAUDE|SOUL|PROBATIO)\.md$/.test(file) || /\/(?:agents|output-styles|overrides|skill-bundles)\/[^/]+\.(?:md|yaml)$/.test(file));
  activeFiles.push(...['CLAUDE.md','PROBATIO.md'].map(f=>path.join(REPO_ROOT,f)));
  activeFiles.push(...walkFiles(path.join(REPO_ROOT,'integrations/hermes-legion-kit/skill-bundles')));
  // Traverse actual markdown links from entrypoints, not every example path in the library.
  const linked = [...activeFiles];
  for(let i=0;i<linked.length;i++) {
    const file=linked[i]; if(!file.endsWith('.md'))continue;
    const text=fs.readFileSync(file,'utf8').replace(/```[\s\S]*?```/g,'');
    for(const m of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      const ref=m[1].split('#')[0]; if(!ref || /^(?:https?:|app:)/.test(ref))continue;
      const target=path.resolve(path.dirname(file),ref);
      if(target.endsWith('.md') && fs.existsSync(target) && !linked.includes(target))linked.push(target);
    }
  }
  activeFiles.push(...linked);
  const violations = [], brokenReferences = [];
  for (const file of [...new Set(activeFiles)]) {
    if (file.includes('/antigravity-') || file.includes('/research-paper-writing/')) continue;
    const text=fs.readFileSync(file,'utf8');
    for (const hit of instructionViolations(text)) violations.push({file,...hit});
    if (!file.endsWith('.md')) continue;
    for (const m of text.replace(/```[\s\S]*?```/g,'').matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      const ref=m[1].split('#')[0];
      if (!ref || /^(?:https?:|app:)/.test(ref) || ref.includes('<')) continue;
      if (!fs.existsSync(path.resolve(path.dirname(file),ref))) brokenReferences.push({file,reference:ref});
    }
  }
  const bundleErrors=[];
  for (const [file,expected] of Object.entries(BUNDLE_MAP)) {
    const p=path.join(REPO_ROOT,'integrations/hermes-legion-kit/skill-bundles',file);
    const text=fs.readFileSync(p,'utf8');
    const selected=[...text.matchAll(/^- ([\w-]+)$/gm)].map(m=>m[1]);
    if (JSON.stringify(selected)!==JSON.stringify(expected)) bundleErrors.push({file,reason:'bundle differs from load map'});
    for (const name of selected) {
      if (!Object.values(INTEGRATION_MAP).flat().some(p=>path.basename(p)===name) && !LOAD_MAP.domain.includes(name)) bundleErrors.push({file,reason:'unowned bundle dependency',name});
    }
  }
  // Repository projections intentionally repeat names; duplicates are meaningful within one consumer only.
  const duplicates=[];
  for (const root of [skillsRoot,...consumerRoots]) {
    const names=new Map();
    for (const r of records.filter(r=>r.file.startsWith(root+path.sep))) {
      const old=names.get(r.name); if (old) duplicates.push({name:r.name,files:[old.file,r.file],drift:old.hash!==r.hash}); else names.set(r.name,r);
    }
  }
  return { scannedRoots:roots,skillCount:records.length,records,
    duplicateNameCount:duplicates.length,driftedDuplicateCount:duplicates.filter(d=>d.drift).length,duplicates,
    longDescriptions:records.filter(r=>!r.excluded && r.descriptionWords>30), violations,brokenReferences,bundleErrors,
    totalEstimatedTokens:records.reduce((n,r)=>n+r.estTokens,0),
    ok:!violations.length && !brokenReferences.length && !bundleErrors.length && !duplicates.length };
}
if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const roots=[];
  for(let i=2;i<process.argv.length;i++) {
    if (process.argv[i]==='--consumer-root' && process.argv[i+1]) roots.push(path.resolve(process.argv[++i]));
    else if (process.argv[i]!=='--json') throw new Error('Use --consumer-root <isolated root>');
  }
  const result=auditSurface({consumerRoots:roots,skillsRoot:process.env.CENTURION_SKILLS_ROOT || path.join(REPO_ROOT,'skills')});
  console.log(JSON.stringify(result,null,2)); if(!result.ok) process.exitCode=1;
}
