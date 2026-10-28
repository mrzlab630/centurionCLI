import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
export const PRODUCT_VERSION = '3.0.0-rc.5';
export const LOAD_MAP = Object.freeze({
  core: ['orchestrator'],
  incorporated: ['planner', 'context-optimizer'],
  domain: ['aedilis','aleator','architect','augur','capabilities','censor','coder',
    'documenter','error-handler','git-master','glossator','haruspex','indagator',
    'ludifex','mercator','nomenclator','orator','pictor',
    'pontifex','praeco','praemonitor','prompt-engineer','quaestor','refactorer',
    'researcher','reviewer','security','tabularius','tester','velites'],
  maintenance: ['artifex','skill-quartermaster'],
  excluded: ['evocate-ad-opus','sicarius']
});
export const INTEGRATION_MAP = Object.freeze({
  core: ['autonomous-ai-agents/aquila-team-orchestration',
    'autonomous-ai-agents/agent-contract-runner'],
  domain: ['autonomous-ai-agents/aquila-execution-state',
    'software-development/solana-program-engineering'],
  maintenance: ['autonomous-ai-agents/aquila-harness-audit',
    'autonomous-ai-agents/aquila-executor-eval','autonomous-ai-agents/aquila-self-debug'],
  excluded: ['overrides/skills/research/research-paper-writing',
    'codex-legion-kit/skills/camofox-browser', 'antigravity-legion-kit']
});
export const BUNDLE_MAP = Object.freeze({
  'aquila-delivery.yaml': ['aquila-team-orchestration','agent-contract-runner'],
  'aquila-executor-eval.yaml': ['aquila-executor-eval','aquila-team-orchestration','agent-contract-runner'],
  'aquila-harness-audit.yaml': ['aquila-harness-audit','aquila-self-debug']
});
export const COMPATIBILITY = Object.freeze({
  productVersion: PRODUCT_VERSION,
  contract: 'AGENT_ORDER_JSON_V1/AGENT_RESULT_JSON_V1/AGENT_HANDOFF_V1',
  launch: 'result_gateway.py',
  adapterVersion: 'centurion-native-v3',
  capabilityBinding: ['binarySha256','binaryVersion','configSha256','routeSha256','adapterSha256'],
  onChange: 'invalidate receipt; maintenance-only capability validation, never dispatch probes or auto-update',
  optional: ['camofox','markitdown'],
  archived: ['open-design'],
  excluded: ['deep-search.js','browse.js','Perplexity','Memoria','sequential-thinking','pal',
    'mission_control.py','evocate.sh','delegate_task','agy','kanban']
});
export const EXPECTED_SKILLS = Object.freeze(Object.values(LOAD_MAP).flat().sort());
export const EXPECTED_SKILL_COUNT = EXPECTED_SKILLS.length;
export const SHARED_CAPABILITIES = Object.freeze([]);
// Historical owned files remain recognizable for safe retirement, never selection.
export const ARCHIVED_SKILLS = Object.freeze({
  'open-design-producer': path.join(REPO_ROOT, 'archive/open-design/skills/open-design-producer')
});
export const ARCHIVED_BUNDLES = Object.freeze(['aquila-design-production.yaml']);
export function selectSkills(profile, requested = [], client = 'codex') {
  if (!['core','domain','maintenance'].includes(profile)) throw new Error('Explicit --profile core|domain|maintenance required');
  const available = profile === 'core' ? [] : [...LOAD_MAP[profile],
    ...(client === 'hermes' ? INTEGRATION_MAP[profile].map(p=>path.basename(p)) : [])];
  for (const slug of requested) if (!available.includes(slug)) throw new Error(`Skill outside ${profile} allowlist: ${slug}`);
  if (profile !== 'core' && !requested.length) throw new Error('Select domain/maintenance skills explicitly with --skill');
  return [...LOAD_MAP.core, ...new Set(requested)].sort();
}
const IGNORED = new Set(['.git','.next','.venv','__pycache__','build','coverage',
  'dist','generated','node_modules','reports','vendor','backups','.reference-cache']);
export function isIgnoredGeneratedDir(name) {
  return IGNORED.has(name) || /(?:centurion-(?:backup|stage)|\.bak(?:$|[-.])|backup[-_])/i.test(name);
}
export function walkFiles(root) {
  if (!fs.existsSync(root)) return [];
  const files = [];
  for (const e of fs.readdirSync(root, { withFileTypes: true })) {
    if (isIgnoredGeneratedDir(e.name) || e.name.endsWith('.pyc')) continue;
    const p = path.join(root, e.name);
    if (e.isSymbolicLink()) throw new Error(`Symlink surface conflict: ${p}`);
    if (e.isDirectory()) files.push(...walkFiles(p));
    else files.push(p);
  }
  return files.sort();
}
