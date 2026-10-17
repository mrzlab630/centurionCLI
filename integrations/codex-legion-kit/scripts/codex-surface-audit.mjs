#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { auditSurface,sha256,instructionViolations } from '../../../skills/context-optimizer/scripts/skill-surface-audit.mjs';
import { PRODUCT_VERSION,REPO_ROOT } from './lib/surface-config.mjs';
import { managedFileCatalogue,validateManagedRows,rejectInstallSymlinks,isManagedInstructionOrControl,preservedInstructionParts } from '../../../scripts/install-owned-files.mjs';
export function stripTomlComment(rawLine) {
  let quote = null;
  let escaped = false;
  for (let index = 0; index < rawLine.length; index += 1) {
    const char = rawLine[index];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (quote === '"') {
      if (char === '\\') escaped = true;
      else if (char === '"') quote = null;
      continue;
    }
    if (quote === "'") {
      if (char === "'") quote = null;
      continue;
    }
    if (char === '"' || char === "'") {
      quote = char;
      continue;
    }
    if (char === '#') return rawLine.slice(0, index);
  }
  return rawLine;
}

export function parseTomlLite(text) {
  const root = {};
  let current = root;
  for (const rawLine of text.split('\n')) {
    const line = stripTomlComment(rawLine).trim();
    if (!line) continue;
    const section = line.match(/^\[([^\]]+)\]$/);
    if (section) {
      current = root;
      for (const part of section[1].split('.')) {
        const key = part.replace(/^['"]|['"]$/g, '');
        current[key] ||= {};
        current = current[key];
      }
      continue;
    }
    const pair = line.match(/^([A-Za-z0-9_.-]+)\s*=\s*(.+)$/);
    if (!pair) continue;
    current[pair[1]] = parseTomlValue(pair[2]);
  }
  return root;
}

function parseTomlValue(value) {
  const trimmed = value.trim();
  if (trimmed === 'true') return true;
  if (trimmed === 'false') return false;
  if (/^['"].*['"]$/.test(trimmed)) return trimmed.slice(1, -1);
  if (/^\[.*\]$/.test(trimmed)) {
    return trimmed.slice(1, -1).split(',').map((item) => parseTomlValue(item)).filter((item) => item !== '');
  }
  if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) return Number(trimmed);
  return trimmed;
}

export function auditClient(client,argv) {
 const options={repoOnly:false};
 for(let i=0;i<argv.length;i++) {
  const a=argv[i]; if(a==='--repo-only')options.repoOnly=true;
  else if(a==='--json' || a==='--no-codex-features')continue;
  else if(['--codex-home','--claude-home','--hermes-home','--agents-home'].includes(a) && argv[i+1]) options[a.slice(2)]=path.resolve(argv[++i]);
  else throw new Error(`Unknown/missing audit argument: ${a}`);
 }
 const home=options[`${client}-home`];
 if(!options.repoOnly && (!home || (client==='codex' && !options['agents-home'])))throw new Error('Explicit client and skill homes required, or --repo-only');
 // Client homes contain credentials, configuration and runtime state. Audit
 // repository rules and explicit receipt files, never recursively scan a home.
 const surface=auditSurface({consumerRoots:[]});
 const failures=[...surface.violations,...surface.brokenReferences,...surface.bundleErrors];
 let installed=null;
 if(!options.repoOnly) {
  const manifest=path.join(home,'centurion/installed-chain.json');
  rejectInstallSymlinks(manifest);
  if(!fs.existsSync(manifest))failures.push({reason:'missing installed-chain manifest'});
  else {
   installed=JSON.parse(fs.readFileSync(manifest,'utf8'));
   if(installed.manifestVersion!=='CENTURION_INSTALLED_CHAIN_V1' || installed.productVersion!==PRODUCT_VERSION || installed.client!==client)failures.push({reason:'installed identity/version mismatch'});
   const catalogue=managedFileCatalogue({client,nativeHome:home,skillHome:client==='codex'?options['agents-home']:home});
   validateManagedRows(installed.files,catalogue);
   const allowed=new Set([manifest,...installed.files.map(r=>r.installedPath)]);
   for(const file of catalogue) if(isManagedInstructionOrControl(file) && !allowed.has(file)) {
    rejectInstallSymlinks(file);
    if(fs.existsSync(file))failures.push({file,reason:'foreign managed instruction/control path'});
   }
   const sourceInRepo=file=>typeof file==='string' && path.resolve(file)===file && file.startsWith(REPO_ROOT+path.sep);
   for(const r of installed.sourceInputs || []) {
    if(!sourceInRepo(r.sourcePath)) {failures.push({reason:'source input outside package root'});continue;}
    rejectInstallSymlinks(r.sourcePath);
    if(!fs.existsSync(r.sourcePath) || sha256(fs.readFileSync(r.sourcePath))!==r.sha256)failures.push({file:r.sourcePath,reason:'source input hash changed'});
   }
   for(const r of installed.files) {
    rejectInstallSymlinks(r.installedPath);
    if(r.generated && sha256(r.renderedContent || '')!==r.sourceSha256)failures.push({file:r.installedPath,reason:'rendered source hash mismatch'});
    if(!fs.existsSync(r.installedPath)) {failures.push({file:r.installedPath,reason:'installed file missing'});continue;}
    const stats=fs.lstatSync(r.installedPath);
    if(!stats.isFile()) {failures.push({file:r.installedPath,reason:'installed target is not a regular file'});continue;}
    const bytes=fs.readFileSync(r.installedPath);
    if(sha256(bytes)!==r.installedSha256) failures.push({file:r.installedPath,reason:'installed hash mismatch'});
    if(r.installedMode!==undefined && (stats.mode&0o777)!==r.installedMode)failures.push({file:r.installedPath,reason:'installed mode mismatch'});
    if(!r.generated) {
     if(!sourceInRepo(r.sourcePath)) failures.push({reason:'source file outside package root'});
     else {rejectInstallSymlinks(r.sourcePath);if(!fs.existsSync(r.sourcePath) || sha256(fs.readFileSync(r.sourcePath))!==r.sourceSha256)failures.push({file:r.sourcePath,reason:'source hash mismatch'});}
    }
    if(r.loadedInstruction) {
     let managed=bytes;
     if(r.preservedInstruction) {
      try {managed=preservedInstructionParts(bytes,r.preservedInstruction).managed;}
      catch(error) {failures.push({file:r.installedPath,reason:error.message});continue;}
     }
     for(const hit of instructionViolations(managed.toString('utf8')))failures.push({file:r.installedPath,...hit});
     for(const match of managed.toString('utf8').replace(/```[\s\S]*?```/g,'').matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      const ref=match[1].split('#')[0];
      if(ref && !/^(?:https?:|app:)/.test(ref) && !ref.includes('<') && !fs.existsSync(path.resolve(path.dirname(r.installedPath),ref)))failures.push({file:r.installedPath,reference:ref,reason:'broken managed instruction link'});
     }
    }
   }
  }
 }
 return {ok:failures.length===0,productVersion:PRODUCT_VERSION,failures,auditScope:'explicit-package-files',liveLoadedChainProven:false,
   preservedInstructionPolicy:installed?.files.some(r=>r.preservedInstruction)?'custom bytes preserved; policy not evaluated':'none',
   repo:{canonicalSkillCount:surface.records.filter(r=>r.file.startsWith(path.join(REPO_ROOT,'skills')+path.sep)).length},
   surface:{skillCount:surface.skillCount,duplicateNameCount:surface.duplicateNameCount},installed};
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try { const r=auditClient('codex',process.argv.slice(2)); console.log(JSON.stringify(r,null,2)); if(!r.ok)process.exitCode=1; }
 catch(e){console.error(e.message);process.exitCode=1;}
}
