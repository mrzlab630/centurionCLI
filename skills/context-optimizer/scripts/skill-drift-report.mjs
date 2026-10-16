#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { auditSurface, sha256 } from './skill-surface-audit.mjs';
const roots=[];
for(let i=2;i<process.argv.length;i++) {
  if(process.argv[i]==='--consumer-root' && process.argv[i+1]) roots.push(path.resolve(process.argv[++i]));
  else throw new Error('Use --consumer-root <isolated root>');
}
const audit=auditSurface({consumerRoots:roots});
const drifted=[];
for (const root of roots) {
  const file=path.join(root,'centurion/installed-chain.json');
  if(!fs.existsSync(file)) {drifted.push({root,reason:'missing installed-chain receipt'});continue;}
  const receipt=JSON.parse(fs.readFileSync(file,'utf8'));
  for(const r of receipt.files) {
    if(!fs.existsSync(r.installedPath) || sha256(fs.readFileSync(r.installedPath))!==r.installedSha256) drifted.push({file:r.installedPath,reason:'installed hash mismatch'});
    if(!r.generated && (!fs.existsSync(r.sourcePath) || sha256(fs.readFileSync(r.sourcePath))!==r.sourceSha256)) drifted.push({file:r.sourcePath,reason:'source hash changed'});
  }
}
console.log(JSON.stringify({driftedCount:drifted.length,drifted,scannedRoots:audit.scannedRoots},null,2));
if(drifted.length)process.exitCode=1;
