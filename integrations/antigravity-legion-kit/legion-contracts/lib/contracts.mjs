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
    return JSON.parse(token);
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
