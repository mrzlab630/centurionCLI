import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export const LEGION_ORDER_VERSION = 'LEGION_ORDER_V1';
export const LEGION_RESULT_VERSION = 'LEGION_RESULT_V1';
export const LEGION_REVIEW_VERSION = 'LEGION_REVIEW_V1';
export const AGENT_RESULT_VERSION = 'AGENT_RESULT_JSON_V1';
const SAFE_ORDER_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/;

function strictJsonParser(text, label) {
  let index = 0;
  const length = text.length;
  const whitespace = () => { while (index < length && /\s/.test(text[index])) index += 1; };
  const parseString = () => {
    const start = index;
    if (text[index] !== '"') throw new Error(`${label} expected string at ${index}`);
    index += 1;
    while (index < length) {
      const char = text[index++];
      if (char === '\\') index += 1;
      else if (char === '"') return JSON.parse(text.slice(start, index));
    }
    throw new Error(`${label} unterminated string`);
  };
  const parseValue = () => {
    whitespace();
    if (text[index] === '{') return parseObject();
    if (text[index] === '[') return parseArray();
    if (text[index] === '"') return parseString();
    const start = index;
    while (index < length && !/[\s,\]}]/.test(text[index])) index += 1;
    const token = text.slice(start, index);
    if (!token) throw new Error(`${label} expected value at ${index}`);
    const value = JSON.parse(token);
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error(`${label} contains non-finite number`);
    return value;
  };
  const parseObject = () => {
    index += 1;
    const value = {};
    const keys = new Set();
    whitespace();
    if (text[index] === '}') { index += 1; return value; }
    while (index < length) {
      whitespace();
      const key = parseString();
      if (keys.has(key)) throw new Error(`${label} duplicate key ${JSON.stringify(key)}`);
      keys.add(key);
      whitespace();
      if (text[index++] !== ':') throw new Error(`${label} expected ':' at ${index - 1}`);
      Object.defineProperty(value, key, { value: parseValue(), enumerable: true, configurable: true, writable: true });
      whitespace();
      if (text[index] === '}') { index += 1; return value; }
      if (text[index++] !== ',') throw new Error(`${label} expected ',' at ${index - 1}`);
    }
    throw new Error(`${label} unterminated object`);
  };
  const parseArray = () => {
    index += 1;
    const value = [];
    whitespace();
    if (text[index] === ']') { index += 1; return value; }
    while (index < length) {
      value.push(parseValue());
      whitespace();
      if (text[index] === ']') { index += 1; return value; }
      if (text[index++] !== ',') throw new Error(`${label} expected ',' at ${index - 1}`);
    }
    throw new Error(`${label} unterminated array`);
  };
  const value = parseValue();
  whitespace();
  if (index !== length) throw new Error(`${label} trailing data at ${index}`);
  return value;
}

export function parseStrictJson(text, label = 'JSON') {
  if (typeof text !== 'string') throw new TypeError(`${label} must be text`);
  return strictJsonParser(text, label);
}

export const RESPONSE_ENVELOPE_VERSION = 'AGENT_RESPONSE_ENVELOPE_V1';
export const RESPONSE_TRANSPORTS = Object.freeze({ RAW_JSON: 'raw_json', JSON_FENCE: 'json_fence' });
export const RESPONSE_ERROR_CODES = Object.freeze({
  FORMAT: 'RESPONSE_FORMAT_ERROR',
  SCHEMA: 'RESPONSE_SCHEMA_ERROR',
  IDENTITY: 'RESPONSE_IDENTITY_ERROR',
  REFUSED: 'RESPONSE_REFUSED',
  INCOMPLETE: 'RESPONSE_INCOMPLETE'
});

export class ResponseEnvelopeError extends Error {
  constructor(code, message, details = {}) {
    super(`${code}: ${message}`);
    this.name = 'ResponseEnvelopeError';
    this.code = code;
    Object.assign(this, details);
  }
}

const RESPONSE_JSON_FENCE = /^[\t\n\r ]*```json[\t ]*\r?\n([\s\S]*?)\r?\n```[\t\n\r ]*$/;

function decodeUtf8(bytes, label) {
  try {
    return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch (error) {
    throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, `${label} is not valid UTF-8: ${error.message}`, { cause: error });
  }
}

function stableJsonValue(value) {
  if (Array.isArray(value)) return value.map(stableJsonValue);
  if (isPlainObject(value)) return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableJsonValue(value[key])]));
  return value;
}

export function canonicalJsonBytes(value) {
  return Buffer.from(`${JSON.stringify(stableJsonValue(value), null, 2)}\n`, 'utf8');
}

function parseResponseDocument(bytes, label) {
  const text = decodeUtf8(bytes, label);
  let body = text;
  let transport = RESPONSE_TRANSPORTS.RAW_JSON;
  const match = text.match(RESPONSE_JSON_FENCE);
  if (match) {
    body = match[1];
    transport = RESPONSE_TRANSPORTS.JSON_FENCE;
  }
  try {
    // JSON.parse enforces JSON ASCII whitespace; parseStrictJson additionally
    // rejects duplicates and overflowing/non-finite numbers.
    JSON.parse(body);
    const value = parseStrictJson(body, `${label} ${transport}`);
    validateUnicodeScalars(value);
    return { value, transport, normalizedBytes: Buffer.from(body, 'utf8') };
  } catch (error) {
    throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, error.message, { cause: error });
  }
}

function validateUnicodeScalars(value) {
  if (typeof value === 'string' && /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value)) throw new Error('response contains a lone Unicode surrogate');
  if (Array.isArray(value)) value.forEach(validateUnicodeScalars);
  else if (isPlainObject(value)) {
    for (const [key, item] of Object.entries(value)) { validateUnicodeScalars(key); validateUnicodeScalars(item); }
  }
}

function responseDigest(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function writeResponseEvidence(file, bytes) {
  ensureResponsePath(file);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  ensureResponsePath(file);
  try {
    fs.writeFileSync(file, bytes, { flag: 'wx', mode: 0o600 });
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
    ensureResponseFile(file, 'existing response evidence');
    if (!fs.readFileSync(file).equals(bytes)) throw new Error(`response evidence collision: ${file}`);
  }
}

function ensureResponsePath(file) {
  const absolute = path.resolve(file);
  let current = path.parse(absolute).root;
  for (const segment of absolute.slice(current.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, segment);
    let stats;
    try { stats = fs.lstatSync(current); } catch (error) {
      if (error.code === 'ENOENT') break;
      throw error;
    }
    if (stats.isSymbolicLink()) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, `response path contains a symlink: ${current}`);
  }
  return absolute;
}

function ensureResponseFile(file, label) {
  ensureResponsePath(file);
  const stats = fs.lstatSync(file);
  if (stats.isSymbolicLink()) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, `${label} is a symlink`);
  if (!stats.isFile()) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, `${label} is not a regular file`);
}

function validateHandoffShape(handoff, { expectedHandoff, orderId } = {}) {
  if (!isPlainObject(handoff)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'result.handoff must be an object');
  const required = ['version', 'schemaId', 'inReplyTo', 'senderRole', 'recipientRole'];
  const allowed = new Set([...required, 'objectiveId']);
  const unexpected = Object.keys(handoff).filter((key) => !allowed.has(key));
  if (unexpected.length) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, `result.handoff contains unexpected keys: ${unexpected.join(', ')}`);
  for (const field of required) {
    if (typeof handoff[field] !== 'string' || !handoff[field].trim()) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, `result.handoff.${field} must be a non-empty string`);
  }
  if (handoff.version !== 'AGENT_HANDOFF_V1' || handoff.schemaId !== AGENT_RESULT_VERSION) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'result.handoff version/schemaId is invalid');
  if (Object.hasOwn(handoff, 'objectiveId') && (typeof handoff.objectiveId !== 'string' || !handoff.objectiveId.trim())) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'result.handoff.objectiveId must be a non-empty string when present');
  if (orderId !== undefined && handoff.inReplyTo !== orderId) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'result.handoff.inReplyTo must match result.orderId', { expected: orderId, actual: handoff.inReplyTo });
  if (expectedHandoff !== undefined) {
    validateHandoffShape(expectedHandoff, { orderId });
    if (Object.keys(handoff).length !== Object.keys(expectedHandoff).length) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'result.handoff keys do not match expected handoff');
    for (const key of Object.keys(expectedHandoff)) {
      if (handoff[key] !== expectedHandoff[key]) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, `result.handoff.${key} does not match expected handoff`, { expected: expectedHandoff[key], actual: handoff[key] });
    }
  }
  return handoff;
}

export function validateAgentHandoff(result, options = {}) {
  if (!isPlainObject(result) || result.handoff === undefined) {
    if (options.expectedHandoff !== undefined) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'result.handoff is required by the order output contract');
    return null;
  }
  return validateHandoffShape(result.handoff, { ...options, orderId: options.orderId ?? result.orderId });
}

export function parseAgentResponseBytes(rawBytes, options = {}) {
  if (!Buffer.isBuffer(rawBytes) && !(rawBytes instanceof Uint8Array)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, 'response must be bytes');
  const bytes = Buffer.from(rawBytes);
  const parsed = parseResponseDocument(bytes, options.label || 'agent response');
  if (isPlainObject(parsed.value)) {
    if (parsed.value.status === 'refused' || (parsed.value.refusal !== undefined && parsed.value.refusal !== null && parsed.value.refusal !== false && parsed.value.refusal !== '')) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.REFUSED, 'provider returned a refusal');
    if (parsed.value.status === 'incomplete' || (parsed.value.incomplete_details !== undefined && parsed.value.incomplete_details !== null)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.INCOMPLETE, 'provider returned an incomplete response');
    if (Object.hasOwn(parsed.value, 'responseEnvelope')) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'responseEnvelope is controller-owned; use finalized-result verification');
  }
  validateAgentHandoff(parsed.value, { expectedHandoff: options.expectedHandoff, orderId: options.orderId });
  return { ...parsed, rawBytes: bytes, rawSha256: responseDigest(bytes), normalizedSha256: responseDigest(parsed.normalizedBytes) };
}

export function readAgentResponse(file, options = {}) {
  const resolved = path.resolve(String(file));
  ensureResponseFile(resolved, `response file ${resolved}`);
  const rawBytes = fs.readFileSync(resolved);
  const rawSha256 = responseDigest(rawBytes);
  const evidenceDir = path.resolve(options.evidenceDir || `${resolved}.responses`);
  const base = path.basename(resolved);
  const rawEvidencePath = path.join(evidenceDir, `${base}.${rawSha256}.raw.bin`);
  writeResponseEvidence(rawEvidencePath, rawBytes);
  let parsed;
  try {
    parsed = parseAgentResponseBytes(rawBytes, options);
  } catch (error) {
    if (error instanceof ResponseEnvelopeError) Object.assign(error, { rawEvidencePath, rawSha256 });
    throw error;
  }
  const normalizedCandidatePath = path.join(evidenceDir, `${base}.${rawSha256}.candidate.json`);
  const receiptPath = path.join(evidenceDir, `${base}.${rawSha256}.response-envelope.json`);
  writeResponseEvidence(normalizedCandidatePath, parsed.normalizedBytes);
  const envelope = {
    version: RESPONSE_ENVELOPE_VERSION,
    transport: parsed.transport,
    rawEvidencePath,
    rawSha256,
    rawBytes: rawBytes.length,
    normalizedCandidatePath,
    normalizedSha256: parsed.normalizedSha256,
    normalizedBytes: parsed.normalizedBytes.length
  };
  writeResponseEvidence(receiptPath, Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf8'));
  return { ...parsed, envelope, rawEvidencePath, normalizedCandidatePath, receiptPath, controlFiles: [rawEvidencePath, normalizedCandidatePath, receiptPath] };
}

export function validateResponseEnvelopeShape(envelope) {
  if (!isPlainObject(envelope)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'responseEnvelope must be an object');
  const keys = ['version', 'transport', 'rawEvidencePath', 'rawSha256', 'rawBytes', 'normalizedCandidatePath', 'normalizedSha256', 'normalizedBytes'];
  if (Object.keys(envelope).length !== keys.length || Object.keys(envelope).some((key) => !keys.includes(key))) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'responseEnvelope keys do not match AGENT_RESPONSE_ENVELOPE_V1');
  if (envelope.version !== RESPONSE_ENVELOPE_VERSION || !Object.values(RESPONSE_TRANSPORTS).includes(envelope.transport)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'responseEnvelope version/transport is invalid');
  for (const field of ['rawEvidencePath', 'normalizedCandidatePath']) {
    if (typeof envelope[field] !== 'string' || !path.isAbsolute(envelope[field])) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, `responseEnvelope.${field} must be an absolute path`);
  }
  for (const field of ['rawSha256', 'normalizedSha256']) {
    if (typeof envelope[field] !== 'string' || !/^[a-f0-9]{64}$/.test(envelope[field])) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, `responseEnvelope.${field} must be a lowercase SHA-256 digest`);
  }
  for (const field of ['rawBytes', 'normalizedBytes']) {
    if (!Number.isSafeInteger(envelope[field]) || envelope[field] < 0) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, `responseEnvelope.${field} must be a non-negative safe integer`);
  }
  return envelope;
}

export function verifyResponseEnvelope(result, options = {}) {
  const envelope = validateResponseEnvelopeShape(result?.responseEnvelope);
  if (path.resolve(envelope.rawEvidencePath) === path.resolve(envelope.normalizedCandidatePath)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'raw evidence and normalized candidate paths must be distinct');
  const roots = options.allowedEvidenceRoots;
  if (!Array.isArray(roots) || !roots.length) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.SCHEMA, 'finalized response verification requires controller evidence roots');
  for (const field of ['rawEvidencePath', 'normalizedCandidatePath']) {
    const file = path.resolve(envelope[field]);
    if (!roots.some((root) => {
      const relative = path.relative(path.resolve(root), file);
      return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
    })) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, `responseEnvelope.${field} escapes controller evidence roots`);
    ensureResponseFile(file, `responseEnvelope.${field}`);
  }
  const raw = fs.readFileSync(envelope.rawEvidencePath);
  const normalized = fs.readFileSync(envelope.normalizedCandidatePath);
  if (raw.length !== envelope.rawBytes || responseDigest(raw) !== envelope.rawSha256) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'responseEnvelope raw evidence digest/size mismatch');
  if (normalized.length !== envelope.normalizedBytes || responseDigest(normalized) !== envelope.normalizedSha256) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'responseEnvelope normalized candidate digest/size mismatch');
  const parsed = parseAgentResponseBytes(raw, options);
  if (parsed.transport !== envelope.transport || !parsed.normalizedBytes.equals(normalized)) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'responseEnvelope raw/normalized transport binding mismatch');
  const { responseEnvelope: _metadata, ...payload } = result;
  if (!canonicalJsonBytes(payload).equals(canonicalJsonBytes(parsed.value))) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'finalized result differs from normalized candidate');
  let receiptPath = null;
  const expectedReceipt = envelope.normalizedCandidatePath.replace(/\.candidate\.json$/, '.response-envelope.json');
  if (expectedReceipt !== envelope.normalizedCandidatePath && fs.existsSync(expectedReceipt)) {
    ensureResponseFile(expectedReceipt, 'response envelope receipt');
    const receipt = parseStrictJson(decodeUtf8(fs.readFileSync(expectedReceipt), 'response envelope receipt'));
    if (!canonicalJsonBytes(receipt).equals(canonicalJsonBytes(envelope))) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.IDENTITY, 'response envelope receipt does not match finalized metadata');
    receiptPath = expectedReceipt;
  }
  return { value: result, envelope, rawEvidencePath: envelope.rawEvidencePath, normalizedCandidatePath: envelope.normalizedCandidatePath, receiptPath, controlFiles: [envelope.rawEvidencePath, envelope.normalizedCandidatePath, ...(receiptPath ? [receiptPath] : [])] };
}

export function readFinalizedAgentResponse(file, options = {}) {
  const resolved = path.resolve(String(file));
  ensureResponseFile(resolved, `response file ${resolved}`);
  const raw = fs.readFileSync(resolved);
  let parsed;
  try { parsed = parseResponseDocument(raw, 'finalized agent result'); } catch {
    return readAgentResponse(resolved, options);
  }
  if (isPlainObject(parsed.value) && Object.hasOwn(parsed.value, 'responseEnvelope')) {
    try {
      if (parsed.transport !== RESPONSE_TRANSPORTS.RAW_JSON) throw new ResponseEnvelopeError(RESPONSE_ERROR_CODES.FORMAT, 'finalized responseEnvelope requires strict raw JSON');
      return verifyResponseEnvelope(parsed.value, options);
    } catch (error) {
      try { readAgentResponse(resolved, options); } catch (evidenceError) {
        error.rawEvidencePath = evidenceError.rawEvidencePath;
        error.rawSha256 = evidenceError.rawSha256;
      }
      throw error;
    }
  }
  return readAgentResponse(resolved, options);
}

export function validateArtifactBindings(result, options = {}) {
  const failures = [];
  for (const [index, item] of (Array.isArray(result?.artifacts) ? result.artifacts : []).entries()) {
    if (!isPlainObject(item)) continue;
    const required = options.expectedHandoff !== undefined && item.exists === true;
    if (!required && item.mediaType === undefined && item.sha256 === undefined) continue;
    if (typeof item.mediaType !== 'string' || !/^[A-Za-z0-9!#$&^_.+-]+\/[A-Za-z0-9!#$&^_.+-]+(?:[\t ]*;[^\r\n]*)?$/.test(item.mediaType)) failures.push(`result.artifacts[${index}].mediaType must be a media type`);
    if (typeof item.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(item.sha256)) failures.push(`result.artifacts[${index}].sha256 must be a lowercase SHA-256 digest`);
  }
  return failures;
}

export function verifyAgentArtifactFiles(result, workspace, options = {}) {
  const failures = validateArtifactBindings(result, options);
  for (const [index, item] of (Array.isArray(result?.artifacts) ? result.artifacts : []).entries()) {
    if (!isPlainObject(item) || item.exists !== true || typeof item.sha256 !== 'string' || typeof item.path !== 'string') continue;
    const file = path.resolve(workspace, item.path);
    const relative = path.relative(path.resolve(workspace), file);
    if (relative === '' || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
      failures.push(`result.artifacts[${index}].path escapes workspace`);
      continue;
    }
    try {
      ensureResponseFile(file, `result.artifacts[${index}].path`);
      if (responseDigest(fs.readFileSync(file)) !== item.sha256) failures.push(`result.artifacts[${index}].sha256 does not match file bytes`);
    } catch (error) {
      failures.push(`result.artifacts[${index}] verification failed: ${error.message}`);
    }
  }
  return failures;
}

const RESULT_STATUSES = new Set(['done', 'blocked']);
const PROOF_RESULTS = new Set(['passed', 'failed', 'not_run']);
const REVIEW_VERDICTS = new Set(['accepted', 'rejected', 'needs_changes', 'blocked']);
const REVIEW_SEVERITIES = new Set(['critical', 'warning', 'note']);
const AGENT_RESULT_EXECUTORS = new Set(['codex', 'claude', 'claudeFable', 'agy', 'hermes_delegate_task', 'other']);
const AGENT_RESULT_STATUSES = new Set(['done', 'blocked', 'failed']);
const AGENT_RESULT_FILE_ACTIONS = new Set(['added', 'modified', 'deleted', 'renamed', 'none']);
const AGENT_RESULT_PROOF_STATUSES = new Set(['pass', 'fail', 'not_run']);
const CANONICAL_LEGACY_FIELDS = new Set(['contractVersion', 'orderVersion', 'owner', 'selfReviewFixed', 'scopeViolations']);

export function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function requireString(failures, object, field, label) {
  if (typeof object[field] !== 'string' || !object[field].trim()) failures.push(`${label}.${field} must be a non-empty string`);
}

function requireStringArray(failures, object, field, label) {
  if (!Array.isArray(object[field])) {
    failures.push(`${label}.${field} must be an array`);
    return;
  }
  if (!object[field].every((item) => typeof item === 'string')) failures.push(`${label}.${field} must contain only strings`);
}

function optionalStringArray(failures, object, field, label) {
  if (object[field] === undefined) return;
  requireStringArray(failures, object, field, label);
}

export function validateLegionOrder(order) {
  const failures = [];
  if (!isPlainObject(order)) return ['order must be a JSON object'];

  if (order.orderVersion !== LEGION_ORDER_VERSION) failures.push(`order.orderVersion must be ${LEGION_ORDER_VERSION}`);
  for (const field of ['owner', 'executor', 'task', 'workspace', 'resultFile']) requireString(failures, order, field, 'order');
  for (const field of ['allowedPaths', 'nonGoals', 'proofCommands']) requireStringArray(failures, order, field, 'order');
  optionalStringArray(failures, order, 'forbiddenPatterns', 'order');
  optionalStringArray(failures, order, 'acceptanceCriteria', 'order');

  if (Array.isArray(order.allowedPaths) && !order.allowedPaths.length) failures.push('order.allowedPaths must include at least one path');
  if (Array.isArray(order.proofCommands) && !order.proofCommands.length) failures.push('order.proofCommands must include at least one command or explicit unavailable proof instruction');

  return failures;
}

export function validateDelegationResult(result, options = {}) {
  const {
    acceptedContractVersions = [LEGION_RESULT_VERSION],
    acceptedOrderVersions = [],
    actorLabel = 'agent',
    requireFilesChangedStrings = true,
    requireProofForDone = true,
    requirePassedProofForDone = true,
    requireSelfReviewForDone = true
  } = options;
  const failures = [];
  if (!isPlainObject(result)) return ['result must be a JSON object'];

  const hasContractVersion = typeof result.contractVersion === 'string';
  const hasOrderVersion = typeof result.orderVersion === 'string';
  if (hasContractVersion) {
    if (!acceptedContractVersions.includes(result.contractVersion)) {
      failures.push(`result.contractVersion must be one of: ${acceptedContractVersions.join(', ')}`);
    }
  } else if (hasOrderVersion) {
    const acceptedLegacy = acceptedOrderVersions.concat(acceptedContractVersions);
    if (!acceptedLegacy.includes(result.orderVersion)) failures.push(`result.orderVersion must be one of: ${acceptedLegacy.join(', ')}`);
  } else {
    failures.push('result.contractVersion or result.orderVersion must be present');
  }

  if (!RESULT_STATUSES.has(result.status)) failures.push('result.status must be done or blocked');
  if (!Array.isArray(result.filesChanged)) failures.push('result.filesChanged must be an array');
  else if (requireFilesChangedStrings && !result.filesChanged.every((item) => typeof item === 'string')) failures.push('result.filesChanged must contain only strings');

  if (!Array.isArray(result.proof)) failures.push('result.proof must be an array');
  else {
    result.proof.forEach((item, index) => {
      if (!isPlainObject(item)) {
        failures.push(`result.proof[${index}] must be an object`);
        return;
      }
      if (typeof item.command !== 'string' || !item.command.trim()) failures.push(`result.proof[${index}].command must be a non-empty string`);
      if (!PROOF_RESULTS.has(item.result)) failures.push(`result.proof[${index}].result must be passed, failed, or not_run`);
      if (typeof item.summary !== 'string') failures.push(`result.proof[${index}].summary must be a string`);
    });
  }

  if (!['yes', 'no'].includes(result.selfReviewFixed)) failures.push('result.selfReviewFixed must be yes or no');
  for (const field of ['scopeViolations', 'forbiddenPatternHits', 'remainingRisks']) requireStringArray(failures, result, field, 'result');

  if (result.status === 'done') {
    if (requireSelfReviewForDone && result.selfReviewFixed !== 'yes') failures.push('done result requires selfReviewFixed=yes');
    if (Array.isArray(result.proof)) {
      if (requireProofForDone && !result.proof.length) failures.push('done result requires at least one proof entry');
      if (requirePassedProofForDone) {
        const pendingProof = result.proof.filter((item) => item?.result !== 'passed');
        if (pendingProof.length) failures.push('done result requires every proof[].result to be passed');
      }
    }
    if (Array.isArray(result.scopeViolations) && result.scopeViolations.length) failures.push(`done result must not include ${actorLabel} scope violations`);
    if (Array.isArray(result.forbiddenPatternHits) && result.forbiddenPatternHits.length) failures.push(`done result must not include ${actorLabel} forbidden pattern hits`);
  }

  return failures;
}

function requireCanonicalIdentity(failures, result, field, expected) {
  if (typeof result[field] !== 'string' || !result[field].trim()) {
    failures.push(`result.${field} must be a non-empty string`);
    return;
  }
  if (field === 'orderId' && !SAFE_ORDER_ID_PATTERN.test(result[field])) failures.push('result.orderId must match 8-128 safe ASCII characters');
  if (expected !== undefined && result[field] !== expected) {
    failures.push(`result.${field} must match expected identity`);
  }
}

function requireCanonicalStringArray(failures, object, field, label) {
  if (!Array.isArray(object[field])) {
    failures.push(`${label}.${field} must be an array`);
    return;
  }
  if (!object[field].every((item) => typeof item === 'string')) {
    failures.push(`${label}.${field} must contain only strings`);
  }
}

function validateCanonicalFilesChanged(failures, result) {
  if (!Array.isArray(result.filesChanged)) {
    failures.push('result.filesChanged must be an array');
    return;
  }
  result.filesChanged.forEach((item, index) => {
    if (!isPlainObject(item)) {
      failures.push(`result.filesChanged[${index}] must be an object`);
      return;
    }
    if (typeof item.path !== 'string' || !item.path.trim()) failures.push(`result.filesChanged[${index}].path must be a non-empty string`);
    if (!AGENT_RESULT_FILE_ACTIONS.has(item.action)) failures.push(`result.filesChanged[${index}].action must be added, modified, deleted, renamed, or none`);
  });
}

function validateCanonicalArtifacts(failures, result) {
  if (!Array.isArray(result.artifacts)) {
    failures.push('result.artifacts must be an array');
    return;
  }
  result.artifacts.forEach((item, index) => {
    if (!isPlainObject(item)) {
      failures.push(`result.artifacts[${index}] must be an object`);
      return;
    }
    if (typeof item.path !== 'string' || !item.path.trim()) failures.push(`result.artifacts[${index}].path must be a non-empty string`);
    if (typeof item.exists !== 'boolean') failures.push(`result.artifacts[${index}].exists must be a boolean`);
    if (typeof item.type !== 'string') failures.push(`result.artifacts[${index}].type must be a string`);
    if (typeof item.note !== 'string') failures.push(`result.artifacts[${index}].note must be a string`);
  });
}

function validateCanonicalProof(failures, result) {
  if (!Array.isArray(result.proof)) {
    failures.push('result.proof must be an array');
    return;
  }
  result.proof.forEach((item, index) => {
    if (!isPlainObject(item)) {
      failures.push(`result.proof[${index}] must be an object`);
      return;
    }
    if (typeof item.command !== 'string' || !item.command.trim()) failures.push(`result.proof[${index}].command must be a non-empty string`);
    if (typeof item.cwd !== 'string' || !item.cwd.trim()) failures.push(`result.proof[${index}].cwd must be a non-empty string`);
    if (!AGENT_RESULT_PROOF_STATUSES.has(item.status)) failures.push(`result.proof[${index}].status must be pass, fail, or not_run`);
    if (!(item.exitCode === null || Number.isInteger(item.exitCode))) failures.push(`result.proof[${index}].exitCode must be an integer or null`);
    if (typeof item.summary !== 'string') failures.push(`result.proof[${index}].summary must be a string`);
  });
}

function validateCanonicalSelfReview(failures, result) {
  if (!isPlainObject(result.selfReview)) {
    failures.push('result.selfReview must be an object');
    return;
  }
  if (typeof result.selfReview.performed !== 'boolean') failures.push('result.selfReview.performed must be a boolean');
  requireCanonicalStringArray(failures, result.selfReview, 'findings', 'result.selfReview');
  requireCanonicalStringArray(failures, result.selfReview, 'fixesApplied', 'result.selfReview');
}

/**
 * Validate the canonical AGENT_RESULT_JSON_V1 result contract.
 * Optional identity fields reject a result that belongs to another order/run.
 */
export function validateAgentResult(result, options = {}) {
  const failures = [];
  if (!isPlainObject(result)) return ['result must be a JSON object'];

  const identity = options.expectedIdentity || options.identity || {};
  const expectedOrderId = options.expectedOrderId ?? options.orderId ?? identity.orderId;
  const expectedExecutor = options.expectedExecutor ?? options.executor ?? identity.executor;
  const expectedStatus = options.expectedStatus ?? options.status ?? identity.status;

  if (result.resultVersion !== AGENT_RESULT_VERSION) failures.push(`result.resultVersion must be ${AGENT_RESULT_VERSION}`);
  const legacyFields = [...CANONICAL_LEGACY_FIELDS].filter((field) => Object.prototype.hasOwnProperty.call(result, field));
  if (legacyFields.length) failures.push(`result must not include legacy fields: ${legacyFields.join(', ')}`);
  requireCanonicalIdentity(failures, result, 'orderId', expectedOrderId);
  if (!AGENT_RESULT_EXECUTORS.has(result.executor)) failures.push('result.executor must be codex, claude, claudeFable, agy, hermes_delegate_task, or other');
  else if (expectedExecutor !== undefined && result.executor !== expectedExecutor) failures.push('result.executor must match expected identity');
  if (!AGENT_RESULT_STATUSES.has(result.status)) failures.push('result.status must be done, blocked, or failed');
  else if (expectedStatus !== undefined && result.status !== expectedStatus) failures.push('result.status must match expected identity');
  if (typeof result.summary !== 'string') failures.push('result.summary must be a string');

  validateCanonicalFilesChanged(failures, result);
  validateCanonicalArtifacts(failures, result);
  validateCanonicalProof(failures, result);
  if (Array.isArray(result.proof) && result.proof.some((item) => isPlainObject(item) && Object.prototype.hasOwnProperty.call(item, 'result'))) {
    failures.push('result.proof must not include legacy result fields');
  }
  validateCanonicalSelfReview(failures, result);

  for (const field of ['scopeDeviations', 'forbiddenPatternHits', 'remainingRisks', 'questions', 'errors']) {
    requireCanonicalStringArray(failures, result, field, 'result');
  }
  if (typeof result.stdoutSummary !== 'string') failures.push('result.stdoutSummary must be a string');
  if (typeof result.stderrSummary !== 'string') failures.push('result.stderrSummary must be a string');
  if (result.executorExtensions !== undefined && !isPlainObject(result.executorExtensions)) failures.push('result.executorExtensions must be an object');
  failures.push(...validateArtifactBindings(result, options));
  if (result.responseEnvelope !== undefined) {
    try { validateResponseEnvelopeShape(result.responseEnvelope); } catch (error) { failures.push(error.message); }
  }
  if (options.expectedHandoff !== undefined || result.handoff !== undefined) {
    try {
      validateAgentHandoff(result, { expectedHandoff: options.expectedHandoff, orderId: expectedOrderId ?? result.orderId });
    } catch (error) {
      failures.push(error.message);
    }
  }

  if (result.status === 'done') {
    if (!Array.isArray(result.proof) || !result.proof.length) failures.push('done result requires at least one proof entry');
    else if (result.proof.some((item) => item?.status !== 'pass')) failures.push('done result requires every proof[].status to be pass');
    if (result.selfReview?.performed !== true) failures.push('done result requires selfReview.performed=true');
    if (Array.isArray(result.scopeDeviations) && result.scopeDeviations.length) failures.push('done result must not include scope deviations');
    if (Array.isArray(result.forbiddenPatternHits) && result.forbiddenPatternHits.length) failures.push('done result must not include forbidden pattern hits');
  }

  return failures;
}

export const validateCanonicalAgentResult = validateAgentResult;
export const validateCanonicalResult = validateAgentResult;

export function validateLegionReview(review) {
  const failures = [];
  if (!isPlainObject(review)) return ['review must be a JSON object'];

  if (review.reviewVersion !== LEGION_REVIEW_VERSION) failures.push(`review.reviewVersion must be ${LEGION_REVIEW_VERSION}`);
  for (const field of ['reviewer', 'targetExecutor', 'targetResultFile', 'verdict', 'summary']) requireString(failures, review, field, 'review');
  if (typeof review.verdict === 'string' && !REVIEW_VERDICTS.has(review.verdict)) failures.push('review.verdict must be accepted, rejected, needs_changes, or blocked');
  requireStringArray(failures, review, 'proofReviewed', 'review');
  requireStringArray(failures, review, 'requiredFixes', 'review');
  requireStringArray(failures, review, 'remainingRisks', 'review');

  if (!Array.isArray(review.findings)) failures.push('review.findings must be an array');
  else {
    review.findings.forEach((finding, index) => {
      if (!isPlainObject(finding)) {
        failures.push(`review.findings[${index}] must be an object`);
        return;
      }
      if (!REVIEW_SEVERITIES.has(finding.severity)) failures.push(`review.findings[${index}].severity must be critical, warning, or note`);
      for (const field of ['title', 'evidence', 'recommendation']) {
        if (typeof finding[field] !== 'string') failures.push(`review.findings[${index}].${field} must be a string`);
      }
    });
  }

  if (review.verdict === 'accepted' && Array.isArray(review.requiredFixes) && review.requiredFixes.length) {
    failures.push('accepted review must not include requiredFixes');
  }

  return failures;
}
