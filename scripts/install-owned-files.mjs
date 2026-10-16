#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { selectSkills, LOAD_MAP, INTEGRATION_MAP, BUNDLE_MAP, COMPATIBILITY, PRODUCT_VERSION, isIgnoredGeneratedDir, walkFiles } from '../integrations/codex-legion-kit/scripts/lib/surface-config.mjs';

let verifiedOwned = new Map();

const SOURCE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function parseArgs(args) {
  const o = { skills: [], dryRun: false };
  const values = { '--agents-home':'agentsHome', '--claude-home':'claudeHome',
    '--codex-home':'codexHome', '--hermes-home':'hermesHome', '--profile':'profile',
    '--client':'client', '--capability-record':'capabilityRecord' };
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
  if (!o[key] || (o.client === 'codex' && !o.codexHome)) throw new Error('Explicit isolated target homes required');
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
function listOperations(options) {
  const operations = [];
  const add = (source, target) => operations.push({ source, target });
  const home = options.nativeHome;
  const skillsTarget = path.join(options.skillHome, 'skills');
  for (const name of options.selected) {
    if (!Object.values(LOAD_MAP).flat().includes(name)) continue;
    const sourceDir = path.join(SOURCE_ROOT, 'skills', name);
    const targetDir = options.client === 'hermes' && name === 'open-design-producer'
      ? path.join(skillsTarget, 'autonomous-ai-agents', name) : path.join(skillsTarget, name);
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
  if (options.selected.includes('open-design-producer')) {
    options.openDesignConfig = path.join(home,'centurion','open-design-bridge.json');
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

function conflictInventory(o) {
  for(const root of [o.nativeHome,o.skillHome]) {
    let cursor=root;
    while(true){
      if(lstatOrNull(cursor)?.isSymbolicLink())throw new Error('Symlink install ancestor: '+cursor);
      const parent=path.dirname(cursor);if(parent===cursor)break;cursor=parent;
    }
  }
  const priorPath = path.join(o.nativeHome, 'centurion', 'installed-chain.json');
  const prior = fs.existsSync(priorPath) ? JSON.parse(fs.readFileSync(priorPath,'utf8')) : null;
  const scopeRoots = [o.nativeHome,o.skillHome].map(p=>p+path.sep);
  if(prior && (!Array.isArray(prior.files) || prior.files.some(r=>typeof r.installedPath!=='string' || !scopeRoots.some(p=>path.resolve(r.installedPath).startsWith(p)) || !/^[a-f0-9]{64}$/.test(r.installedSha256)))) throw new Error('Invalid prior manifest paths/hashes');
  const owned = new Map((prior?.files || []).map(r => [r.installedPath,r.installedSha256]));
  verifiedOwned = owned;
  const conflicts = [];
  const roots = [o.nativeHome, ...(o.skillHome !== o.nativeHome ? [o.skillHome] : [])];
  for (const root of roots) {
    for (const file of walkFiles(root)) {
      const rel = path.relative(root,file);
      if (rel === 'centurion/installed-chain.json') continue;
      const expected = owned.get(file);
      if (!expected || sha(fs.readFileSync(file)) !== expected) conflicts.push(rel);
    }
  }
  if (conflicts.length) throw new Error(`Foreign/global surface conflict (unchanged): ${conflicts.slice(0,12).join(', ')}`);
  return prior;
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

function rejectForeignEntries(source, target) {
  const sourcePaths = new Set(JSON.parse(inspectTree(source, true)).map((entry) => entry.path));
  for (const entry of JSON.parse(inspectTree(target))) {
    if (entry.path === '.') continue;
    if (entry.path.split(path.sep).some(isGenerated)) {
      throw new Error(`Foreign/generated surface conflict (unchanged): ${path.join(target,entry.path)}`);
    }
    if (!sourcePaths.has(entry.path) && !(entry.kind === 'directory' || (verifiedOwned.get(path.join(target,entry.path)) === entry.sha256))) throw new Error(`Unmanaged file in managed directory: ${path.join(target, entry.path)}`);
  }
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
    if (existing?.isDirectory()) rejectForeignEntries(operation.source, operation.target);
    operation.before = existing ? inspectTree(operation.target) : null;
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
      if (current?.isDirectory()) rejectForeignEntries(operation.source, operation.target);
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
    process.stdout.write('Usage: install-owned-files.mjs --client codex|claude|hermes --profile core|domain|maintenance --skill <slug> [repeat] --agents-home <dir> --codex-home <dir> | --claude-home <dir> | --hermes-home <dir> [--dry-run] [--capability-record <receipt>]\n');
    return;
  }
  const prior = conflictInventory(options);
  const adapter = capability(options);
  const { operations, skillCount } = listOperations(options);
  if (options.dryRun) {
    process.stdout.write(JSON.stringify({ dryRun:true, selected:options.selected, adapter, targets:operations.map(o=>o.target) })+'\n'); return;
  }
  const scratch = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'centurion-package-'));
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
  if(options.client==='hermes' && options.selected.includes('open-design-producer')) {
    const op=operations.find(o=>o.target.endsWith('/autonomous-ai-agents/open-design-producer'));
    const projected=path.join(scratch,'open-design-producer');
    copyExact(op.source,projected);
    const entry=path.join(projected,'SKILL.md');
    fs.writeFileSync(entry,fs.readFileSync(entry,'utf8').replace('../orchestrator/SKILL.md','../../orchestrator/SKILL.md'));
    options.projectedSources=[...walkFiles(op.source)];
    op.source=projected;
  }
  if (options.openDesignConfig) generated('open-design.json',JSON.stringify({configVersion:'CENTURION_OPEN_DESIGN_CONFIG_V1',bridgeRoot:path.join(SOURCE_ROOT,'integrations/open-design-bridge')})+'\n',options.openDesignConfig);
  // Full per-file source/installed receipt, including every instruction and packaged runtime.
  const files = [];
  for (const op of operations) {
    const entries = JSON.parse(inspectTree(op.source,true)).filter(e=>e.kind==='file');
    for (const e of entries) {
      const sourcePath = e.path === '.' ? op.source : path.join(op.source,e.path);
      const installedPath = e.path === '.' ? op.target : path.join(op.target,e.path);
      files.push({ sourcePath, installedPath, sourceSha256:e.sha256, installedSha256:e.sha256,
        loadedInstruction:(/\/(?:SKILL|CLAUDE|AGENTS|SOUL|PROBATIO)\.md$/.test(sourcePath) || /\/(?:agents|output-styles|overrides|skill-bundles)\/[^/]+\.(?:md|yaml)$/.test(sourcePath)), generated:sourcePath.startsWith(scratch+path.sep),
        ...(sourcePath.startsWith(scratch+path.sep) ? { renderedContent:fs.readFileSync(sourcePath,'utf8') } : {}) });
    }
  }
  const receipt = { manifestVersion:'CENTURION_INSTALLED_CHAIN_V1', productVersion:PRODUCT_VERSION,
    client:options.client, profile:options.profile, selected:options.selected, compatibility:COMPATIBILITY,
    capability:adapter, files, sourceRoot:SOURCE_ROOT,
    sourceInputs:[...new Set([path.join(SOURCE_ROOT,'CLAUDE.md'),path.join(SOURCE_ROOT,'PROBATIO.md'),
      path.join(SOURCE_ROOT,'scripts/install-owned-files.mjs'),
      path.join(SOURCE_ROOT,'integrations/codex-legion-kit/scripts/lib/surface-config.mjs'),
      ...(options.projectedSources || []),
      ...(options.pluginSource?walkFiles(options.pluginSource):[])])]
      .map(sourcePath=>({sourcePath,sha256:sha(fs.readFileSync(sourcePath))})),
    nativeInstructionEntrypoint:path.join(options.nativeHome,options.client==='hermes'?'SOUL.md':options.client==='claude'?'CLAUDE.md':'AGENTS.md'),
    liveLoadedChainProven:false };
  generated('installed-chain.json',JSON.stringify(receipt,null,2)+'\n',path.join(options.nativeHome,'centurion/installed-chain.json'));
  const batchId = crypto.randomUUID();
  const createdParents = new Set();
  const injected = process.env.CENTURION_INSTALL_TEST_FAIL_AFTER;
  const failAfter = injected ? Number(injected) : 0;
  if (injected && (!Number.isSafeInteger(failAfter) || failAfter < 1)) throw new Error('Invalid test failure point');
  // Remove only hash-verified prior owned files that no longer belong to the selection.
  const retained = new Set(files.map(r=>r.installedPath));
  const retired = (prior?.files || []).filter(r=>!retained.has(r.installedPath) && !operations.some(op=>r.installedPath.startsWith(op.target+path.sep)));
  const retiredBackups = [];
  let committed = false;
  try {
    stageAll(operations,batchId,createdParents,options);
    for (const r of retired) {
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
    fs.rmSync(scratch,{recursive:true,force:true});
  }
  process.stdout.write(JSON.stringify({ productVersion:PRODUCT_VERSION, selected:options.selected, skillCount,
    targetCount:operations.length, backupCount:operations.filter(o=>o.backup).length, backupBatchId:batchId,
    manifestPath:path.join(options.nativeHome,'centurion/installed-chain.json'), capability:adapter })+'\n');
}

try { main(); } catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
