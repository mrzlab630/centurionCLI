import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const mockOd = path.join(here, 'fixtures', 'mock-od.mjs');

function run(command, args, options = {}) {
  return spawnSync(command, args, { cwd: repoRoot, encoding: 'utf8', ...options });
}

function installClients(root) {
  const homes = {
    hermes: path.join(root, 'hermes-home'),
    claude: path.join(root, 'claude-home'),
    codex: path.join(root, 'codex-home'),
    agents: path.join(root, 'agents-home')
  };
  const commands = [
    ['Hermes', path.join(repoRoot, 'integrations', 'hermes-legion-kit', 'installer', 'install.mjs'), ['--hermes-home', homes.hermes]],
    ['Claude', path.join(repoRoot, 'integrations', 'claude-legion-kit', 'installer', 'install.mjs'), ['--claude-home', homes.claude]],
    ['Codex', path.join(repoRoot, 'integrations', 'codex-legion-kit', 'installer', 'install-open-design.mjs'), ['--agents-home', homes.agents, '--codex-home', homes.codex]]
  ];
  for (const [label, installer, args] of commands) {
    const installed = run(process.execPath, [installer, ...args]);
    assert.equal(installed.status, 0, `${label} installer failed: ${installed.stderr || installed.stdout}`);
  }
  return {
    homes,
    launchers: {
      hermes: path.join(homes.hermes, 'skills', 'autonomous-ai-agents', 'open-design-producer', 'scripts', 'open-design.mjs'),
      claude: path.join(homes.claude, 'skills', 'open-design-producer', 'scripts', 'open-design.mjs'),
      codex: path.join(homes.agents, 'skills', 'open-design-producer', 'scripts', 'open-design.mjs')
    }
  };
}

function invokeClient(client, launcher, request, resultPath, env) {
  const requestPath = path.join(path.dirname(resultPath), `${client}-request.json`);
  fs.mkdirSync(path.dirname(resultPath), { recursive: true });
  fs.writeFileSync(requestPath, `${JSON.stringify(request, null, 2)}\n`);
  const invocation = run(process.execPath, [launcher, '--request', requestPath, '--result', resultPath, '--pretty'], { env });
  assert.equal(invocation.status, 0, `${client} launcher failed: ${invocation.stderr || invocation.stdout}`);
  return JSON.parse(fs.readFileSync(resultPath, 'utf8'));
}

test('installed Hermes create continues through installed Claude and Codex launchers', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-cross-client-'));
  try {
    const { homes, launchers } = installClients(root);
    for (const launcher of Object.values(launchers)) assert(fs.existsSync(launcher), `installed launcher missing: ${launcher}`);
    const receipts = path.join(root, 'design', '.results');
    const env = {
      ...process.env,
      HOME: root,
      HERMES_HOME: homes.hermes,
      CLAUDE_HOME: homes.claude,
      CODEX_HOME: homes.codex,
      MOCK_OD_STATE_DIR: path.join(root, 'state'),
      CENTURION_DESIGN_ROOT: path.join(root, 'design'),
      CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
    };

    const hermesResultPath = path.join(receipts, 'hermes-create.json');
    const hermes = invokeClient('hermes', launchers.hermes, {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'hermes-create',
      action: 'create',
      brief: 'Create a mock landing.',
      orchestrator: { client: 'hermes', owner: 'AEDILIS' },
      artifact: { outputDir: path.join(root, 'design', 'hermes-create') },
      screenshot: { enabled: false }
    }, hermesResultPath, env);

    const claudeResultPath = path.join(receipts, 'claude-revise.json');
    const claude = invokeClient('claude', launchers.claude, {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'claude-revise',
      action: 'revise',
      brief: 'Improve the hero for Claude.',
      orchestrator: { client: 'claude', owner: 'PICTOR' },
      project: { previousResultPath: hermesResultPath },
      artifact: { outputDir: path.join(root, 'design', 'claude-revise') },
      screenshot: { enabled: false }
    }, claudeResultPath, env);

    const codexResultPath = path.join(receipts, 'codex-revise.json');
    const codex = invokeClient('codex', launchers.codex, {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'codex-revise',
      action: 'revise',
      brief: 'Improve the hero for Codex.',
      orchestrator: { client: 'codex', owner: 'PICTOR' },
      project: { previousResultPath: claudeResultPath },
      artifact: { outputDir: path.join(root, 'design', 'codex-revise') },
      screenshot: { enabled: false }
    }, codexResultPath, env);

    assert.deepEqual([hermes.status, claude.status, codex.status], ['done', 'done', 'done']);
    assert.equal(hermes.projectId, claude.projectId);
    assert.equal(claude.projectId, codex.projectId);
    assert.equal(claude.revisionOf, hermesResultPath);
    assert.equal(codex.revisionOf, claudeResultPath);
    assert.deepEqual([hermes.orchestrator.client, claude.orchestrator.client, codex.orchestrator.client], ['hermes', 'claude', 'codex']);
    assert(codex.proof.some((entry) => entry.check === 'revision-changed' && entry.result === 'passed'));
    assert.equal(hermesResultPath.startsWith(`${hermes.artifact.outputDir}${path.sep}`), false);
    assert.equal(claudeResultPath.startsWith(`${claude.artifact.outputDir}${path.sep}`), false);
    assert.equal(codexResultPath.startsWith(`${codex.artifact.outputDir}${path.sep}`), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
