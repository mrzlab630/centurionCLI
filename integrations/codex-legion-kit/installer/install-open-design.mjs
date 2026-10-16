#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const result=spawnSync(process.execPath,[fileURLToPath(new URL('../../../scripts/install-owned-files.mjs',import.meta.url)),
 '--client','codex','--profile','domain','--skill','open-design-producer',...process.argv.slice(2)],{stdio:'inherit',env:process.env});
process.exitCode=result.status??1;
