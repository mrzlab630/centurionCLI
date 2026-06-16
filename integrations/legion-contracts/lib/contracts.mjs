export const LEGION_ORDER_VERSION = 'LEGION_ORDER_V1';
export const LEGION_RESULT_VERSION = 'LEGION_RESULT_V1';
export const LEGION_REVIEW_VERSION = 'LEGION_REVIEW_V1';

const RESULT_STATUSES = new Set(['done', 'blocked']);
const PROOF_RESULTS = new Set(['passed', 'failed', 'not_run']);
const REVIEW_VERDICTS = new Set(['accepted', 'rejected', 'needs_changes', 'blocked']);
const REVIEW_SEVERITIES = new Set(['critical', 'warning', 'note']);

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
