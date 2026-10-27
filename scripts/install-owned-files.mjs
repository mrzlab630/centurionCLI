#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { selectSkills, LOAD_MAP, INTEGRATION_MAP, BUNDLE_MAP, COMPATIBILITY, PRODUCT_VERSION, ARCHIVED_SKILLS, ARCHIVED_BUNDLES, isIgnoredGeneratedDir, walkFiles } from '../integrations/codex-legion-kit/scripts/lib/surface-config.mjs';

const SOURCE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const INSTRUCTION_START = '\n\n<!-- CENTURION_MANAGED_V3_START -->\n';
const INSTRUCTION_END = '\n<!-- CENTURION_MANAGED_V3_END -->\n';

function parseArgs(args) {
  const o = { skills: [], dryRun: false };
  const values = { '--agents-home':'agentsHome', '--claude-home':'claudeHome',
    '--codex-home':'codexHome', '--hermes-home':'hermesHome', '--profile':'profile',
    '--client':'client', '--capability-record':'capabilityRecord', '--migration-record':'migrationRecord' };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--help') { o.help = true; continue; }
    if (arg === '--dry-run') { o.dryRun = true; continue; }
    if (arg === '--skill') {
      if (!args[i+1] || args[i+1].startsWith('--')) throw new Error('Missing --skill value');
      o.skills.push(args[++i]); continue;
    }
    if (!values[arg] || !args[i+1] || args[i+1].startsWith('--')) throw new Error(`Unknown/missing argument: ${arg}`);
    o[values[arg]] = args[++i];
  }
  if (o.help) return o;
  o.client ||= 'codex';
  if (!['codex','claude','hermes'].includes(o.client)) throw new Error('Unsupported client');
  o.selected = selectSkills(o.profile, o.skills, o.client);
  const key = { codex:'agentsHome', claude:'claudeHome', hermes:'hermesHome' }[o.client];
  if (!o[key] || (o.client === 'codex' && !o.codexHome)) throw new Error('Explicit target homes required');
  o.skillHome = path.resolve(o[key]);
  o.nativeHome = path.resolve(o.client === 'codex' ? o.codexHome : o[key]);
  if (o.client === 'codex' && o.skillHome === o.nativeHome) throw new Error('Codex and Agents homes must differ');
  return o;
}

function lstatOrNull(target) {
  try { return fs.lstatSync(target); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function expectedMode(source, kind) {
  if (kind === 'directory') return 0o755;
  if (source.endsWith('.py')) return 0o644;
  return fs.statSync(source).mode & 0o111 ? 0o755 : 0o644;
}

function excludedSource(current, name) {
  if (current.endsWith('/skills/orchestrator') && name==='scripts') return true;
  if (current.endsWith('/skills/tester') && name==='scripts') return true;
  if (current.endsWith('/skills/skill-quartermaster') && name==='scripts') return true;
  if (current.includes('/skills/researcher') && ['scripts','package.json','package-lock.json'].includes(name)) return true;
  if (current.includes('/skills/autonomous-ai-agents/') && !current.includes('/agent-contract-runner') && name==='references') return true;
  return ['deep-search.js','browse.js','check-deps.js','monid-adapter.js','mission_control.py','mission-prep.mjs','evocate.sh','findskills-audit.mjs','legion-skill-eval.mjs'].includes(name);
}
function isGenerated(name) {
  return isIgnoredGeneratedDir(name) || name.endsWith('.pyc');
}

function inspectTree(root, source = false) {
  const entries = [];
  function visit(current, relative) {
    const stats = fs.lstatSync(current);
    if (stats.isSymbolicLink()) throw new Error(`Symlink in ${source ? 'source' : 'staged target'}: ${current}`);
    if (stats.isDirectory()) {
      entries.push({ path: relative, kind: 'directory', mode: source ? expectedMode(current, 'directory') : stats.mode & 0o777 });
      for (const name of fs.readdirSync(current).sort()) {
        if (source && (isGenerated(name) || excludedSource(current,name))) continue;
        visit(path.join(current, name), path.join(relative, name));
      }
    } else if (stats.isFile()) {
      entries.push({
        path: relative,
        kind: 'file',
        mode: source ? expectedMode(current, 'file') : stats.mode & 0o777,
        sha256: crypto.createHash('sha256').update(fs.readFileSync(current)).digest('hex')
      });
    } else {
      throw new Error(`Unsupported file type: ${current}`);
    }
  }
  visit(root, '.');
  return JSON.stringify(entries);
}

function copyExact(source, destination) {
  const stats = fs.lstatSync(source);
  if (stats.isSymbolicLink()) throw new Error(`Symlink in source: ${source}`);
  if (stats.isDirectory()) {
    fs.mkdirSync(destination, { mode: 0o755 });
    fs.chmodSync(destination, 0o755);
    for (const name of fs.readdirSync(source).sort()) {
      if (isGenerated(name) || excludedSource(source,name)) continue;
      copyExact(path.join(source, name), path.join(destination, name));
    }
  } else if (stats.isFile()) {
    fs.copyFileSync(source, destination);
    fs.chmodSync(destination, expectedMode(source, 'file'));
  } else {
    throw new Error(`Unsupported file type: ${source}`);
  }
}

const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
export function preservedInstructionParts(bytes,record) {
  const {prefixBytes,suffixBytes,prefixSha256,suffixSha256}=record;
  if (!Number.isSafeInteger(prefixBytes) || prefixBytes<0 || !Number.isSafeInteger(suffixBytes) || suffixBytes<0 || prefixBytes+suffixBytes>=bytes.length) throw new Error('Invalid preserved instruction ranges');
  const prefix=bytes.subarray(0,prefixBytes),suffix=bytes.subarray(bytes.length-suffixBytes);
  if (sha(prefix)!==prefixSha256 || sha(suffix)!==suffixSha256) throw new Error('Preserved instruction ranges/hash mismatch');
  const managed=bytes.subarray(prefixBytes,bytes.length-suffixBytes);
  const start=Buffer.from(INSTRUCTION_START),end=Buffer.from(INSTRUCTION_END),marker=Buffer.from('<!-- CENTURION_MANAGED_V3_');
  const body=managed.subarray(start.length,managed.length-end.length);
  if (managed.length<=start.length+end.length || !managed.subarray(0,start.length).equals(start) ||
      !managed.subarray(managed.length-end.length).equals(end) || !body.toString('utf8').trim() ||
      prefix.includes(marker) || suffix.includes(marker) || body.includes(marker)) throw new Error('Invalid preserved instruction managed wrapper');
  return {prefix,managed,suffix};
}

function listOperations(options) {
  const operations = [];
  const add = (source, target) => operations.push({ source, target });
  const home = options.nativeHome;
  const skillsTarget = path.join(options.skillHome, 'skills');
  for (const name of options.selected) {
    if (!Object.values(LOAD_MAP).flat().includes(name)) continue;
    const sourceDir = path.join(SOURCE_ROOT, 'skills', name);
    const targetDir = path.join(skillsTarget, name);
    add(sourceDir, targetDir);
  }
  add(path.join(SOURCE_ROOT, 'CLAUDE.md'), path.join(home, options.client === 'claude' ? 'CLAUDE.md' : options.client === 'hermes' ? 'SOUL.md' : 'AGENTS.md'));
  add(path.join(SOURCE_ROOT, 'PROBATIO.md'), path.join(home, 'PROBATIO.md'));
  if (options.client === 'codex') {
    // The pointer is relative to native home; keep the canonical core in the shared skill home.
    options.corePointer = path.relative(home, path.join(skillsTarget, 'orchestrator', 'SKILL.md'));
  }
  if (options.client === 'hermes') {
    const kit = path.join(SOURCE_ROOT, 'integrations/hermes-legion-kit');
    const selectedIntegration = [...INTEGRATION_MAP.core];
    selectedIntegration.push(...[...INTEGRATION_MAP.domain,...INTEGRATION_MAP.maintenance]
      .filter(rel=>options.selected.includes(path.basename(rel))));
    for (const rel of selectedIntegration) add(path.join(kit, 'skills', rel), path.join(skillsTarget, rel));
    const names = new Set([...options.selected, ...selectedIntegration.map(r => path.basename(r))]);
    for (const [file, required] of Object.entries(BUNDLE_MAP)) {
      if (required.every(n => names.has(n))) add(path.join(kit,'skill-bundles',file), path.join(home,'skill-bundles',file));
    }
    for (const name of ['AQUILA_SOUL_OVERRIDES','SOUL_CLAUDE_ROLE_RULE','SOUL_RUNTIME_MODEL_RULE','ADAPTIVE_MODEL_ROUTING_POLICY']) {
      add(path.join(kit,'overrides',name+'.md'),path.join(home,'centurion','overrides',name+'.md'));
    }
  }
  if (options.client === 'claude') {
    options.pluginSource = path.join(SOURCE_ROOT, 'integrations/claude-legion-kit/plugin');
    options.pluginTarget = path.join(skillsTarget, 'centurion-legion');
  }
  for(const name of ['package.json','package-lock.json']) {
    const source=path.join(SOURCE_ROOT,`integrations/${options.client}-legion-kit`,name);
    if(fs.existsSync(source)) add(source,path.join(home,'centurion','package',name));
  }
  add(path.join(SOURCE_ROOT,'integrations/codex-legion-kit/scripts/lib/surface-config.mjs'),path.join(home,'centurion','surface-config.mjs'));
  if (options.selected.some(n=>['haruspex','velites'].includes(n))) {
    for(const name of fs.readdirSync(path.join(SOURCE_ROOT,'libs')).filter(n=>n.endsWith('.py'))) {
      add(path.join(SOURCE_ROOT,'libs',name),path.join(options.skillHome,'libs',name));
    }
  }
  return { operations, skillCount: options.selected.length };
}

export function rejectInstallSymlinks(target) {
  let cursor = path.resolve(target);
  while (true) {
    if (lstatOrNull(cursor)?.isSymbolicLink()) throw new Error('Symlink install ancestor: '+cursor);
    const parent = path.dirname(cursor); if (parent === cursor) break; cursor = parent;
  }
}

// Enumerate repository-defined package names only. Never discover ownership by
// walking a client home, or by trusting arbitrary paths in a supplied receipt.
export function managedFileCatalogue(o) {
  const names = new Set();
  const add = (source,target) => {
    const stats = fs.lstatSync(source);
    if (stats.isSymbolicLink()) throw new Error('Symlink in package source: '+source);
    if (stats.isDirectory()) for (const file of walkFiles(source)) {
      const relative=path.relative(source,file);
      if (!relative.split(path.sep).some(part=>['.centurion','memory'].includes(part))) names.add(path.join(target,relative));
    }
    else names.add(target);
  };
  for (const name of Object.values(LOAD_MAP).flat()) {
    add(path.join(SOURCE_ROOT,'skills',name),path.join(o.skillHome,'skills',name));
  }
  for (const [name, source] of Object.entries(ARCHIVED_SKILLS)) {
    const rel = o.client === 'hermes' ? 'autonomous-ai-agents/' + name : name;
    add(source, path.join(o.skillHome, 'skills', rel));
  }
  for (const name of ['AGENTS.md','CLAUDE.md','SOUL.md'].filter(n=>n===({codex:'AGENTS.md',claude:'CLAUDE.md',hermes:'SOUL.md'}[o.client]))) names.add(path.join(o.nativeHome,name));
  for (const rel of ['PROBATIO.md','centurion/installed-chain.json','centurion/open-design-bridge.json','centurion/surface-config.mjs']) names.add(path.join(o.nativeHome,rel));
  for (const name of ['package.json','package-lock.json']) {
    const source=path.join(SOURCE_ROOT,'integrations',o.client+'-legion-kit',name);
    if (fs.existsSync(source)) names.add(path.join(o.nativeHome,'centurion/package',name));
  }
  for (const name of fs.readdirSync(path.join(SOURCE_ROOT,'libs')).filter(n=>n.endsWith('.py'))) names.add(path.join(o.skillHome,'libs',name));
  if (o.client === 'claude') add(path.join(SOURCE_ROOT,'integrations/claude-legion-kit/plugin'),path.join(o.skillHome,'skills/centurion-legion'));
  if (o.client === 'claude') for (const rel of ['lib/claude-result-validator.mjs','scripts/claude-order-guard.mjs']) names.add(path.join(o.skillHome,'skills/centurion-legion',rel));
  if (o.client === 'claude') names.add(path.join(o.skillHome,'skills/centurion-legion/scripts/open-design-mcp.mjs'));
  if (o.client === 'hermes') {
    const kit=path.join(SOURCE_ROOT,'integrations/hermes-legion-kit');
    for (const rel of [...INTEGRATION_MAP.core,...INTEGRATION_MAP.domain,...INTEGRATION_MAP.maintenance]) add(path.join(kit,'skills',rel),path.join(o.skillHome,'skills',rel));
    for (const file of Object.keys(BUNDLE_MAP)) names.add(path.join(o.nativeHome,'skill-bundles',file));
    for (const file of ARCHIVED_BUNDLES) names.add(path.join(o.nativeHome,'skill-bundles',file));
    for (const file of ['AQUILA_SOUL_OVERRIDES','SOUL_CLAUDE_ROLE_RULE','SOUL_RUNTIME_MODEL_RULE','ADAPTIVE_MODEL_ROUTING_POLICY']) names.add(path.join(o.nativeHome,'centurion/overrides',file+'.md'));
  }
  return names;
}

export function validateManagedRows(rows,catalogue) {
  const seen=new Set();
  if (!Array.isArray(rows)) throw new Error('Invalid managed manifest files');
  for (const row of rows) {
    if (!row || typeof row.installedPath!=='string' || !catalogue.has(row.installedPath) || row.installedPath.endsWith('/centurion/installed-chain.json') ||
        path.resolve(row.installedPath)!==row.installedPath || seen.has(row.installedPath) ||
        !/^[a-f0-9]{64}$/.test(row.installedSha256) ||
        (row.installedMode!==undefined && (!Number.isInteger(row.installedMode) || row.installedMode<0 || row.installedMode>0o777))) throw new Error('Invalid managed manifest path/hash/mode');
    seen.add(row.installedPath);
  }
}

export function isManagedInstructionOrControl(file) {
  return /\/(?:SKILL|AGENTS|CLAUDE|SOUL|PROBATIO)\.md$/.test(file) ||
    /\/(?:agents|output-styles|overrides|skill-bundles)\/[^/]+\.(?:md|yaml)$/.test(file) ||
    /\/(?:mission_control\.py|mission-prep\.mjs|evocate\.sh|claude-order-guard\.mjs)$/.test(file);
}

function verifiedPreimage(row) {
  rejectInstallSymlinks(row.installedPath);
  const stats=lstatOrNull(row.installedPath);
  if (!stats?.isFile()) throw new Error('Managed preimage missing or not a regular file: '+row.installedPath);
  const before=inspectTree(row.installedPath);
  const entry=JSON.parse(before)[0];
  if (entry.sha256!==row.installedSha256 || (row.installedMode!==undefined && entry.mode!==row.installedMode)) throw new Error('Managed preimage changed (unchanged): '+row.installedPath);
  return before;
}

function ownership(o) {
  rejectInstallSymlinks(o.nativeHome); rejectInstallSymlinks(o.skillHome);
  const catalogue=managedFileCatalogue(o);
  const priorPath=path.join(o.nativeHome,'centurion/installed-chain.json');
  rejectInstallSymlinks(priorPath);
  const priorStats=lstatOrNull(priorPath);
  if (priorStats && !priorStats.isFile()) throw new Error('Prior manifest is not a regular file');
  const priorBytes=priorStats ? fs.readFileSync(priorPath) : null;
  const prior=priorBytes ? JSON.parse(priorBytes) : null;
  if (prior && (prior.manifestVersion!=='CENTURION_INSTALLED_CHAIN_V1' || prior.client!==o.client)) throw new Error('Invalid prior manifest identity');
  if (prior) validateManagedRows(prior.files,catalogue);
  if (prior && o.migrationRecord) throw new Error('Migration record requires a legacy home without an installed-chain manifest');
  const migration=o.migrationRecord ? JSON.parse(fs.readFileSync(o.migrationRecord,'utf8')) : null;
  if (migration && (migration.migrationVersion!=='CENTURION_INSTALL_MIGRATION_V1' || migration.client!==o.client)) throw new Error('Invalid migration record identity');
  if (migration) {
    validateManagedRows(migration.files,catalogue);
    for (const row of migration.files) {
      if (!['replace','retire','preserve-instruction'].includes(row.action) || row.installedPath===priorPath) throw new Error('Invalid migration action: '+row.installedPath);
      if (row.action==='preserve-instruction' && row.installedPath!==path.join(o.nativeHome,{codex:'AGENTS.md',claude:'CLAUDE.md',hermes:'SOUL.md'}[o.client])) throw new Error('Preservation is limited to the native instruction entrypoint');
    }
  }
  const rows=[...(prior?.files || []),...(migration?.files || [])];
  const preimages=new Map(rows.map(r=>[r.installedPath,verifiedPreimage(r)]));
  return {prior,migration,rows,preimages,catalogue,priorPath,priorSha256:priorBytes ? sha(priorBytes) : null};
}

function conflictInventory(state,operations) {
  const targets=new Set(operations.map(op=>op.target));
  const acknowledged=new Set([...targets,...state.rows.map(r=>r.installedPath)]);
  for (const file of state.catalogue) if (isManagedInstructionOrControl(file) && !acknowledged.has(file)) {
    rejectInstallSymlinks(file);
    if (lstatOrNull(file)) throw new Error('Foreign managed instruction/control path; explicit migration retirement required (unchanged): '+file);
  }
  for (const row of state.migration?.files || []) if (row.action!=='retire' && !targets.has(row.installedPath)) throw new Error('Migration replacement is outside selected targets: '+row.installedPath);
  for (const op of operations) {
    rejectInstallSymlinks(op.target);
    const existing=lstatOrNull(op.target);
    if (!existing) { op.preflightBefore=null; continue; }
    if (!existing.isFile()) throw new Error('Unsafe managed target type: '+op.target);
    const expected=state.preimages.get(op.target);
    if (op.target===state.priorPath && state.priorSha256) {
      op.preflightBefore=inspectTree(op.target);
      if (JSON.parse(op.preflightBefore)[0].sha256!==state.priorSha256) throw new Error('Prior manifest changed during install');
    } else {
      if (!expected) throw new Error('Foreign managed-path conflict; explicit migration preimage required (unchanged): '+op.target);
      op.preflightBefore=inspectTree(op.target);
      if (op.preflightBefore!==expected) throw new Error('Managed preimage changed during planning: '+op.target);
    }
  }
}

function capability(o) {
  if (!o.capabilityRecord) return { client:o.client, status:'excluded', reason:'missing binary/config/route/adapter evidence' };
  const r = JSON.parse(fs.readFileSync(o.capabilityRecord,'utf8'));
  if (r.client !== o.client || r.adapterVersion !== COMPATIBILITY.adapterVersion ||
      !COMPATIBILITY.capabilityBinding.every(k => typeof r[k] === 'string' && r[k].length > 0) ||
      !Array.isArray(r.supportedFlags) || typeof r.nativeSchemaSupported !== 'boolean' ||
      typeof r.permissionMode !== 'string' || typeof r.extractionMode !== 'string' ||
      typeof r.evidenceSha256 !== 'string' || !r.evidencePath) {
    throw new Error('Invalid capability record binding');
  }
  // Receipts are evidence only. They never grant authority or run probes.
  const adapter = path.join(SOURCE_ROOT,'integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/result_gateway.py');
  const config = r.configPath;
  if (!r.binaryPath || !config || !r.routePath ||
      ![r.binaryPath,config,r.routePath,adapter,r.evidencePath].every(p=>fs.existsSync(p)) ||
      sha(fs.readFileSync(r.binaryPath)) !== r.binarySha256 ||
      sha(fs.readFileSync(config)) !== r.configSha256 ||
      sha(fs.readFileSync(r.routePath)) !== r.routeSha256 ||
      sha(fs.readFileSync(adapter)) !== r.adapterSha256 ||
      sha(fs.readFileSync(r.evidencePath)) !== r.evidenceSha256) {
    return { client:o.client, status:'excluded', reason:'capability binding changed; maintenance validation required' };
  }
  return { ...r, status:'recorded', liveDispatchProven:false };
}

function ensureParent(target, createdParents, createMissing = true) {
  const missing = [];
  let cursor = path.dirname(target);
  while (true) {
    const stats = lstatOrNull(cursor);
    if (stats?.isSymbolicLink()) throw new Error(`Symlink install ancestor: ${cursor}`);
    if (stats && !stats.isDirectory()) throw new Error(`Install ancestor is not a directory: ${cursor}`);
    if (!stats) {
      if (!createMissing) throw new Error(`Install ancestor disappeared: ${cursor}`);
      missing.push(cursor);
    }
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
    cursor = parent;
  }
  for (const directory of missing.reverse()) {
    fs.mkdirSync(directory);
    createdParents.add(directory);
  }
  // A staged sibling must resolve to the same directory as its target.
  const parent = path.dirname(target);
  if (!fs.lstatSync(parent).isDirectory()) throw new Error(`Install parent is not a directory: ${parent}`);
}

function cleanupParents(createdParents) {
  for (const directory of [...createdParents].sort((a, b) => b.length - a.length)) {
    try { fs.rmdirSync(directory); } catch (error) {
      if (!['ENOENT', 'ENOTEMPTY', 'EEXIST'].includes(error.code)) throw error;
    }
  }
}

function backupPath(target,batchId,options) {
  const root=[options.nativeHome,options.skillHome].sort((a,b)=>b.length-a.length).find(r=>target.startsWith(r+path.sep));
  if(!root)throw new Error('Backup target outside install homes');
  return path.join(root,'centurion','backups',batchId,path.relative(root,target));
}
function stageAll(operations, batchId, createdParents, options) {
  for (const operation of operations) {
    ensureParent(operation.target, createdParents);
    const sourceStats = fs.lstatSync(operation.source);
    const existing = lstatOrNull(operation.target);
    if (existing && (existing.isSymbolicLink() || existing.isDirectory() !== sourceStats.isDirectory())) {
      throw new Error(`Unsafe target type: ${operation.target}`);
    }
    operation.before = existing ? inspectTree(operation.target) : null;
    if (operation.before !== operation.preflightBefore) throw new Error('Managed target changed before staging: '+operation.target);
    operation.expected = inspectTree(operation.source, true);
    operation.staged = path.join(path.dirname(operation.target), `.${path.basename(operation.target)}.centurion-stage-${batchId}`);
    operation.backup = existing ? backupPath(operation.target,batchId,options) : null;
    if(operation.backup)ensureParent(operation.backup,createdParents);
    if (lstatOrNull(operation.staged) || (operation.backup && lstatOrNull(operation.backup))) {
      throw new Error(`Install batch path already exists: ${operation.target}`);
    }
    copyExact(operation.source, operation.staged);
    if (inspectTree(operation.staged) !== operation.expected) throw new Error(`Staged hash or mode mismatch: ${operation.target}`);
  }
}

function commitAll(operations, failAfter) {
  const touched = [];
  try {
    for (const operation of operations) {
      if (inspectTree(operation.source, true) !== operation.expected) throw new Error(`Source changed during install: ${operation.source}`);
      ensureParent(operation.target, new Set(), false);
      const current = lstatOrNull(operation.target);
      if ((current ? inspectTree(operation.target) : null) !== operation.before) {
        throw new Error(`Target changed during install: ${operation.target}`);
      }
      touched.push(operation);
      if (operation.backup) {
        fs.renameSync(operation.target, operation.backup);
        operation.backedUp = true;
        if (inspectTree(operation.backup) !== operation.before) throw new Error(`Backup hash or mode mismatch: ${operation.target}`);
      }
      fs.renameSync(operation.staged, operation.target);
      operation.installed = true;
      if (inspectTree(operation.target) !== operation.expected) throw new Error(`Installed hash or mode mismatch: ${operation.target}`);
      if (failAfter && touched.length === failAfter) throw new Error(`Injected install failure after ${failAfter} swaps`);
    }
  } catch (error) {
    const rollbackErrors = [];
    for (const operation of touched.reverse()) {
      try {
        if (operation.installed) fs.rmSync(operation.target, { recursive: true, force: true });
        if (operation.backedUp) fs.renameSync(operation.backup, operation.target);
      } catch (rollbackError) {
        rollbackErrors.push(`${operation.target}: ${rollbackError.message}`);
      }
    }
    if (rollbackErrors.length) throw new Error(`${error.message}; rollback incomplete: ${rollbackErrors.join('; ')}`);
    throw error;
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write('Usage: install-owned-files.mjs --client codex|claude|hermes --profile core|domain|maintenance --skill <slug> [repeat] --agents-home <dir> --codex-home <dir> | --claude-home <dir> | --hermes-home <dir> [--dry-run] [--capability-record <receipt>] [--migration-record <preimages>]\n');
    return;
  }
  const state = ownership(options);
  const adapter = capability(options);
  const listed = listOperations(options);
  let operations = listed.operations;
  const skillCount = listed.skillCount;
  const scratch = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'centurion-package-'));
  try {
  const generated = (name, text, target) => {
    const file = path.join(scratch,name); fs.writeFileSync(file,text); operations.push({ source:file, target });
  };
  if (options.corePointer) {
    const op = operations.find(o=>o.target === path.join(options.nativeHome,'AGENTS.md'));
    operations.splice(operations.indexOf(op),1);
    generated('AGENTS.md',fs.readFileSync(op.source,'utf8').replaceAll('skills/orchestrator/SKILL.md',options.corePointer),op.target);
  }
  if (options.pluginSource) {
    const plugin = path.join(scratch,'plugin');
    copyExact(options.pluginSource,plugin);
    fs.rmSync(path.join(plugin,'skills'),{recursive:true,force:true});
    for (const file of fs.readdirSync(path.join(plugin,'agents'))) {
      if (!options.selected.includes(file.replace(/\.md$/,''))) fs.rmSync(path.join(plugin,'agents',file));
    }
    // No implicit MCP registration or historical guard dispatcher.
    fs.writeFileSync(path.join(plugin,'.mcp.json'),'{"mcpServers":{}}\n');
    fs.rmSync(path.join(plugin,'references'),{recursive:true,force:true});
    fs.rmSync(path.join(plugin,'scripts'),{recursive:true,force:true});
    operations.push({ source:plugin,target:options.pluginTarget });
  }
  // A legacy custom instruction is never overwritten. The explicit migration
  // action appends one managed block and records the untouched original bytes.
  const instructionPath=path.join(options.nativeHome,{codex:'AGENTS.md',claude:'CLAUDE.md',hermes:'SOUL.md'}[options.client]);
  const instruction=operations.find(op=>op.target===instructionPath);
  const priorInstruction=state.prior?.files.find(r=>r.installedPath===instructionPath)?.preservedInstruction;
  const preserve=state.migration?.files.find(r=>r.installedPath===instructionPath && r.action==='preserve-instruction');
  let preservedInstruction=null;
  if (preserve || priorInstruction) {
    const current=fs.readFileSync(instructionPath);
    let prefix=current, suffix=Buffer.alloc(0);
    if (priorInstruction) {
      ({prefix,suffix}=preservedInstructionParts(current,priorInstruction));
    } else if (current.includes(Buffer.from('<!-- CENTURION_MANAGED_V3_'))) throw new Error('Unowned managed instruction marker');
    const text=Buffer.concat([prefix,Buffer.from(INSTRUCTION_START),fs.readFileSync(instruction.source),Buffer.from(INSTRUCTION_END),suffix]);
    if (!text.equals(Buffer.from(text.toString('utf8')))) throw new Error('Custom instruction must be valid UTF-8; original bytes unchanged');
    const file=path.join(scratch,'preserved-instruction.md');fs.writeFileSync(file,text);
    instruction.source=file;
    preservedInstruction={prefixBytes:prefix.length,prefixSha256:sha(prefix),suffixBytes:suffix.length,suffixSha256:sha(suffix)};
  }
  // File swaps leave sibling runtime directories, caches and user data intact.
  const managedRoots=operations.filter(op=>fs.lstatSync(op.source).isDirectory()).map(op=>op.target);
  operations=operations.flatMap(op=>JSON.parse(inspectTree(op.source,true)).filter(e=>e.kind==='file').map(e=>({
    source:e.path==='.'?op.source:path.join(op.source,e.path),target:e.path==='.'?op.target:path.join(op.target,e.path)
  })));
  // Full per-file source/installed receipt, including every instruction and packaged runtime.
  const files = [];
  for (const op of operations) {
    const entries = JSON.parse(inspectTree(op.source,true)).filter(e=>e.kind==='file');
    for (const e of entries) {
      const sourcePath = e.path === '.' ? op.source : path.join(op.source,e.path);
      const installedPath = e.path === '.' ? op.target : path.join(op.target,e.path);
      files.push({ sourcePath, installedPath, sourceSha256:e.sha256, installedSha256:e.sha256,
        loadedInstruction:(/\/(?:SKILL|CLAUDE|AGENTS|SOUL|PROBATIO)\.md$/.test(installedPath) || /\/(?:agents|output-styles|overrides|skill-bundles)\/[^/]+\.(?:md|yaml)$/.test(installedPath)), generated:sourcePath.startsWith(scratch+path.sep),
        installedMode:e.mode,
        ...(installedPath===instructionPath && preservedInstruction ? {preservedInstruction} : {}),
        ...(sourcePath.startsWith(scratch+path.sep) ? { renderedContent:fs.readFileSync(sourcePath,'utf8') } : {}) });
    }
  }
  const receipt = { manifestVersion:'CENTURION_INSTALLED_CHAIN_V1', productVersion:PRODUCT_VERSION,
    client:options.client, profile:options.profile, selected:options.selected, compatibility:COMPATIBILITY,
    capability:adapter, files, managedRoots, ownershipScope:'explicit-package-files', sourceRoot:SOURCE_ROOT,
    sourceInputs:[...new Set([path.join(SOURCE_ROOT,'CLAUDE.md'),path.join(SOURCE_ROOT,'PROBATIO.md'),
      path.join(SOURCE_ROOT,'scripts/install-owned-files.mjs'),
      path.join(SOURCE_ROOT,'integrations/codex-legion-kit/scripts/lib/surface-config.mjs'),
      ...(options.projectedSources || []),
      ...(options.pluginSource?walkFiles(options.pluginSource):[])])]
      .map(sourcePath=>({sourcePath,sha256:sha(fs.readFileSync(sourcePath))})),
    nativeInstructionEntrypoint:path.join(options.nativeHome,options.client==='hermes'?'SOUL.md':options.client==='claude'?'CLAUDE.md':'AGENTS.md'),
    liveLoadedChainProven:false };
  generated('installed-chain.json',JSON.stringify(receipt,null,2)+'\n',path.join(options.nativeHome,'centurion/installed-chain.json'));
  conflictInventory(state,operations);
  const batchId = crypto.randomUUID();
  const createdParents = new Set();
  const injected = process.env.CENTURION_INSTALL_TEST_FAIL_AFTER;
  const failAfter = injected ? Number(injected) : 0;
  if (injected && (!Number.isSafeInteger(failAfter) || failAfter < 1)) throw new Error('Invalid test failure point');
  // Remove only hash-verified prior owned files that no longer belong to the selection.
  const retained = new Set(files.map(r=>r.installedPath));
  const retired = state.rows.filter(r=>r.action==='retire' || !retained.has(r.installedPath));
  if (retired.some(r=>retained.has(r.installedPath))) throw new Error('Cannot retire a selected package target');
  if (options.dryRun) {
    process.stdout.write(JSON.stringify({ dryRun:true, selected:options.selected, adapter, ownershipScope:'explicit-package-files',targets:operations.map(o=>o.target),retired:retired.map(r=>r.installedPath),preservedInstruction:!!preservedInstruction })+'\n'); return;
  }
  const retiredBackups = [];
  let committed = false;
  try {
    stageAll(operations,batchId,createdParents,options);
    for (const r of retired) {
      rejectInstallSymlinks(r.installedPath);
      if (inspectTree(r.installedPath)!==state.preimages.get(r.installedPath)) throw new Error('Retired preimage changed: '+r.installedPath);
      const backup = backupPath(r.installedPath,batchId,options);
      ensureParent(backup,createdParents);
      if(lstatOrNull(backup))throw new Error('Backup already exists: '+backup);
      fs.renameSync(r.installedPath,backup); retiredBackups.push([r.installedPath,backup]);
    }
    commitAll(operations,failAfter);
    committed = true;
  } finally {
    for (const op of operations) if (op.staged) fs.rmSync(op.staged,{recursive:true,force:true});
    if (!committed) {
      for (const [target,backup] of retiredBackups.reverse()) fs.renameSync(backup,target);
      cleanupParents(createdParents);
    }
  }
  process.stdout.write(JSON.stringify({ productVersion:PRODUCT_VERSION, selected:options.selected, skillCount,
    targetCount:operations.length, backupCount:operations.filter(o=>o.backup).length, backupBatchId:batchId,
    manifestPath:path.join(options.nativeHome,'centurion/installed-chain.json'), capability:adapter })+'\n');
  } finally { fs.rmSync(scratch,{recursive:true,force:true}); }
}

if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) try { main(); } catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
