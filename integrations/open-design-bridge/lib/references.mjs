import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { isIP } from 'node:net';
import { lookup } from 'node:dns/promises';
import https from 'node:https';
import { assertPathWithinRoot, isWithinPath } from './path-safety.mjs';
import { AnchoredRoot } from './descriptor-fs.mjs';

export const REFERENCE_REQUEST_VERSION = 'CENTURION_REFERENCE_REQUEST_V1';
export const REFERENCE_RESULT_VERSION = 'CENTURION_REFERENCE_RESULT_V1';
export const REFERENCE_MANIFEST_VERSION = 'CENTURION_REFERENCE_MANIFEST_V1';

const DEFAULT_SOURCES = Object.freeze(['shadcn', 'magicui', 'hyperui', 'tabler', 'landbook']);
const SOURCE_SET = new Set(DEFAULT_SOURCES);
const STRATEGIES = new Set(['compose', 'adapt', 'inspire']);
const MAX_RESPONSE_BYTES = 4 * 1024 * 1024;
const MAX_SNIPPET_BYTES = 48 * 1024;
const MAX_REDIRECTS = 5;
const WORD_ALIASES = Object.freeze({
  analytics: ['dashboard', 'chart', 'data', 'stats', 'table', 'metrics'],
  landing: ['hero', 'pricing', 'features', 'testimonial', 'call-to-action', 'marketing'],
  ecommerce: ['store', 'shop', 'product', 'cart', 'checkout'],
  authentication: ['auth', 'login', 'sign-in', 'signup', 'sign-up'],
  b2b: ['business', 'saas', 'enterprise', 'wholesale'],
  portfolio: ['case-study', 'projects', 'work'],
  settings: ['preferences', 'account', 'profile'],
  motion: ['animated', 'animation', 'marquee', 'beam', 'video'],
  лендинг: ['landing', 'hero', 'pricing', 'features', 'marketing'],
  аналитика: ['analytics', 'dashboard', 'chart', 'metrics', 'data'],
  дашборд: ['dashboard', 'chart', 'table', 'application'],
  магазин: ['ecommerce', 'store', 'shop', 'product', 'checkout'],
  авторизация: ['authentication', 'auth', 'login', 'sign-in'],
  портфолио: ['portfolio', 'case-study', 'projects'],
  настройки: ['settings', 'preferences', 'account', 'profile'],
  анимация: ['motion', 'animated', 'animation', 'marquee'],
  саас: ['saas', 'b2b', 'business', 'enterprise']
});

const SOURCE_DEFINITIONS = Object.freeze({
  shadcn: {
    label: 'shadcn/ui',
    policy: 'import-and-adapt',
    license: 'MIT',
    catalogUrl: 'https://raw.githubusercontent.com/shadcn-ui/ui/main/apps/v4/registry.json',
    homepage: 'https://ui.shadcn.com',
    allowedOrigins: ['https://raw.githubusercontent.com']
  },
  magicui: {
    label: 'Magic UI',
    policy: 'import-and-adapt',
    license: 'MIT',
    catalogUrl: 'https://raw.githubusercontent.com/magicuidesign/magicui/main/apps/www/public/r/registry.json',
    homepage: 'https://magicui.design',
    allowedOrigins: ['https://raw.githubusercontent.com']
  },
  hyperui: {
    label: 'HyperUI',
    policy: 'import-and-adapt',
    license: 'MIT',
    catalogUrl: 'https://api.github.com/repos/markmead/hyperui/git/trees/main?recursive=1',
    homepage: 'https://www.hyperui.dev',
    allowedOrigins: ['https://api.github.com', 'https://raw.githubusercontent.com']
  },
  tabler: {
    label: 'Tabler',
    policy: 'import-and-adapt',
    license: 'MIT',
    catalogUrl: 'https://preview.tabler.io/sitemap.xml',
    homepage: 'https://tabler.io',
    allowedOrigins: ['https://preview.tabler.io']
  },
  landbook: {
    label: 'Landbook',
    policy: 'inspire-only',
    license: 'reference-only',
    catalogUrl: 'https://land-book.com/rss.xml',
    homepage: 'https://land-book.com',
    allowedOrigins: ['https://land-book.com']
  }
});

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isPrivateAddress(address) {
  const value = String(address).toLowerCase();
  if (value === '::1' || value === '::' || value.startsWith('fe80:') || value.startsWith('fc') || value.startsWith('fd')) return true;
  const mapped = value.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/)?.[1];
  const ipv4 = mapped || (isIP(value) === 4 ? value : null);
  if (!ipv4) return false;
  const [a, b] = ipv4.split('.').map(Number);
  return a === 0 || a === 10 || a === 127 || a >= 224
    || (a === 100 && b >= 64 && b <= 127)
    || (a === 169 && b === 254)
    || (a === 172 && b >= 16 && b <= 31)
    || (a === 192 && b === 0)
    || (a === 192 && b === 168)
    || (a === 198 && (b === 18 || b === 19));
}

function createSearchId() {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
  return `ref-${stamp}-${crypto.randomUUID().slice(0, 8)}`;
}

function tokens(value) {
  return [...new Set(String(value ?? '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .split(/\s+/)
    .filter((token) => token.length > 1))];
}

function expandedTokens(request) {
  const base = tokens([request.query, request.artifactType, request.platform].filter(Boolean).join(' '));
  return [...new Set(base.flatMap((token) => [token, ...(WORD_ALIASES[token] ?? [])]))];
}

function normalizeId(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
}

function scoreCandidate(candidate, queryTokens) {
  const haystack = `${candidate.title} ${candidate.description ?? ''} ${(candidate.tags ?? []).join(' ')} ${candidate.sourcePath ?? ''}`.toLowerCase();
  let score = 0;
  const reasons = [];
  for (const token of queryTokens) {
    if (!haystack.includes(token)) continue;
    const weight = candidate.title.toLowerCase().includes(token) ? 5 : 2;
    score += weight;
    reasons.push(token);
  }
  if (candidate.kind === 'page' || candidate.kind === 'block') score += 1;
  return { ...candidate, score, matchReasons: [...new Set(reasons)] };
}

function decodeXml(value) {
  return String(value)
    .replaceAll('&amp;', '&')
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>')
    .replaceAll('&quot;', '"')
    .replaceAll('&#39;', "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)));
}

async function fetchText(url, options) {
  let currentUrl = new URL(url);
  let response;
  for (let redirect = 0; redirect <= MAX_REDIRECTS; redirect += 1) {
    const verifiedAddresses = await assertAllowedNetworkUrl(currentUrl, options);
    response = options.pinnedHttps
      ? await pinnedHttpsResponse(currentUrl, verifiedAddresses, options.timeoutMs)
      : await options.fetcher(currentUrl.href, {
          headers: { 'user-agent': 'CENTURION-Open-Design-Bridge/0.2' },
          redirect: 'manual',
          signal: AbortSignal.timeout(options.timeoutMs)
        });
    if (![301, 302, 303, 307, 308].includes(response.status)) break;
    const location = response.headers.get('location');
    if (!location) throw new Error(`redirect ${response.status} omitted location`);
    currentUrl = new URL(location, currentUrl);
    if (redirect === MAX_REDIRECTS) throw new Error(`redirect limit exceeded: ${url}`);
  }
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  const length = Number(response.headers.get('content-length') ?? 0);
  if (length > MAX_RESPONSE_BYTES) throw new Error(`response exceeds ${MAX_RESPONSE_BYTES} bytes`);
  const buffer = Buffer.from(await response.arrayBuffer());
  if (buffer.length > MAX_RESPONSE_BYTES) throw new Error(`response exceeds ${MAX_RESPONSE_BYTES} bytes`);
  return buffer.toString('utf8');
}

async function assertAllowedNetworkUrl(url, options) {
  if (url.protocol !== 'https:' || !options.allowedOrigins.includes(url.origin)) {
    throw new Error(`URL origin is not allowed for ${options.source}: ${url.href}`);
  }
  const addresses = isIP(url.hostname)
    ? [{ address: url.hostname }]
    : await options.lookup(url.hostname, { all: true, verbatim: true });
  if (addresses.length === 0 || addresses.some(({ address }) => isPrivateAddress(address))) {
    throw new Error(`URL resolves to a private or unavailable address: ${url.hostname}`);
  }
  return addresses;
}

function pinnedHttpsResponse(url, addresses, timeoutMs) {
  return new Promise((resolve, reject) => {
    const selected = addresses[0];
    const request = https.request(url, {
      method: 'GET',
      headers: { 'user-agent': 'CENTURION-Open-Design-Bridge/0.2' },
      servername: url.hostname,
      lookup(_hostname, _options, callback) {
        callback(null, selected.address, selected.family);
      }
    }, (response) => {
      const chunks = [];
      let bytes = 0;
      response.on('data', (chunk) => {
        bytes += chunk.length;
        if (bytes > MAX_RESPONSE_BYTES) request.destroy(new Error(`response exceeds ${MAX_RESPONSE_BYTES} bytes`));
        else chunks.push(chunk);
      });
      response.on('end', () => {
        const buffer = Buffer.concat(chunks);
        resolve({
          ok: response.statusCode >= 200 && response.statusCode < 300,
          status: response.statusCode,
          statusText: response.statusMessage ?? '',
          headers: { get: (name) => response.headers[String(name).toLowerCase()] ?? null },
          arrayBuffer: async () => buffer
        });
      });
    });
    request.setTimeout(timeoutMs, () => request.destroy(new Error(`request timed out after ${timeoutMs}ms`)));
    request.on('error', reject);
    request.end();
  });
}

async function fetchJson(url, options) {
  return JSON.parse(await fetchText(url, options));
}

function githubRaw(repository, sourcePath) {
  return `https://raw.githubusercontent.com/${repository}/main/${sourcePath}`;
}

async function searchRegistrySource(source, request, options) {
  const definition = SOURCE_DEFINITIONS[source];
  const registry = await fetchJson(definition.catalogUrl, options);
  const items = Array.isArray(registry.items) ? registry.items : [];
  const repository = source === 'shadcn' ? 'shadcn-ui/ui' : 'magicuidesign/magicui';
  return items
    .filter((item) => item && item.name && item.type !== 'registry:style' && item.type !== 'registry:internal')
    .map((item) => {
      const sourcePath = item.files?.find((file) => typeof file.path === 'string')?.path ?? null;
      const kind = item.type === 'registry:block' ? 'block' : item.type === 'registry:example' ? 'example' : 'component';
      return {
        id: `${source}:${item.name}`,
        source,
        title: item.title || item.name.replaceAll('-', ' '),
        description: item.description || `${definition.label} ${kind}`,
        kind,
        tags: [...(item.categories ?? []), item.type, ...(item.registryDependencies ?? [])],
        sourceUrl: sourcePath ? githubRaw(repository, sourcePath) : definition.homepage,
        attributionUrl: definition.homepage,
        sourcePath,
        snippetUrl: sourcePath ? githubRaw(repository, sourcePath) : null,
        policy: definition.policy,
        license: definition.license
      };
    });
}

async function searchHyperUi(request, options) {
  const definition = SOURCE_DEFINITIONS.hyperui;
  const tree = await fetchJson(definition.catalogUrl, options);
  const paths = Array.isArray(tree.tree) ? tree.tree : [];
  return paths
    .filter((entry) => entry.type === 'blob' && /^public\/examples\/.+\.html$/.test(entry.path))
    .map((entry) => {
      const segments = entry.path.split('/');
      const category = segments.at(-2) ?? 'component';
      const variant = path.basename(entry.path, '.html');
      return {
        id: `hyperui:${normalizeId(`${segments.at(-3)}-${category}-${variant}`)}`,
        source: 'hyperui',
        title: `HyperUI ${category.replaceAll('-', ' ')} ${variant}`,
        description: `HTML/Tailwind ${category.replaceAll('-', ' ')} example`,
        kind: 'block',
        tags: [segments.at(-3), category, variant, 'html', 'tailwind'],
        sourceUrl: githubRaw('markmead/hyperui', entry.path),
        attributionUrl: definition.homepage,
        sourcePath: entry.path,
        snippetUrl: githubRaw('markmead/hyperui', entry.path),
        policy: definition.policy,
        license: definition.license
      };
    });
}

async function searchTabler(request, options) {
  const definition = SOURCE_DEFINITIONS.tabler;
  const xml = await fetchText(definition.catalogUrl, options);
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => {
    const sourceUrl = decodeXml(match[1]);
    assertSourceUrl(sourceUrl, definition);
    const slug = path.basename(new URL(sourceUrl).pathname, '.html');
    return {
      id: `tabler:${normalizeId(slug)}`,
      source: 'tabler',
      title: `Tabler ${slug.replaceAll('-', ' ')}`,
      description: 'Responsive Bootstrap application page reference',
      kind: 'page',
      tags: [slug, 'dashboard', 'bootstrap', 'application'],
      sourceUrl,
      attributionUrl: definition.homepage,
      sourcePath: null,
      snippetUrl: sourceUrl,
      policy: definition.policy,
      license: definition.license
    };
  });
}

async function searchLandbook(request, options) {
  const definition = SOURCE_DEFINITIONS.landbook;
  const xml = await fetchText(definition.catalogUrl, options);
  return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((itemMatch) => {
    const body = itemMatch[1];
    const title = decodeXml(body.match(/<title>([\s\S]*?)<\/title>/)?.[1]?.trim() ?? 'Landbook reference');
    const sourceUrl = decodeXml(body.match(/<link>([^<]+)<\/link>/)?.[1]?.trim() ?? definition.homepage);
    assertSourceUrl(sourceUrl, definition);
    const imageUrl = decodeXml(body.match(/<img[^>]+src="([^"]+)"/i)?.[1] ?? '');
    const slug = path.basename(new URL(sourceUrl).pathname);
    return {
      id: `landbook:${normalizeId(slug || title)}`,
      source: 'landbook',
      title,
      description: 'Human-curated website design inspiration',
      kind: 'inspiration',
      tags: tokens(title),
      sourceUrl,
      previewImageUrl: imageUrl || null,
      attributionUrl: sourceUrl,
      sourcePath: null,
      snippetUrl: null,
      policy: definition.policy,
      license: definition.license
    };
  });
}

function assertSourceUrl(value, definition) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || !definition.allowedOrigins.includes(url.origin)) {
    throw new Error(`${definition.label} returned a URL outside its HTTPS allowlist: ${value}`);
  }
}

async function sourceCandidates(source, request, options) {
  if (source === 'shadcn' || source === 'magicui') return searchRegistrySource(source, request, options);
  if (source === 'hyperui') return searchHyperUi(request, options);
  if (source === 'tabler') return searchTabler(request, options);
  if (source === 'landbook') return searchLandbook(request, options);
  throw new Error(`unsupported reference source: ${source}`);
}

export function validateReferenceRequest(request) {
  const failures = [];
  if (!isObject(request)) return ['request must be a JSON object'];
  if (request.requestVersion !== REFERENCE_REQUEST_VERSION) failures.push(`request.requestVersion must be ${REFERENCE_REQUEST_VERSION}`);
  if (typeof request.query !== 'string' || !request.query.trim() || request.query.length > 1_000) failures.push('request.query must be a non-empty string up to 1000 characters');
  for (const field of ['artifactType', 'platform', 'searchId']) {
    if (request[field] !== undefined && (typeof request[field] !== 'string' || !request[field].trim())) failures.push(`request.${field} must be a non-empty string when provided`);
  }
  if (request.sources !== undefined && (!Array.isArray(request.sources) || request.sources.length === 0 || !request.sources.every((source) => SOURCE_SET.has(source)))) {
    failures.push(`request.sources must contain only: ${DEFAULT_SOURCES.join(', ')}`);
  }
  if (request.limit !== undefined && (!Number.isInteger(request.limit) || request.limit < 1 || request.limit > 10)) failures.push('request.limit must be an integer from 1 to 10');
  if (request.cacheMaxAgeHours !== undefined && (!Number.isInteger(request.cacheMaxAgeHours) || request.cacheMaxAgeHours < 1 || request.cacheMaxAgeHours > 720)) failures.push('request.cacheMaxAgeHours must be an integer from 1 to 720');
  return failures;
}

export function normalizedReferenceRequest(request) {
  const failures = validateReferenceRequest(request);
  if (failures.length) throw new Error(failures.join('; '));
  return {
    requestVersion: REFERENCE_REQUEST_VERSION,
    searchId: request.searchId?.trim() || createSearchId(),
    query: request.query.trim(),
    artifactType: request.artifactType?.trim() || 'interface',
    platform: request.platform?.trim() || 'web',
    sources: [...new Set(request.sources ?? DEFAULT_SOURCES)],
    limit: request.limit ?? 5,
    cacheMaxAgeHours: request.cacheMaxAgeHours ?? 24
  };
}

export function sweepReferenceCache(referenceRoot, maxAgeHours, options = {}) {
  let storageRoot;
  try {
    storageRoot = new AnchoredRoot(referenceRoot, { create: false, hook: options.storageHook });
  } catch (error) {
    if (error.code === 'ENOENT') return 0;
    throw error;
  }
  const cutoff = Date.now() - (maxAgeHours * 60 * 60 * 1000);
  let removed = 0;
  try {
    for (const entry of storageRoot.entries()) {
      if (!entry.isDirectory() || entry.isSymbolicLink()) continue;
      const stats = storageRoot.lstat(entry.name);
      if (!stats?.isDirectory() || stats.isSymbolicLink() || stats.mtimeMs >= cutoff) continue;
      storageRoot.remove(entry.name, { operation: 'reference-cache-ttl-remove', expectedType: 'directory' });
      removed += 1;
    }
  } finally {
    storageRoot.close();
  }
  return removed;
}

async function materializeSnippet(reference, cacheDir, storageRoot, options) {
  if (reference.policy !== 'import-and-adapt' || !reference.snippetUrl) return null;
  try {
    const text = await fetchText(reference.snippetUrl, options);
    const truncated = Buffer.from(text).subarray(0, MAX_SNIPPET_BYTES);
    const extension = path.extname(reference.sourcePath || new URL(reference.snippetUrl).pathname) || '.txt';
    const relativePath = path.join('snippets', `${normalizeId(reference.id)}${extension}`);
    const absolutePath = path.join(cacheDir, relativePath);
    storageRoot.writeFile(storageRoot.relative(absolutePath), truncated, { operation: 'reference-cache-snippet-write' });
    return {
      relativePath: relativePath.split(path.sep).join('/'),
      absolutePath,
      bytes: truncated.length,
      sha256: crypto.createHash('sha256').update(truncated).digest('hex'),
      truncated: Buffer.byteLength(text) > truncated.length
    };
  } catch (error) {
    options.warnings.push(`${reference.id}: snippet unavailable: ${error.message}`);
    return null;
  }
}

export async function searchDesignReferences(rawRequest, options = {}) {
  const request = normalizedReferenceRequest(rawRequest);
  const cwd = options.cwd ?? process.cwd();
  const env = options.env ?? process.env;
  const designRoot = path.resolve(env.CENTURION_DESIGN_ROOT ?? path.join(cwd, '.centurion', 'design'));
  const referenceRoot = path.resolve(env.CENTURION_REFERENCE_ROOT ?? path.join(designRoot, '.reference-cache'));
  const cacheDir = path.join(referenceRoot, normalizeId(request.searchId));
  assertPathWithinRoot(referenceRoot, cacheDir, { allowRoot: false, label: 'reference cache' });
  const referenceStorage = new AnchoredRoot(referenceRoot, { create: true, hook: options.storageHook });
  const cacheRelative = referenceStorage.relative(cacheDir);
  if (referenceStorage.exists(cacheRelative)) {
    referenceStorage.close();
    throw new Error(`reference cache already exists: ${cacheDir}`);
  }

  const warnings = [];
  const errors = [];
  const sourceReports = [];
  const staleCachesRemoved = sweepReferenceCache(referenceRoot, request.cacheMaxAgeHours, { storageHook: options.storageHook });
  const fetcher = options.fetcher ?? globalThis.fetch;
  if (typeof fetcher !== 'function') throw new Error('reference search requires a fetch implementation');
  const adapterOptions = {
    fetcher,
    lookup: options.lookup ?? lookup,
    pinnedHttps: options.fetcher === undefined,
    timeoutMs: options.timeoutMs ?? 20_000,
    warnings
  };
  const queryTokens = expandedTokens(request);
  const candidates = [];

  const settled = await Promise.allSettled(request.sources.map(async (source) => {
    const items = await sourceCandidates(source, request, {
      ...adapterOptions,
      source,
      allowedOrigins: SOURCE_DEFINITIONS[source].allowedOrigins
    });
    return { source, items };
  }));
  for (let index = 0; index < settled.length; index += 1) {
    const source = request.sources[index];
    const result = settled[index];
    if (result.status === 'rejected') {
      warnings.push(`${source}: ${result.reason.message ?? result.reason}`);
      sourceReports.push({ source, status: 'failed', candidates: 0, error: result.reason.message ?? String(result.reason) });
      continue;
    }
    sourceReports.push({ source, status: 'done', candidates: result.value.items.length, error: null });
    candidates.push(...result.value.items);
  }

  const scored = candidates.map((candidate) => scoreCandidate(candidate, queryTokens));
  let selected = scored.filter((candidate) => candidate.score > 0);
  if (selected.length === 0) selected = scored;
  selected = selected.sort((left, right) => right.score - left.score || left.id.localeCompare(right.id));
  const diverse = [];
  for (const source of request.sources) {
    const candidate = selected.find((item) => item.source === source && !diverse.some((chosen) => chosen.id === item.id));
    if (candidate) diverse.push(candidate);
    if (diverse.length === request.limit) break;
  }
  for (const candidate of selected) {
    if (diverse.length === request.limit) break;
    if (!diverse.some((chosen) => chosen.id === candidate.id)) diverse.push(candidate);
  }
  selected = diverse;

  if (selected.length === 0) errors.push('no reference candidates were available from the requested sources');
  try {
    const cacheDirectory = referenceStorage.createDirectory(cacheRelative, {
      createParents: true,
      operation: 'reference-cache-create'
    });
    cacheDirectory.close();
    const references = [];
    for (const reference of selected) {
      const snippet = await materializeSnippet(reference, cacheDir, referenceStorage, {
        ...adapterOptions,
        source: reference.source,
        allowedOrigins: SOURCE_DEFINITIONS[reference.source].allowedOrigins
      });
      references.push({
        id: reference.id,
        source: reference.source,
        title: reference.title,
        description: reference.description,
        kind: reference.kind,
        policy: reference.policy,
        license: reference.license,
        sourceUrl: reference.sourceUrl,
        attributionUrl: reference.attributionUrl,
        previewImageUrl: reference.previewImageUrl ?? null,
        matchReasons: reference.matchReasons,
        score: reference.score,
        snippet
      });
    }

    const manifestPath = path.join(cacheDir, 'reference-manifest.json');
    const generatedAt = new Date();
    const manifest = {
      manifestVersion: REFERENCE_MANIFEST_VERSION,
      searchId: request.searchId,
      generatedAt: generatedAt.toISOString(),
      expiresAt: new Date(generatedAt.getTime() + request.cacheMaxAgeHours * 60 * 60 * 1000).toISOString(),
      query: request.query,
      artifactType: request.artifactType,
      platform: request.platform,
      strategy: 'compose',
      references
    };
    const manifestBytes = Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`);
    referenceStorage.writeFile(referenceStorage.relative(manifestPath), manifestBytes, {
      operation: 'reference-cache-manifest-write'
    });
    const manifestSha256 = crypto.createHash('sha256').update(manifestBytes).digest('hex');
    return {
    resultVersion: REFERENCE_RESULT_VERSION,
    searchId: request.searchId,
    status: errors.length ? 'failed' : 'done',
    query: request.query,
    manifestPath,
    manifestSha256,
    references,
    sources: sourceReports,
    cleanup: {
      cachePath: cacheDir,
      staleCachesRemoved,
      expiresAt: manifest.expiresAt,
      acceptedBundlesExcludedFromTtl: true
    },
    warnings,
    errors
    };
  } finally {
    referenceStorage.close();
  }
}

export function loadReferenceManifest(file, options = {}) {
  const absolutePath = path.resolve(options.cwd ?? process.cwd(), file);
  const allowedRoots = (options.allowedRoots ?? []).map((root) => path.resolve(root));
  const selectedRoot = allowedRoots.find((root) => isWithinPath(root, absolutePath)) ?? path.dirname(absolutePath);
  if (allowedRoots.length > 0 && !allowedRoots.includes(selectedRoot)) {
    throw new Error(`reference manifest must stay within an allowed root: ${allowedRoots.join(', ')}`);
  }
  const storageRoot = new AnchoredRoot(selectedRoot, { create: false, hook: options.storageHook });
  let bytes;
  try {
    bytes = storageRoot.readFile(storageRoot.relative(absolutePath), {
      operation: 'reference-manifest-load',
      label: 'reference manifest'
    });
  } catch (error) {
    storageRoot.close();
    throw error;
  }
  const data = JSON.parse(bytes.toString('utf8'));
  if (data.manifestVersion !== REFERENCE_MANIFEST_VERSION || !Array.isArray(data.references)) {
    storageRoot.close();
    throw new Error(`reference manifest must use ${REFERENCE_MANIFEST_VERSION}`);
  }
  if (!options.keepStorageOpen) storageRoot.close();
  return {
    absolutePath,
    rootPath: selectedRoot,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
    data,
    storageRoot: options.keepStorageOpen ? storageRoot : null
  };
}

export function normalizeDesignReferences(input, options = {}) {
  if (input === undefined || input === null) return null;
  if (!isObject(input)) throw new Error('request.references must be an object');
  if (typeof input.manifestPath !== 'string' || !input.manifestPath.trim()) throw new Error('request.references.manifestPath must be a non-empty string');
  if (input.selectedIds !== undefined && (!Array.isArray(input.selectedIds) || !input.selectedIds.every((id) => typeof id === 'string' && id.trim()))) {
    throw new Error('request.references.selectedIds must contain only non-empty strings');
  }
  if (input.strategy !== undefined && !STRATEGIES.has(input.strategy)) throw new Error('request.references.strategy must be compose, adapt, or inspire');
  const manifest = loadReferenceManifest(input.manifestPath, { ...options, keepStorageOpen: true });
  try {
    const available = new Set(manifest.data.references.map((reference) => reference.id));
    const selectedIds = [...new Set(input.selectedIds ?? manifest.data.references.map((reference) => reference.id))];
    const missing = selectedIds.filter((id) => !available.has(id));
    if (missing.length) throw new Error(`request.references.selectedIds not found in manifest: ${missing.join(', ')}`);
    for (const reference of manifest.data.references.filter((item) => selectedIds.includes(item.id))) {
      if (!reference.snippet) continue;
      const snippetPath = path.resolve(reference.snippet.absolutePath ?? '');
      if (!path.isAbsolute(reference.snippet.absolutePath ?? '')
        || !isWithinPath(path.dirname(manifest.absolutePath), snippetPath)) {
        throw new Error(`reference snippet must stay within manifest cache: ${reference.id}`);
      }
      let bytes;
      try {
        bytes = manifest.storageRoot.readFile(manifest.storageRoot.relative(snippetPath), {
          operation: 'reference-snippet-load',
          label: `reference snippet ${reference.id}`
        });
      } catch (error) {
        if (error.message.includes('must be a regular file')) {
          throw new Error(`reference snippet missing or unsafe: ${reference.id}`);
        }
        throw error;
      }
      const hash = crypto.createHash('sha256').update(bytes).digest('hex');
      if (hash !== reference.snippet.sha256) throw new Error(`reference snippet SHA-256 mismatch: ${reference.id}`);
      if (reference.snippet.bytes !== undefined && reference.snippet.bytes !== bytes.length) {
        throw new Error(`reference snippet byte count mismatch: ${reference.id}`);
      }
    }
    return {
      manifestPath: manifest.absolutePath,
      manifestRoot: manifest.rootPath,
      manifestSha256: manifest.sha256,
      selectedIds,
      strategy: input.strategy ?? manifest.data.strategy ?? 'compose',
      manifest: manifest.data
    };
  } finally {
    manifest.storageRoot.close();
  }
}
