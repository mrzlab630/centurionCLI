#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { REFERENCE_RESULT_VERSION, searchDesignReferences } from '../lib/references.mjs';

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--request') options.request = argv[++index];
    else if (token === '--result') options.result = argv[++index];
    else if (token === '--pretty') options.pretty = true;
    else if (token === '--help' || token === '-h') options.help = true;
    else throw new Error(`unknown argument: ${token}`);
  }
  return options;
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}

async function readRequest(source) {
  if (!source) throw new Error('--request is required');
  return JSON.parse(source === '-' ? await readStdin() : fs.readFileSync(path.resolve(source), 'utf8'));
}

function writeResult(result, options) {
  const json = `${JSON.stringify(result, null, options.pretty ? 2 : 0)}\n`;
  if (options.result) {
    const resultPath = path.resolve(options.result);
    fs.mkdirSync(path.dirname(resultPath), { recursive: true });
    fs.writeFileSync(resultPath, json);
  }
  process.stdout.write(json);
}

const options = parseArgs(process.argv.slice(2));
if (options.help) {
  process.stdout.write('Usage: centurion-reference --request <file|-> [--result <file>] [--pretty]\n');
} else {
  try {
    const result = await searchDesignReferences(await readRequest(options.request), { cwd: process.cwd(), env: process.env });
    writeResult(result, options);
    if (result.status !== 'done') process.exitCode = 1;
  } catch (error) {
    writeResult({
      resultVersion: REFERENCE_RESULT_VERSION,
      searchId: null,
      status: 'failed',
      query: null,
      manifestPath: null,
      manifestSha256: null,
      references: [],
      sources: [],
      cleanup: null,
      warnings: [],
      errors: [error.message]
    }, options);
    process.exitCode = 1;
  }
}
