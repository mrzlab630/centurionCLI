#!/usr/bin/env node
import fs from 'node:fs';
import process from 'node:process';

const DEFAULT_BASE_URL = process.env.CAMOFOX_BASE_URL || 'http://127.0.0.1:9377';
const DEFAULT_USER_ID = `codex-camofox-${process.pid}-${Date.now()}`;

function usage() {
  return `Usage: camofox-smoke.mjs [options] [url]\n\nOptions:\n  --base-url <url>       Camofox server URL. Default: ${DEFAULT_BASE_URL}\n  --user-id <id>         Session user id. Default: ${DEFAULT_USER_ID}\n  --session-key <key>    Session key/list item id. Default: codex-smoke\n  --screenshot <file>    Save PNG screenshot to file\n  --health               Only run health check\n  --json                 Print JSON only\n`;
}

function parseArgs(argv) {
  const options = {
    baseUrl: DEFAULT_BASE_URL,
    userId: DEFAULT_USER_ID,
    sessionKey: 'codex-smoke',
    screenshotPath: null,
    healthOnly: false,
    json: false,
    url: null
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--base-url') options.baseUrl = argv[++i];
    else if (arg === '--user-id') options.userId = argv[++i];
    else if (arg === '--session-key') options.sessionKey = argv[++i];
    else if (arg === '--screenshot') options.screenshotPath = argv[++i];
    else if (arg === '--health') options.healthOnly = true;
    else if (arg === '--json') options.json = true;
    else if (arg === '--help' || arg === '-h') options.help = true;
    else if (!options.url) options.url = arg;
    else throw new Error(`Unexpected argument: ${arg}`);
  }
  options.baseUrl = options.baseUrl.replace(/\/$/, '');
  return options;
}

function assertHttpUrl(value) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`Invalid URL: ${value}`);
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`Blocked URL scheme: ${parsed.protocol} (only http/https allowed)`);
  }
  return parsed.toString();
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'content-type': 'application/json',
      ...(options.headers || {})
    }
  });
  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { raw: text };
    }
  }
  if (!response.ok) {
    const details = body ? JSON.stringify(body) : text;
    throw new Error(`${options.method || 'GET'} ${url} failed ${response.status}: ${details}`);
  }
  return body;
}

async function requestBuffer(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${options.method || 'GET'} ${url} failed ${response.status}: ${text}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

async function health(baseUrl) {
  return requestJson(`${baseUrl}/health`);
}

function summarizeSnapshot(snapshot) {
  const raw = snapshot?.snapshot || snapshot?.text || snapshot?.content || '';
  const text = typeof raw === 'string' ? raw : JSON.stringify(raw || '');
  const titleMatch = text.match(/(?:title|heading|text)[:=]\s*['\"]?([^\n'\"]{1,120})/i);
  return {
    length: text.length,
    refsCount: snapshot?.refsCount ?? snapshot?.refs?.length ?? null,
    truncated: Boolean(snapshot?.truncated),
    titleHint: titleMatch ? titleMatch[1].trim() : null,
    preview: text.replace(/\s+/g, ' ').slice(0, 280)
  };
}

async function cleanup(baseUrl, userId) {
  try {
    await requestJson(`${baseUrl}/sessions/${encodeURIComponent(userId)}`, { method: 'DELETE' });
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

async function run(options) {
  const healthResult = await health(options.baseUrl);
  if (options.healthOnly) {
    return { ok: true, baseUrl: options.baseUrl, health: healthResult };
  }
  if (!options.url) throw new Error('URL is required unless --health is used');
  const url = assertHttpUrl(options.url);

  let tabId = null;
  try {
    const created = await requestJson(`${options.baseUrl}/tabs`, {
      method: 'POST',
      body: JSON.stringify({ url, userId: options.userId, sessionKey: options.sessionKey })
    });
    tabId = created?.tabId || created?.id || created?.tab?.id;
    if (!tabId) throw new Error(`Could not determine tab id from response: ${JSON.stringify(created)}`);

    const snapshot = await requestJson(`${options.baseUrl}/tabs/${encodeURIComponent(tabId)}/snapshot?userId=${encodeURIComponent(options.userId)}`);
    let screenshot = null;
    if (options.screenshotPath) {
      const screenshotBuffer = await requestBuffer(`${options.baseUrl}/tabs/${encodeURIComponent(tabId)}/screenshot?userId=${encodeURIComponent(options.userId)}`);
      fs.writeFileSync(options.screenshotPath, screenshotBuffer);
      screenshot = { path: options.screenshotPath, bytes: fs.statSync(options.screenshotPath).size };
    }

    const cleaned = await cleanup(options.baseUrl, options.userId);
    return {
      ok: true,
      baseUrl: options.baseUrl,
      url,
      userId: options.userId,
      tabId,
      health: healthResult,
      snapshot: summarizeSnapshot(snapshot),
      screenshot,
      cleanup: cleaned
    };
  } catch (error) {
    const cleaned = await cleanup(options.baseUrl, options.userId);
    return {
      ok: false,
      baseUrl: options.baseUrl,
      url,
      userId: options.userId,
      tabId,
      error: error.message,
      cleanup: cleaned
    };
  }
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
  } else {
    const report = await run(options);
    if (options.json) process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    else {
      process.stdout.write(`Camofox smoke: ${report.ok ? 'pass' : 'fail'}\n`);
      process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    }
    if (!report.ok) process.exitCode = 1;
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
