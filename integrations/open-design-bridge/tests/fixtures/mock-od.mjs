#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const daemonIndex = args.indexOf('--daemon-url');
if (daemonIndex >= 0) args.splice(daemonIndex, 2);
const stateDir = process.env.MOCK_OD_STATE_DIR;
const projectId = 'mock-project-1';
const conversationId = 'mock-conversation-1';
const runId = 'mock-run-1';
const baseHtml = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mock Landing</title>
  <style>
    :root { color-scheme: light; font-family: system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #fff8d7; color: #1d1836; }
    main { min-height: 100vh; display: grid; place-items: center; padding: 48px; }
    section { width: min(900px, 100%); border: 2px solid currentColor; padding: 64px; background: white; }
    h1 { max-width: 12ch; margin: 0 0 24px; font-size: 64px; line-height: 1; }
    p { max-width: 55ch; font-size: 18px; line-height: 1.6; }
    button { min-height: 48px; padding: 0 24px; border: 0; background: #ff6b00; color: white; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <section>
      <p>CALM PRODUCTIVITY FOR TODAY</p>
      <h1>Mock landing page</h1>
      <p>A deterministic fixture that is large enough to exercise materialization, HTML validation, and browser rendering without calling a provider.</p>
      <button id="cta" type="button">Start now</button>
    </section>
  </main>
  <script>document.querySelector('#cta').addEventListener('click', () => document.body.dataset.clicked = 'true');</script>
</body>
</html>`;
function currentHtml() {
  const revisionFile = path.join(stateDir, 'revision-count');
  const revision = fs.existsSync(revisionFile) ? Number(fs.readFileSync(revisionFile, 'utf8')) : 0;
  return revision > 0
    ? baseHtml.replace('Mock landing page', `Improved mock landing page revision ${revision}`)
    : baseHtml;
}

function json(value) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

if (args[0] === 'status') json({ status: 'running' });
else if (args[0] === 'project' && args[1] === 'create') json({ project: { id: projectId }, conversationId });
else if (args[0] === 'project' && args[1] === 'delete') {
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, 'project-deleted'), args[2] ?? 'unknown');
  process.stdout.write(`[project] deleted ${args[2]}\n`);
}
else if (args[0] === 'run' && args[1] === 'start') {
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, 'started.json'), JSON.stringify({ args }));
  if (args.join(' ').includes('Improve the hero')) {
    const revisionFile = path.join(stateDir, 'revision-count');
    const revision = fs.existsSync(revisionFile) ? Number(fs.readFileSync(revisionFile, 'utf8')) : 0;
    fs.writeFileSync(revisionFile, String(revision + 1));
  }
  json({ runId, conversationId });
} else if (args[0] === 'run' && args[1] === 'watch') {
  const delayMs = Number(process.env.MOCK_OD_WATCH_DELAY_MS ?? 0);
  if (Number.isFinite(delayMs) && delayMs > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
  process.stdout.write(`${JSON.stringify({ event: 'start', data: { runId } })}\n`);
  process.stdout.write(`${JSON.stringify({ event: 'end', data: { status: 'completed', artifactCount: 1 } })}\n`);
} else if (args[0] === 'run' && args[1] === 'info') {
  json({ id: runId, status: 'completed', exitCode: 0 });
} else if (args[0] === 'files' && args[1] === 'list') {
  const html = currentHtml();
  const filePath = process.env.MOCK_OD_UNSAFE_PATH === '1'
    ? '../outside.html'
    : process.env.MOCK_OD_MATERIALIZE_SYMLINK_PARENT === '1'
      ? 'assets/index.html'
      : 'index.html';
  if (process.env.MOCK_OD_MATERIALIZE_SYMLINK_PARENT === '1') {
    const stagingRoot = path.resolve(stateDir, '..', '.staging');
    const stagingDir = fs.readdirSync(stagingRoot, { withFileTypes: true })
      .find((entry) => entry.isDirectory())?.name;
    if (stagingDir) {
      const target = path.join(stagingRoot, stagingDir, 'assets');
      const outside = process.env.MOCK_OD_SYMLINK_OUTSIDE;
      if (!fs.existsSync(target)) fs.symlinkSync(outside, target, 'dir');
    }
  }
  json({ files: [{ name: path.basename(filePath), path: filePath, type: 'file', size: Buffer.byteLength(html), kind: 'html', artifactManifest: { status: 'complete' } }] });
} else if (args[0] === 'files' && args[1] === 'read') {
  process.stdout.write(currentHtml());
} else if (args[0] === 'files' && args[1] === 'write') {
  const content = fs.readFileSync(0);
  const relativePath = args[3];
  const target = path.join(stateDir, 'written-files', relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
  json({ file: { name: relativePath } });
} else {
  process.stderr.write(`unsupported mock od command: ${args.join(' ')}\n`);
  process.exitCode = 2;
}
