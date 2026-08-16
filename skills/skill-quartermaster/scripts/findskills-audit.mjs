#!/usr/bin/env node

const API_BASE = 'https://findskills.org/api/v1';

const args = process.argv.slice(2);
const queryParts = [];
let limit = 10;
let skillId = '';

for (let i = 0; i < args.length; i += 1) {
  const arg = args[i];
  if (arg === '--limit') {
    const next = Number(args[i + 1]);
    if (Number.isInteger(next) && next > 0) limit = Math.min(next, 50);
    i += 1;
  } else if (arg === '--id') {
    skillId = String(args[i + 1] || '').trim();
    i += 1;
  } else {
    queryParts.push(arg);
  }
}

const query = queryParts.join(' ').trim();

if (!query && !skillId) {
  console.error('Usage: findskills-audit.mjs "<query>" [--limit 10]');
  console.error('   or: findskills-audit.mjs --id <skill-id>');
  process.exit(2);
}

const key = process.env.FINDSKILLS_API_KEY || process.env.FINDSKILLS_KEY || '';

function headers() {
  return key ? { Authorization: `Bearer ${key}` } : {};
}

async function getJson(url) {
  const response = await fetch(url, { headers: headers() });
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response from ${url}: ${text.slice(0, 200)}`);
  }
  if (!response.ok) {
    const message = data.error || response.statusText;
    throw new Error(`${response.status} ${message}`);
  }
  return { data, response };
}

function auditText(candidate) {
  const body = [
    candidate.name,
    candidate.description,
    candidate.skill_md,
    JSON.stringify(candidate.openapi_spec || {}),
  ]
    .filter(Boolean)
    .join('\n');

  const blockers = [];
  const warnings = [];

  const checks = [
    [/base64\s+-d\s*\|\s*(bash|sh)/i, 'encoded shell payload'],
    [/(curl|wget)[^|;&]*\|\s*(bash|sh)/i, 'remote shell pipe'],
    [/\bsudo\b/i, 'privileged command'],
    [/\beval\s*\(/i, 'dynamic eval'],
    [/\bchmod\s+777\b/i, 'world-writable permissions'],
    [/\brm\s+-rf\s+(\/|\$HOME|~)/i, 'destructive delete'],
    [/(API[_-]?KEY|SECRET|PASSWORD|PRIVATE[_-]?KEY)/i, 'secret handling'],
  ];

  for (const [pattern, label] of checks) {
    if (pattern.test(body)) blockers.push(label);
  }

  if (!candidate.skill_md) warnings.push('no skill_md in registry detail');
  if (!candidate.url && !candidate.source) warnings.push('source hidden or unavailable');
  if (candidate.safety?.safety_label === 'caution' || candidate.safety_label === 'caution') {
    warnings.push('registry safety_label=caution');
  }

  return {
    blockers: [...new Set(blockers)],
    warnings: [...new Set(warnings)],
  };
}

async function main() {
  if (skillId) {
    const { data: detail } = await getJson(`${API_BASE}/skills/${encodeURIComponent(skillId)}`);
    const audit = auditText(detail);
    const verdict = audit.blockers.length
      ? 'blocked'
      : audit.warnings.length
        ? 'needs-review'
        : 'candidate';

    console.log(JSON.stringify({
      id: skillId,
      authenticated: Boolean(key),
      result: {
        id: detail.id,
        name: detail.name,
        category: detail.category,
        safety_label: detail.safety?.safety_label || detail.safety_label,
        quality_tier: detail.quality?.quality_tier,
        url: detail.url,
        source: detail.source,
        verdict,
        blockers: audit.blockers,
        warnings: audit.warnings,
        description: detail.description,
      },
    }, null, 2));
    return;
  }

  const searchUrl = `${API_BASE}/search?q=${encodeURIComponent(query)}&limit=${limit}`;
  const { data: search } = await getJson(searchUrl);
  const skills = Array.isArray(search.skills) ? search.skills : [];

  const results = [];
  for (const item of skills) {
    let detail = item;
    if (item.id) {
      try {
        const { data } = await getJson(`${API_BASE}/skills/${encodeURIComponent(item.id)}`);
        detail = { ...item, ...data };
      } catch (error) {
        detail = { ...item, detail_error: error.message };
      }
    }

    const audit = auditText(detail);
    const verdict = audit.blockers.length
      ? 'blocked'
      : audit.warnings.length
        ? 'needs-review'
        : 'candidate';

    results.push({
      id: detail.id,
      name: detail.name,
      category: detail.category,
      safety_label: detail.safety?.safety_label || detail.safety_label,
      quality_tier: detail.quality?.quality_tier,
      url: detail.url,
      source: detail.source,
      verdict,
      blockers: audit.blockers,
      warnings: audit.warnings,
      description: detail.description,
    });
  }

  console.log(JSON.stringify({
    query,
    total: search.total,
    limit,
    authenticated: Boolean(key),
    results,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
