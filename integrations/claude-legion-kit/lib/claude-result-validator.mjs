const RESULT_STATUSES = new Set(['done', 'blocked']);
const PROOF_RESULTS = new Set(['passed', 'failed', 'not_run']);
const CANONICAL_RESULT_STATUSES = new Set(['done', 'blocked', 'failed']);
const CANONICAL_PROOF_STATUSES = new Set(['pass', 'fail', 'not_run']);
const FILE_ACTIONS = new Set(['added', 'modified', 'deleted', 'renamed', 'none']);
const EXECUTORS = new Set(['codex', 'claude', 'claudeFable', 'agy', 'hermes_delegate_task', 'other']);
const CANONICAL_FIELDS = [
  'resultVersion', 'orderId', 'executor', 'status', 'summary', 'filesChanged', 'artifacts', 'proof',
  'selfReview', 'scopeDeviations', 'forbiddenPatternHits', 'remainingRisks', 'questions', 'errors',
  'stdoutSummary', 'stderrSummary'
];
const LEGACY_ONLY_FIELDS = ['contractVersion', 'orderVersion', 'owner', 'selfReviewFixed', 'scopeViolations'];
const SAFE_ORDER_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/;

export function parseStrictJson(text, label = 'JSON') {
  if (typeof text !== 'string') throw new TypeError(`${label} must be text`);
  let index = 0;
  const whitespace = () => { while (index < text.length && /\s/.test(text[index])) index += 1; };
  const parseString = () => {
    const start = index;
    if (text[index] !== '"') throw new Error(`${label} expected string at ${index}`);
    index += 1;
    while (index < text.length) {
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
    while (index < text.length && !/[\s,\]}]/.test(text[index])) index += 1;
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
    while (index < text.length) {
      whitespace();
      const key = parseString();
      if (keys.has(key)) throw new Error(`${label} duplicate key ${JSON.stringify(key)}`);
      keys.add(key);
      whitespace();
      if (text[index++] !== ':') throw new Error(`${label} expected ':' at ${index - 1}`);
      value[key] = parseValue();
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
    while (index < text.length) {
      value.push(parseValue());
      whitespace();
      if (text[index] === ']') { index += 1; return value; }
      if (text[index++] !== ',') throw new Error(`${label} expected ',' at ${index - 1}`);
    }
    throw new Error(`${label} unterminated array`);
  };
  const value = parseValue();
  whitespace();
  if (index !== text.length) throw new Error(`${label} trailing data at ${index}`);
  return value;
}

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

function requireCanonicalArray(failures, result, field, validateItem) {
  if (!Array.isArray(result[field])) {
    failures.push(`result.${field} must be an array`);
    return;
  }
  result[field].forEach((item, index) => validateItem(item, index));
}

export function validateCanonicalAgentResult(result, options = {}) {
  const identity = options.expectedIdentity || options.identity || {};
  const expectedOrderId = options.expectedOrderId ?? options.orderId ?? identity.orderId;
  const expectedExecutor = options.expectedExecutor ?? options.executor ?? identity.executor;
  const expectedStatus = options.expectedStatus ?? options.status ?? identity.status;
  const failures = [];
  if (!isPlainObject(result)) return ['result must be a JSON object'];

  for (const field of CANONICAL_FIELDS) {
    if (!Object.hasOwn(result, field)) failures.push(`result.${field} is required`);
  }
  for (const field of LEGACY_ONLY_FIELDS) {
    if (Object.hasOwn(result, field)) failures.push(`result.${field} is legacy-only and not allowed in canonical mode`);
  }

  if (result.resultVersion !== 'AGENT_RESULT_JSON_V1') failures.push('result.resultVersion must be AGENT_RESULT_JSON_V1');
  if (typeof result.orderId !== 'string' || !SAFE_ORDER_ID_PATTERN.test(result.orderId)) failures.push('result.orderId must match 8-128 safe ASCII characters');
  if (expectedOrderId !== undefined && result.orderId !== expectedOrderId) failures.push(`result.orderId must match expected orderId: ${expectedOrderId}`);
  if (!EXECUTORS.has(result.executor)) failures.push(`result.executor must be one of: ${[...EXECUTORS].join(', ')}`);
  if (expectedExecutor !== undefined && result.executor !== expectedExecutor) failures.push(`result.executor must match expected executor: ${expectedExecutor}`);
  if (!CANONICAL_RESULT_STATUSES.has(result.status)) failures.push('result.status must be done, blocked, or failed');
  if (expectedStatus !== undefined && result.status !== expectedStatus) failures.push(`result.status must match expected status: ${expectedStatus}`);
  if (typeof result.summary !== 'string') failures.push('result.summary must be a string');

  requireCanonicalArray(failures, result, 'filesChanged', (item, index) => {
    if (!isPlainObject(item)) {
      failures.push(`result.filesChanged[${index}] must be an object`);
      return;
    }
    requireString(failures, item, 'path', `result.filesChanged[${index}]`);
    if (!FILE_ACTIONS.has(item.action)) failures.push(`result.filesChanged[${index}].action must be added, modified, deleted, renamed, or none`);
  });

  requireCanonicalArray(failures, result, 'artifacts', (item, index) => {
    if (!isPlainObject(item)) {
      failures.push(`result.artifacts[${index}] must be an object`);
      return;
    }
    requireString(failures, item, 'path', `result.artifacts[${index}]`);
    if (typeof item.exists !== 'boolean') failures.push(`result.artifacts[${index}].exists must be a boolean`);
    if (typeof item.type !== 'string') failures.push(`result.artifacts[${index}].type must be a string`);
    if (typeof item.note !== 'string') failures.push(`result.artifacts[${index}].note must be a string`);
  });

  requireCanonicalArray(failures, result, 'proof', (item, index) => {
    if (!isPlainObject(item)) {
      failures.push(`result.proof[${index}] must be an object`);
      return;
    }
    requireString(failures, item, 'command', `result.proof[${index}]`);
    requireString(failures, item, 'cwd', `result.proof[${index}]`);
    if (!CANONICAL_PROOF_STATUSES.has(item.status)) failures.push(`result.proof[${index}].status must be pass, fail, or not_run`);
    if (!(item.exitCode === null || Number.isInteger(item.exitCode))) failures.push(`result.proof[${index}].exitCode must be an integer or null`);
    if (typeof item.summary !== 'string') failures.push(`result.proof[${index}].summary must be a string`);
    if (Object.hasOwn(item, 'result')) failures.push(`result.proof[${index}].result is legacy-only and not allowed in canonical mode`);
  });

  if (!isPlainObject(result.selfReview)) failures.push('result.selfReview must be an object');
  else {
    if (typeof result.selfReview.performed !== 'boolean') failures.push('result.selfReview.performed must be a boolean');
    requireStringArray(failures, result.selfReview, 'findings', 'result.selfReview');
    requireStringArray(failures, result.selfReview, 'fixesApplied', 'result.selfReview');
  }

  for (const field of ['scopeDeviations', 'forbiddenPatternHits', 'remainingRisks', 'questions', 'errors']) {
    requireStringArray(failures, result, field, 'result');
  }
  for (const field of ['stdoutSummary', 'stderrSummary']) {
    if (typeof result[field] !== 'string') failures.push(`result.${field} must be a string`);
  }
  if (result.executorExtensions !== undefined && !isPlainObject(result.executorExtensions)) failures.push('result.executorExtensions must be an object');

  if (result.status === 'done') {
    if (Array.isArray(result.proof) && !result.proof.length) failures.push('done result requires at least one proof entry');
    if (Array.isArray(result.proof) && result.proof.some((item) => item?.status !== 'pass')) failures.push('done result requires every proof[].status to be pass');
    if (result.selfReview?.performed !== true) failures.push('done result requires selfReview.performed=true');
    if (Array.isArray(result.scopeDeviations) && result.scopeDeviations.length) failures.push('done result must not include scope deviations');
    if (Array.isArray(result.forbiddenPatternHits) && result.forbiddenPatternHits.length) failures.push('done result must not include forbidden pattern hits');
  }
  return failures;
}

export const validateAgentResult = validateCanonicalAgentResult;
export const validateCanonicalResult = validateCanonicalAgentResult;

export function validateDelegationResult(result, options = {}) {
  const {
    acceptedContractVersions = ['LEGION_RESULT_V1'],
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
    if (!acceptedContractVersions.includes(result.contractVersion)) failures.push(`result.contractVersion must be one of: ${acceptedContractVersions.join(', ')}`);
  } else if (hasOrderVersion) {
    const acceptedLegacy = acceptedOrderVersions.concat(acceptedContractVersions);
    if (!acceptedLegacy.includes(result.orderVersion)) failures.push(`result.orderVersion must be one of: ${acceptedLegacy.join(', ')}`);
  } else failures.push('result.contractVersion or result.orderVersion must be present');

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
      if (requirePassedProofForDone && result.proof.some((item) => item?.result !== 'passed')) failures.push('done result requires every proof[].result to be passed');
    }
    if (Array.isArray(result.scopeViolations) && result.scopeViolations.length) failures.push(`done result must not include ${actorLabel} scope violations`);
    if (Array.isArray(result.forbiddenPatternHits) && result.forbiddenPatternHits.length) failures.push(`done result must not include ${actorLabel} forbidden pattern hits`);
  }

  return failures;
}
