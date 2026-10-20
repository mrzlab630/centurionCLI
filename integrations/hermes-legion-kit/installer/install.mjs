#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const installer = fileURLToPath(new URL('../../../scripts/install-owned-files.mjs',import.meta.url));
const result = spawnSync(process.execPath,[installer,'--client','hermes',...process.argv.slice(2)],{ stdio:'inherit',env:process.env });
process.exitCode = result.status ?? 1;
