#!/usr/bin/env node
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const hermesHome = path.resolve(process.env.HERMES_HOME || path.join(os.homedir(), '.hermes'));
const agentsHome = path.resolve(process.env.AGENTS_HOME || path.join(os.homedir(), '.agents'));
const apply = process.argv.includes('--apply');
const unknown = process.argv.slice(2).filter((arg) => arg !== '--apply');
if (unknown.length) throw new Error(`Unknown argument(s): ${unknown.join(', ')}`);

const result = spawnSync('python3', [
  path.join(repoRoot, 'scripts', 'deploy_centurion_roots.py'),
  '--repo', repoRoot,
  '--hermes-home', hermesHome,
  '--agents-home', agentsHome,
  ...(apply ? ['--apply'] : [])
], { encoding: 'utf8' });
if (result.error) throw result.error;
process.stdout.write(result.stdout);
process.stderr.write(result.stderr);
process.exitCode = result.status ?? 1;
