#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { runDesignRequest } from '../lib/bridge.mjs';
import { readJsonInput } from '../lib/json-input.mjs';

class ResultWriteError extends Error {}

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

function usage() {
  return `Usage:
  centurion-design --request <file|-> [--result <file>] [--pretty]

Environment:
  CENTURION_OD_COMMAND_JSON  JSON argv array for Open Design, for example
                            ["node","/path/to/open-design/apps/daemon/bin/od.mjs"]
  CENTURION_OD_ROOT          Open Design checkout with a built daemon CLI
  CENTURION_BROWSER_BIN      Chrome/Chromium executable for screenshots
  CENTURION_DESIGN_ROOT      Allowed root for outputs and previous results
`;
}

function writeResult(result, options) {
  const json = `${JSON.stringify(result, null, options.pretty ? 2 : 0)}\n`;
  if (options.result) {
    const resultPath = path.resolve(options.result);
    try {
      fs.mkdirSync(path.dirname(resultPath), { recursive: true });
      fs.writeFileSync(resultPath, json);
    } catch (error) {
      throw new ResultWriteError(`failed to write --result ${resultPath}: ${error.message}`);
    }
  }
  process.stdout.write(json);
}

let options = {};
let completedResult = null;
try {
  options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
  } else {
    const request = await readJsonInput(options.request, { label: 'Open Design request' });
    completedResult = await runDesignRequest(request, {
      cwd: process.cwd(),
      env: process.env,
      resultPath: options.result ? path.resolve(options.result) : null
    });
    writeResult(completedResult, options);
    if (completedResult.status !== 'done') process.exitCode = 1;
  }
} catch (error) {
  const resultWriteFailed = error instanceof ResultWriteError;
  const result = completedResult
    ? {
        ...completedResult,
        status: 'failed',
        warnings: [
          ...completedResult.warnings,
          ...(resultWriteFailed ? ['result file was not written; use the stdout payload'] : [])
        ],
        errors: [...completedResult.errors, error.message]
      }
    : {
        resultVersion: 'CENTURION_OD_RESULT_V1',
        requestId: null,
        status: 'failed',
        action: null,
        projectId: null,
        conversationId: null,
        runId: null,
        artifact: null,
        screenshot: null,
        proof: [],
        warnings: [],
        errors: [error.message]
      };
  try {
    writeResult(result, resultWriteFailed ? { ...options, result: null } : options);
  } catch (writeError) {
    writeResult({
      ...result,
      warnings: [...result.warnings, 'result file was not written; use the stdout payload'],
      errors: [...result.errors, writeError.message]
    }, { ...options, result: null });
  }
  process.exitCode = 1;
}
