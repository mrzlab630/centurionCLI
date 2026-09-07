#!/usr/bin/env node
'use strict';

const { spawn } = require('node:child_process');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');

const MAX_QUERY_LENGTH = 4000;
const MAX_JSON_LENGTH = 16384;
const MAX_OUTPUT_BYTES = 256 * 1024;
const MAX_STDERR_BYTES = 64 * 1024;
const MAX_DEPTH = 8;
const MAX_ARRAY_ITEMS = 100;
const MAX_OBJECT_KEYS = 100;
const DEFAULT_LIMIT = 5;
const MAX_LIMIT = 10;
const DEFAULT_TIMEOUT_MS = 10000;
const MAX_TIMEOUT_MS = 60000;
const DEFAULT_POLL_TIMEOUT_MS = 30000;
const MAX_POLL_TIMEOUT_MS = 120000;
const DEFAULT_MAX_POLLS = 8;
const MAX_MAX_POLLS = 20;
const DEFAULT_POLL_INTERVAL_MS = 250;
const MAX_POLL_INTERVAL_MS = 5000;
const MAX_URL_DECODE_PASSES = 8;
const TERMINAL_STATUSES = new Set(['COMPLETED', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'BLOCKED']);
const KNOWN_PENDING_STATUSES = new Set(['PENDING', 'QUEUED', 'RUNNING', 'IN_PROGRESS']);
const SENSITIVE_KEY_PATTERN = /(?:token|secret|password|cookie|authorization|api[-_]?key|credential|private[-_]?key|access[-_]?key|sig(?:nature)?)/iu;
const COMMAND_OPTIONS = {
  discover: new Set(['enable', 'query', 'limit', 'timeout-ms']),
  inspect: new Set(['enable', 'provider', 'endpoint', 'timeout-ms']),
  run: new Set(['enable', 'provider', 'endpoint', 'input', 'authorization', 'wait', 'confirm-cost', 'timeout-ms', 'poll-timeout-ms', 'max-polls', 'poll-interval-ms'])
};
const CREDENTIAL_VALUE_PATTERN = /(?:bearer|basic)\s+[A-Za-z0-9._~+\/-]{8,}|(?:sk|pk|rk|key|token|secret|credential|cred|auth|access)[_-][A-Za-z0-9_-]{8,}|(?:eyJ[A-Za-z0-9_-]{8,}\.){2}[A-Za-z0-9_-]{8,}|(?:token|secret|password|authorization|api[-_]?key|credential|private[-_]?key|access[-_]?key|signature?)\s*[:=]\s*[^\s&#]{6,}/iu;

const USAGE = `Usage:
  monid-adapter.js discover --query <text> [--limit <n>] --enable
  monid-adapter.js inspect --provider <slug> --endpoint <path> --enable
  monid-adapter.js run --provider <slug> --endpoint <path> --input <json> --authorization <json> --enable --wait --confirm-cost

The adapter is disabled unless --enable is supplied. It never installs or configures Monid.`;

function resultError(code, message, details = {}) { return { ok: false, error: { code, message, ...details } }; }

function fail(code, message, details = {}) {
  const error = new Error(message);
  error.result = resultError(code, message, details);
  error.code = code;
  return error;
}

function parseArgs(argv) {
  if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h') return { help: true };
  const command = argv[0];
  if (!['discover', 'inspect', 'run'].includes(command)) throw fail('UNSUPPORTED_COMMAND', 'Unsupported adapter command.');
  const options = {};
  const booleans = new Set(['enable', 'wait', 'confirm-cost']);
  const values = new Set(['query', 'limit', 'provider', 'endpoint', 'input', 'authorization', 'timeout-ms', 'poll-timeout-ms', 'max-polls', 'poll-interval-ms']);
  for (let i = 1; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) throw fail('INVALID_ARGUMENT', 'Unexpected positional argument.');
    const name = token.slice(2);
    if (booleans.has(name)) {
      if (options[name] === true) throw fail('INVALID_ARGUMENT', 'Duplicate flag.');
      options[name] = true;
      continue;
    }
    if (!values.has(name) || i + 1 >= argv.length || argv[i + 1].startsWith('--') || options[name] !== undefined) throw fail('INVALID_ARGUMENT', 'Invalid or missing option value.');
    options[name] = argv[i + 1];
    i += 1;
  }
  validateCommandOptions(command, options);
  return { command, options };
}

function validateCommandOptions(command, options) {
  const allowed = COMMAND_OPTIONS[command];
  if (!allowed) throw fail('UNSUPPORTED_COMMAND', 'Unsupported adapter command.');
  if (!options || typeof options !== 'object' || Array.isArray(options)) throw fail('INVALID_ARGUMENT', 'Invalid command options.');
  for (const name of Object.keys(options)) {
    if (!allowed.has(name)) throw fail('INVALID_ARGUMENT', `Option --${name} does not apply to ${command}.`);
  }
}

function requireText(value, field, maxLength) {
  if (typeof value !== 'string' || value.length === 0 || value.length > maxLength || /[\u0000-\u001f\u007f]/u.test(value)) throw fail('INVALID_ARGUMENT', `Invalid ${field}.`);
  return value;
}

function validateProvider(value) {
  const provider = requireText(value, 'provider', 64);
  if (!/^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$/u.test(provider)) throw fail('INVALID_ARGUMENT', 'Invalid provider.');
  return provider;
}

function validateEndpoint(value) {
  const endpoint = requireText(value, 'endpoint', 256);
  if (!endpoint.startsWith('/') || endpoint.includes('..') || /[\\;&|`$<>\n\r\t]/u.test(endpoint)) throw fail('INVALID_ARGUMENT', 'Invalid endpoint.');
  return endpoint;
}

function parseBoundedInteger(value, field, min, max, fallback) {
  if (value === undefined) return fallback;
  if (!/^[0-9]+$/u.test(value)) throw fail('INVALID_ARGUMENT', `Invalid ${field}.`);
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < min || parsed > max) throw fail('INVALID_ARGUMENT', `Invalid ${field}.`);
  return parsed;
}

// Parse JSON with bounded structure and duplicate-key rejection before handing it to a child.
function parseJsonValue(value, field) {
  requireText(value, field, MAX_JSON_LENGTH);
  let index = 0;
  const whitespace = () => { while (/\s/u.test(value[index] || '')) index += 1; };
  const parseString = () => {
    if (value[index] !== '"') throw new Error('string');
    const start = index++;
    let escaped = false;
    while (index < value.length) {
      const char = value[index++];
      if (escaped) { escaped = false; continue; }
      if (char === '\\') { escaped = true; continue; }
      if (char === '"') return JSON.parse(value.slice(start, index));
      if (char < ' ') throw new Error('control');
    }
    throw new Error('unterminated');
  };
  const parseValue = (depth) => {
    if (depth > MAX_DEPTH) throw new Error('depth');
    whitespace();
    const char = value[index];
    if (char === '"') return parseString();
    if (char === '{') {
      index += 1;
      const object = Object.create(null);
      const keys = new Set();
      whitespace();
      if (value[index] === '}') { index += 1; return object; }
      while (index < value.length) {
        whitespace();
        const key = parseString();
        if (keys.has(key) || keys.size >= MAX_OBJECT_KEYS) throw new Error('keys');
        keys.add(key);
        whitespace();
        if (value[index++] !== ':') throw new Error('colon');
        object[key] = parseValue(depth + 1);
        whitespace();
        if (value[index] === '}') { index += 1; return object; }
        if (value[index++] !== ',') throw new Error('comma');
      }
      throw new Error('object');
    }
    if (char === '[') {
      index += 1;
      const array = [];
      whitespace();
      if (value[index] === ']') { index += 1; return array; }
      while (index < value.length) {
        if (array.length >= MAX_ARRAY_ITEMS) throw new Error('array');
        array.push(parseValue(depth + 1));
        whitespace();
        if (value[index] === ']') { index += 1; return array; }
        if (value[index++] !== ',') throw new Error('comma');
      }
      throw new Error('array');
    }
    const match = value.slice(index).match(/^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/u);
    if (!match) throw new Error('value');
    index += match[0].length;
    const primitive = JSON.parse(match[0]);
    if (typeof primitive === 'number' && !Number.isFinite(primitive)) throw new Error('number');
    return primitive;
  };
  try {
    const parsed = parseValue(0);
    whitespace();
    if (index !== value.length || !parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('root');
    return parsed;
  } catch { throw fail('INVALID_JSON_INPUT', `Invalid JSON for ${field}.`); }
}

function decodeRepeated(value) {
  let decoded = value.replace(/\+/gu, ' ');
  for (let attempt = 0; attempt < MAX_URL_DECODE_PASSES; attempt += 1) {
    let next;
    try { next = decodeURIComponent(decoded); } catch { break; }
    if (next === decoded) break;
    decoded = next.replace(/\+/gu, ' ');
  }
  return decoded;
}

function isCredentialLikeValue(value) {
  const decoded = decodeRepeated(String(value));
  return CREDENTIAL_VALUE_PATTERN.test(decoded) || /%[0-9a-f]{2}/iu.test(decoded);
}

function sanitizeUrlString(value) {
  const normalized = value.trimStart();
  if (!/^https?:\/\//iu.test(normalized)) return value;
  const authorityMatch = normalized.match(/^(https?:\/\/)([^/?#]*)/iu);
  // Drop the whole URL rather than turn a credential-bearing source into a candidate.
  if (authorityMatch && (decodeRepeated(authorityMatch[2]).includes('@') || isCredentialLikeValue(authorityMatch[2]))) return '[REDACTED]';
  const hashIndex = normalized.indexOf('#');
  const withoutFragment = hashIndex >= 0 ? normalized.slice(0, hashIndex) : normalized;
  const queryIndex = withoutFragment.indexOf('?');
  if (queryIndex < 0) return withoutFragment;
  const prefix = withoutFragment.slice(0, queryIndex);
  const query = withoutFragment.slice(queryIndex + 1);
  const sanitizedQuery = query.split('&').map((part) => {
    const separator = part.indexOf('=');
    if (separator < 0) return part;
    const rawKey = part.slice(0, separator);
    const rawValue = part.slice(separator + 1);
    const decodedKey = decodeRepeated(rawKey);
    return SENSITIVE_KEY_PATTERN.test(decodedKey) || isCredentialLikeValue(rawValue)
      ? `${rawKey}=[REDACTED]`
      : `${rawKey}=${rawValue}`;
  }).join('&');
  return `${prefix}?${sanitizedQuery}`;
}

function sanitize(value, key = '') {
  if (SENSITIVE_KEY_PATTERN.test(key)) return '[REDACTED]';
  if (typeof value === 'string') {
    return sanitizeUrlString(value)
      .replace(/([?&])([^=&#\s]+)=([^&#\s]*)/gu, (match, delimiter, queryKey, queryValue) => {
        let decodedKey = queryKey;
        try { decodedKey = decodeURIComponent(queryKey); } catch {}
        return SENSITIVE_KEY_PATTERN.test(decodedKey) || isCredentialLikeValue(queryValue) ? `${delimiter}${queryKey}=[REDACTED]` : `${delimiter}${queryKey}=${queryValue}`;
      })
      .replace(/(?:Bearer|Basic)\s+[A-Za-z0-9._~+\/-]{8,}/giu, (match) => `${match.split(/\s+/u)[0]} [REDACTED]`)
      .replace(/(?:sk|pk|rk|key|token|secret|credential|cred|auth|access)[_-][A-Za-z0-9_-]{8,}/giu, '[REDACTED]');
  }
  if (Array.isArray(value)) return value.slice(0, MAX_ARRAY_ITEMS).map((item) => sanitize(item));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).slice(0, MAX_OBJECT_KEYS).map(([childKey, childValue]) => [childKey, sanitize(childValue, childKey)]));
  return value;
}

const FORBIDDEN_IPV4_RANGES = [
  [0x00000000, 8], // Current network and unspecified
  [0x0a000000, 8], // Private
  [0x64400000, 10], // Shared address space
  [0x7f000000, 8], // Loopback
  [0xa9fe0000, 16], // Link-local
  [0xac100000, 12], // Private
  [0xc0000000, 24], // IETF protocol assignments
  [0xc0000200, 24], // Documentation
  [0xc0586300, 24], // 6to4 anycast (deprecated)
  [0xc0a80000, 16], // Private
  [0xc6120000, 15], // Benchmarking
  [0xc6336400, 24], // Documentation
  [0xcb007100, 24], // Documentation
  [0xe0000000, 4], // Multicast
  [0xf0000000, 4] // Reserved
];

const FORBIDDEN_IPV6_RANGES = [
  [Array(12).fill(0), 96], // IPv4-compatible, unspecified, and loopback space
  [[0x01, 0x00, 0x00, 0x00], 64], // Discard-only
  [[0x20, 0x01, 0x00, 0x01], 32], // Port Control Protocol anycast
  [[0x20, 0x01, 0x00, 0x00], 32], // Special-purpose 2001::/32
  [[0x20, 0x01, 0x00, 0x30], 28], // Documentation and benchmarking 2001:30::/28
  [[0x20, 0x01, 0x00, 0x02], 48], // Benchmarking
  [[0x20, 0x01, 0x00, 0x03], 32], // AMT
  [[0x20, 0x01, 0x00, 0x04, 0x01, 0x12], 48], // AS112-v4
  [[0x20, 0x01, 0x00, 0x10], 28], // ORCHID
  [[0x20, 0x01, 0x00, 0x20], 28], // ORCHIDv2
  [[0x20, 0x01, 0x0d, 0xb8], 32], // Documentation
  [[0x20, 0x02], 16], // 6to4
  [[0x00, 0x64, 0xff, 0x9b, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00], 96], // IPv4-IPv6 translation
  [[0x00, 0x64, 0xff, 0x9b, 0x00, 0x01], 48], // Network-specific IPv4-IPv6 translation
  [[0x3f, 0xff], 20], // Documentation
  [[0xfc], 7], // Unique local
  [[0xfe, 0x80], 10], // Link-local
  [[0xff], 8] // Multicast
];

function ipv4Number(hostname) {
  const octets = hostname.split('.');
  if (octets.length !== 4 || octets.some((octet) => !/^[0-9]{1,3}$/u.test(octet) || Number(octet) > 255)) return null;
  return octets.reduce((value, octet) => (value * 256) + Number(octet), 0);
}

function ipv4InRange(address, [base, prefix]) {
  const mask = prefix === 0 ? 0 : (0xffffffff << (32 - prefix)) >>> 0;
  return (address & mask) === (base & mask);
}

function parseIpv6Bytes(address) {
  let value = address.toLowerCase();
  if (value.includes('.')) {
    const separator = value.lastIndexOf(':');
    if (separator < 0) return null;
    const embedded = ipv4Number(value.slice(separator + 1));
    if (embedded === null) return null;
    const prefix = value.slice(0, separator + 1);
    value = `${prefix}${(embedded >>> 16).toString(16)}:${(embedded & 0xffff).toString(16)}`;
  }
  const halves = value.split('::');
  if (halves.length > 2) return null;
  const left = halves[0] ? halves[0].split(':') : [];
  const right = halves.length === 2 && halves[1] ? halves[1].split(':') : [];
  if ([...left, ...right].some((part) => !/^[0-9a-f]{1,4}$/u.test(part))) return null;
  const groups = halves.length === 2 ? [...left, ...Array(8 - left.length - right.length).fill('0'), ...right] : [...left, ...right];
  if (groups.length !== 8) return null;
  const bytes = [];
  for (const group of groups) {
    const number = Number.parseInt(group, 16);
    bytes.push(number >>> 8, number & 0xff);
  }
  return bytes;
}

function ipv6InRange(address, [prefix, prefixLength]) {
  const prefixBytes = prefix.length === 16 ? prefix : [...prefix, ...Array(16 - prefix.length).fill(0)];
  const fullBytes = Math.floor(prefixLength / 8);
  if (!address.slice(0, fullBytes).every((byte, index) => byte === prefixBytes[index])) return false;
  const remainder = prefixLength % 8;
  return remainder === 0 || (address[fullBytes] >> (8 - remainder)) === (prefixBytes[fullBytes] >> (8 - remainder));
}

function isForbiddenIpv4(address) {
  return FORBIDDEN_IPV4_RANGES.some((range) => ipv4InRange(address, range));
}

function isForbiddenIpv6(bytes) {
  if (FORBIDDEN_IPV6_RANGES.some((range) => ipv6InRange(bytes, range))) return true;
  const mapped = bytes.slice(0, 10).every((byte) => byte === 0) && bytes[10] === 0xff && bytes[11] === 0xff;
  if (mapped) {
    const embedded = bytes.slice(12).reduce((value, byte) => (value * 256) + byte, 0);
    return isForbiddenIpv4(embedded);
  }
  return false;
}

function hasExplicitPort(value) {
  const authorityMatch = value.trimStart().match(/^https?:\/\/([^/?#]*)/iu);
  if (!authorityMatch) return false;
  const authority = authorityMatch[1];
  const hostPort = authority.slice(authority.lastIndexOf('@') + 1);
  if (hostPort.startsWith('[')) {
    const closingBracket = hostPort.indexOf(']');
    return closingBracket >= 0 && hostPort.slice(closingBracket + 1).startsWith(':');
  }
  return hostPort.includes(':');
}

function validateCandidateUrl(value) {
  if (typeof value !== 'string' || value.length > 2048) return false;
  if (hasExplicitPort(value)) return false;
  let url;
  try { url = new URL(value); } catch { return false; }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.port) return false;
  // URLSearchParams already decoded once. Remaining escapes in a key are
  // ambiguous nested encoding: fail closed even if the eventual spelling is benign.
  if ([...url.searchParams.entries()].some(([key, value]) => SENSITIVE_KEY_PATTERN.test(decodeRepeated(key)) || /%[0-9a-f]{2}/iu.test(key) || isCredentialLikeValue(value))) return false;
  const hostname = url.hostname.toLowerCase();
  const normalizedHostname = hostname.replace(/\.+$/u, '');
  if (normalizedHostname === 'localhost' || normalizedHostname.endsWith('.localhost') || normalizedHostname === 'metadata.google.internal' || normalizedHostname === 'instance-data.ec2.internal') return false;
  const literalHostname = normalizedHostname.replace(/^\[|\]$/gu, '');
  const ipVersion = net.isIP(literalHostname);
  if (ipVersion === 4 && isForbiddenIpv4(ipv4Number(normalizedHostname))) return false;
  if (ipVersion === 6) {
    const bytes = parseIpv6Bytes(literalHostname);
    if (!bytes || isForbiddenIpv6(bytes)) return false;
  }
  return true;
}

function candidateProvenance(payload) {
  const urls = [];
  const safePayload = sanitize(payload);
  const visit = (value) => {
    if (urls.length >= 20) return;
    if (typeof value === 'string' && /^https?:\/\//iu.test(value) && validateCandidateUrl(value) && !urls.includes(value)) { urls.push(value); return; }
    if (Array.isArray(value)) { value.slice(0, MAX_ARRAY_ITEMS).forEach(visit); return; }
    if (value && typeof value === 'object') Object.values(value).slice(0, MAX_OBJECT_KEYS).forEach(visit);
  };
  visit(safePayload);
  return { kind: 'candidate-unverified', urls };
}

function extractPayloadStatus(payload) {
  const body = payload && typeof payload.data === 'object' && !Array.isArray(payload.data) ? payload.data : payload;
  const rawStatus = typeof body?.status === 'string' ? body.status.toUpperCase() : undefined;
  return { body, rawStatus, status: rawStatus && (TERMINAL_STATUSES.has(rawStatus) || KNOWN_PENDING_STATUSES.has(rawStatus) ? rawStatus : 'UNKNOWN'), runId: typeof body?.runId === 'string' ? body.runId : (typeof body?.run_id === 'string' ? body.run_id : undefined), cost: body?.cost, currency: body?.currency, controls: body?.controls };
}

function childEnvironment() {
  return {
    PATH: process.env.PATH || '',
    HOME: fs.mkdtempSync(path.join(os.tmpdir(), 'monid-home-')),
    XDG_CONFIG_HOME: fs.mkdtempSync(path.join(os.tmpdir(), 'monid-config-')),
    XDG_CACHE_HOME: fs.mkdtempSync(path.join(os.tmpdir(), 'monid-cache-')),
    LANG: process.env.LANG || 'C',
    LC_ALL: process.env.LC_ALL || 'C'
  };
}

function approvedBinary() {
  const override = process.env.MONID_BIN;
  if (override !== undefined) {
    if (process.env.MONID_ADAPTER_TEST_MODE !== '1' || !path.isAbsolute(override) || !override.endsWith('.js')) throw fail('MONID_BIN_FORBIDDEN', 'MONID_BIN is accepted only as an absolute Node fixture in test mode.');
    return override;
  }
  const configured = process.env.MONID_APPROVED_BIN;
  if (!configured || !path.isAbsolute(configured)) throw fail('MONID_BINARY_NOT_APPROVED', 'An approved absolute Monid executable is required.');
  return configured;
}

function spawnJson(binary, args, timeoutMs, spawnImpl = spawn) {
  return new Promise((resolve, reject) => {
    let child;
    try { child = spawnImpl(binary, args, { shell: false, windowsHide: true, env: childEnvironment() }); } catch { reject(fail('MONID_SPAWN_FAILED', 'Unable to start Monid command.')); return; }
    let stdout = '';
    let stderrBytes = 0;
    let killTimer;
    let settled = false;
    let timer;
    const finish = (error, value, keepKillTimer = false) => { if (settled) return; settled = true; clearTimeout(timer); if (!keepKillTimer) clearTimeout(killTimer); if (error) reject(error); else resolve(value); };
    const terminate = () => {
      try { child.kill('SIGTERM'); } catch {}
      if (!killTimer) killTimer = setTimeout(() => { try { child.kill('SIGKILL'); } catch {} }, 100);
    };
    timer = setTimeout(() => { terminate(); finish(fail('MONID_TIMEOUT', 'Monid command timed out.'), undefined, true); }, timeoutMs);
    child.stdout?.on('data', (chunk) => { if (settled) return; stdout += chunk.toString('utf8'); if (Buffer.byteLength(stdout) > MAX_OUTPUT_BYTES) { terminate(); finish(fail('MONID_OUTPUT_LIMIT', 'Monid output exceeded the bounded limit.'), undefined, true); } });
    child.stderr?.on('data', (chunk) => { stderrBytes += Buffer.byteLength(chunk.toString('utf8')); if (stderrBytes > MAX_STDERR_BYTES) { terminate(); finish(fail('MONID_OUTPUT_LIMIT', 'Monid diagnostics exceeded the bounded limit.'), undefined, true); } });
    child.once('error', (error) => { if (!settled) finish(fail(error?.code === 'ENOENT' ? 'MONID_NOT_FOUND' : 'MONID_SPAWN_FAILED', 'Unable to start Monid command.')); });
    child.once('close', (code, signal) => {
      clearTimeout(killTimer);
      if (settled) return;
      if (signal || code !== 0) { finish(fail('MONID_EXIT_NONZERO', 'Monid command failed.', { exitCode: typeof code === 'number' ? code : null })); return; }
      try { if (!stdout.trim()) throw new Error(); const payload = parseJsonValue(stdout, 'Monid output'); finish(null, { payload: sanitize(payload), stderrBytes }); } catch (error) { finish(error?.result ? error : fail('MONID_MALFORMED_JSON', 'Monid returned malformed JSON.')); }
    });
  });
}

function required(options, fields) { for (const field of fields) if (options[field] === undefined) throw fail('INVALID_ARGUMENT', `Missing required option --${field}.`); }

function validateAuthorization(authorization, provider, endpoint, now = Date.now()) {
  if (!authorization || authorization.provider !== provider || authorization.endpoint !== endpoint || typeof authorization.currency !== 'string' || !/^[A-Z]{3,8}$/u.test(authorization.currency) || !Number.isFinite(authorization.maxCost) || authorization.maxCost < 0 || typeof authorization.expiresAt !== 'string') throw fail('COST_AUTH_INVALID', 'A finite provider, endpoint, currency, maxCost, and expiry authorization is required.');
  const expiry = Date.parse(authorization.expiresAt);
  if (!Number.isFinite(expiry) || expiry <= now) throw fail('COST_AUTH_EXPIRED', 'Cost authorization has expired.');
}

function validateCompletedCost(meta, authorization) {
  if (!Number.isFinite(meta.cost) || meta.cost < 0 || typeof meta.currency !== 'string' || meta.currency !== authorization.currency || meta.cost > authorization.maxCost) {
    throw fail('COST_UNVERIFIABLE', 'Completed cost is missing, mismatched, negative, or exceeds authorization.');
  }
}

function buildArgs(command, options) {
  validateCommandOptions(command, options);
  if (command === 'discover') { required(options, ['query']); requireText(options.query, 'query', MAX_QUERY_LENGTH); const limit = parseBoundedInteger(options.limit, 'limit', 1, MAX_LIMIT, DEFAULT_LIMIT); return ['discover', '-q', options.query, '--limit', String(limit), '--json']; }
  required(options, ['provider', 'endpoint']);
  const provider = validateProvider(options.provider); const endpoint = validateEndpoint(options.endpoint);
  if (command === 'inspect') return ['inspect', '-p', provider, '-e', endpoint, '--json'];
  required(options, ['input', 'authorization']);
  if (!options.wait) throw fail('WAIT_REQUIRED', 'run requires --wait.');
  const input = parseJsonValue(options.input, 'input');
  validateAuthorization(parseJsonValue(options.authorization, 'authorization'), provider, endpoint);
  return ['run', '-p', provider, '-e', endpoint, '-i', JSON.stringify(input), '--wait', '--json'];
}

async function runCommand(command, options = {}, dependencies = {}) {
  if (!options || typeof options !== 'object' || Array.isArray(options)) throw fail('INVALID_ARGUMENT', 'Invalid command options.');
  if (!options.enable) throw fail('MONID_DISABLED', 'Monid adapter is disabled; pass --enable explicitly.');
  validateCommandOptions(command, options);
  if (command === 'run' && options['confirm-cost'] !== true) throw fail('COST_CONFIRMATION_REQUIRED', 'Potentially billable run requires --confirm-cost.');
  const timeoutMs = parseBoundedInteger(options['timeout-ms'], 'timeout-ms', 1, MAX_TIMEOUT_MS, DEFAULT_TIMEOUT_MS);
  const pollTimeoutMs = command === 'run' ? parseBoundedInteger(options['poll-timeout-ms'], 'poll-timeout-ms', 1, MAX_POLL_TIMEOUT_MS, DEFAULT_POLL_TIMEOUT_MS) : undefined;
  const maxPolls = command === 'run' ? parseBoundedInteger(options['max-polls'], 'max-polls', 1, MAX_MAX_POLLS, DEFAULT_MAX_POLLS) : undefined;
  const pollIntervalMs = command === 'run' ? parseBoundedInteger(options['poll-interval-ms'], 'poll-interval-ms', 0, MAX_POLL_INTERVAL_MS, DEFAULT_POLL_INTERVAL_MS) : undefined;
  const binary = dependencies.binary || approvedBinary();
  const invoke = dependencies.spawnJson || ((args, timeout) => spawnJson(binary, args, timeout, dependencies.spawnImpl));
  if (command !== 'run') { const response = await invoke(buildArgs(command, options), timeoutMs); return { ok: true, command, data: response.payload, provenance: candidateProvenance(response.payload) }; }
  const provider = validateProvider(options.provider); const endpoint = validateEndpoint(options.endpoint); const authorization = parseJsonValue(options.authorization, 'authorization');
  validateAuthorization(authorization, provider, endpoint);
  parseJsonValue(options.input, 'input');
  const inspect = await invoke(buildArgs('inspect', { provider, endpoint }), timeoutMs); const inspectMeta = extractPayloadStatus(inspect.payload); const estimatedCost = inspectMeta.body?.estimatedCost ?? inspectMeta.body?.estimated_cost ?? inspectMeta.body?.cost;
  if (!Number.isFinite(estimatedCost) || estimatedCost < 0 || typeof inspectMeta.body?.currency !== 'string' || inspectMeta.body.currency !== authorization.currency || estimatedCost > authorization.maxCost) throw fail('COST_UNVERIFIABLE', 'Estimated cost is missing, mismatched, or exceeds authorization.');
  const first = await invoke(buildArgs('run', options), timeoutMs); const firstMeta = extractPayloadStatus(first.payload);
  if (firstMeta.status === 'BLOCKED') throw fail('MONID_BLOCKED', 'Monid run was blocked and will not be retried.', { runId: firstMeta.runId || null, controls: sanitize(firstMeta.controls || null) });
  if (firstMeta.status === 'FAILED' || firstMeta.status === 'CANCELLED') throw fail('MONID_TERMINAL_FAILURE', 'Monid run ended in a terminal failure.', { status: firstMeta.rawStatus });
  if (firstMeta.status === 'COMPLETED' || firstMeta.status === 'SUCCEEDED') {
    validateCompletedCost(firstMeta, authorization);
    return { ok: true, command, runId: firstMeta.runId || null, status: firstMeta.status, rawStatus: firstMeta.rawStatus, cost: firstMeta.cost, data: first.payload, provenance: candidateProvenance(first.payload) };
  }
  if (!firstMeta.runId || !KNOWN_PENDING_STATUSES.has(firstMeta.status)) throw fail('MONID_UNKNOWN_STATUS', 'Monid returned an unknown or malformed run status.');
  const startedAt = Date.now(); const deadline = startedAt + pollTimeoutMs; let last = first;
  for (let poll = 0; poll < maxPolls; poll += 1) {
    let remainingMs = deadline - Date.now();
    if (remainingMs <= 0) break;
    if (pollIntervalMs) {
      await new Promise((resolve) => setTimeout(resolve, Math.min(pollIntervalMs, remainingMs)));
      remainingMs = deadline - Date.now();
      if (remainingMs <= 0) break;
    }
    let polled;
    try {
      polled = await invoke(['runs', 'get', '-r', firstMeta.runId, '--wait', '--json'], Math.min(timeoutMs, remainingMs));
    } catch (error) {
      if (error?.code === 'MONID_TIMEOUT' && Date.now() >= deadline) throw fail('MONID_POLL_TIMEOUT', 'Monid polling deadline exceeded.', { runId: firstMeta.runId, maxPolls, elapsedMs: Date.now() - startedAt });
      throw error;
    }
    last = polled;
    if (Date.now() >= deadline) throw fail('MONID_POLL_TIMEOUT', 'Monid polling deadline exceeded.', { runId: firstMeta.runId, maxPolls, elapsedMs: Date.now() - startedAt });
    const meta = extractPayloadStatus(polled.payload);
    if (meta.status === 'BLOCKED') throw fail('MONID_BLOCKED', 'Monid run was blocked and will not be retried.', { runId: firstMeta.runId, controls: sanitize(meta.controls || null) });
    if (meta.status === 'FAILED' || meta.status === 'CANCELLED') throw fail('MONID_TERMINAL_FAILURE', 'Monid run ended in a terminal failure.', { status: meta.rawStatus });
    if (meta.status === 'COMPLETED' || meta.status === 'SUCCEEDED') {
      validateCompletedCost(meta, authorization);
      return { ok: true, command, runId: firstMeta.runId, status: meta.status, rawStatus: meta.rawStatus, cost: meta.cost, data: polled.payload, provenance: candidateProvenance(polled.payload) };
    }
    if (!KNOWN_PENDING_STATUSES.has(meta.status)) throw fail('MONID_UNKNOWN_STATUS', 'Monid returned an unknown or malformed poll status.');
  }
  const elapsedMs = Date.now() - startedAt;
  if (elapsedMs >= pollTimeoutMs) throw fail('MONID_POLL_TIMEOUT', 'Monid polling deadline exceeded.', { runId: firstMeta.runId, maxPolls, elapsedMs });
  throw fail('MONID_POLL_LIMIT', 'Monid polling limit exceeded.', { runId: firstMeta.runId, maxPolls });
}

async function main(argv = process.argv.slice(2), dependencies = {}) {
  try { const parsed = parseArgs(argv); if (parsed.help) { process.stdout.write(`${USAGE}\n`); return 0; } process.stdout.write(`${JSON.stringify(await runCommand(parsed.command, parsed.options, dependencies))}\n`); return 0; }
  catch (error) { process.stderr.write(`${JSON.stringify(error?.result || resultError('MONID_ADAPTER_FAILED', 'Monid adapter failed.'))}\n`); return 1; }
}

if (require.main === module) main().then((code) => { process.exitCode = code; }).catch(() => { process.exitCode = 1; });

module.exports = { MAX_OUTPUT_BYTES, candidateProvenance, main, parseArgs, parseJsonValue, runCommand, sanitize, spawnJson, validateAuthorization, validateCandidateUrl };
