#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const args=process.argv.slice(2);const write=args.includes('--write');
const result=spawnSync(process.execPath,[fileURLToPath(new URL('../../../scripts/install-owned-files.mjs',import.meta.url)),
 '--client','codex',...args.filter(a=>a!=='--write' && a!=='--json'),...(write?[]:['--dry-run'])],{stdio:'inherit',env:process.env});
process.exitCode=result.status??1;
